import aiohttp
import datetime
import discord
import re
from attr import dataclass
from babel.units import format_unit
from core.view import DesignerView
from discord import ui
from utils.emoji import emoji


def parse_duration(duration: str, max_duration: str | None = None) -> datetime.timedelta:
    """
    Parse a duration string into a timedelta object.

    Parameters:
        duration (str): A string representing the duration, e.g., "2w3d4h5m6s".
        max_duration (str | None): An optional maximum duration string, e.g., "2w3d".
    """
    pattern = re.compile(r"(?P<value>\d+)(?P<unit>[wdhms])")
    matches = pattern.findall(duration)

    if not matches:
        raise ValueError(
            "Invalid duration format.\n-# Use `w` for weeks, `d` for days, `h` for hours, `m` for minutes, and `s` for seconds."
        )

    total_duration = datetime.timedelta()
    funcs = {
        "w": lambda x: datetime.timedelta(weeks=x),
        "d": lambda x: datetime.timedelta(days=x),
        "h": lambda x: datetime.timedelta(hours=x),
        "m": lambda x: datetime.timedelta(minutes=x),
        "s": lambda x: datetime.timedelta(seconds=x),
    }

    for value, unit in matches:
        value = int(value)
        if value <= 0:
            raise ValueError("Duration values must be positive.")
        total_duration += funcs[unit](value)

    if total_duration.total_seconds() <= 0:
        raise ValueError("Total duration must be positive.")

    # Check against max_duration if provided
    if max_duration is not None:
        max_td = parse_duration(max_duration)
        if total_duration > max_td:
            raise ValueError(f"Total duration must not exceed `{max_duration}`.")

    elif total_duration.days > 28:
        raise ValueError("Total duration must be less than `28 days`.")

    return total_duration


def fmt_perms(perms: list[str]) -> str:
    """
    Format a list of permissions into a human-readable string.

    Parameters:
        perms (list[str]): A list of permission names.

    Returns:
        str: A formatted string of permissions.
    """
    perms = [perm.replace("_", " ").replace("guild", "server").title() for perm in perms]
    if not perms:
        return "No permissions"
    if len(perms) == 1:
        return perms[0]
    return ", ".join(perms[:-1]) + " and " + perms[-1]


def fmt_memory(bytes_value):
    gb = round(bytes_value / 1024 / 1024 / 1024, 2)
    mb = round(bytes_value / 1024 / 1024, 2)
    if gb >= 1:
        return format_unit(gb, "digital-gigabyte", "short")
    else:
        return format_unit(mb, "digital-megabyte", "short")


@dataclass
class MemeViewData:
    nsfw: bool
    view: DesignerView


async def meme_view(subreddit: str | None = None) -> MemeViewData | None:
    """
    Creates a meme view from a subreddit or a random meme.

    Parameters:
        subreddit (str): The subreddit to fetch a meme from. If empty, fetches from a random subreddit.
    """
    url = "https://meme-api.com/gimme"
    if subreddit:
        url += f"/{subreddit}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if "url" in data:
                    view = DesignerView(
                        ui.Container(
                            ui.TextDisplay(f"## [{data['title']}]({data['postLink']})"),
                            ui.TextDisplay(
                                f"{emoji.reddit} **Subreddit**: [`r/{data['subreddit']}`](https://reddit.com/r/{data['subreddit']})\n"
                                f"{emoji.upvote} **Upvotes**: {data['ups']}"
                            ),
                            ui.MediaGallery(discord.MediaGalleryItem(url=data["url"])),
                        )
                    )
                    return MemeViewData(
                        nsfw=data.get("nsfw", False),
                        view=view,
                    )
                else:
                    return None
