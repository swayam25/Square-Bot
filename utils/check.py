import aiohttp
import discord
from attr import dataclass
from db.funcs.dev import fetch_dev_ids
from discord.ext import commands
from utils import config


class NotAuthorized(commands.CheckFailure):
    """Exception raised when a user is not authorized to use a command."""

    pass


def is_owner(_ctx: discord.ApplicationContext | None = None):
    """
    Check if the command invoker is the bot owner.

    Can be used as a decorator or as a normal async function.
    """

    async def check_func(ctx: discord.ApplicationContext):
        owner_id = config.owner_id
        if ctx.author.id == owner_id:
            return True
        else:
            if _ctx is None:
                raise NotAuthorized()
            else:
                return False

    if _ctx is None:
        return commands.check(check_func)
    else:
        return check_func(_ctx)


def is_dev(_ctx: discord.ApplicationContext | None = None):
    """
    Check if the command invoker is a developer or the bot owner.

    Can be used as a decorator or as a normal async function.
    """

    async def check_func(ctx: discord.ApplicationContext):
        owner_id = config.owner_id
        dev_ids = await fetch_dev_ids()
        if ctx.author.id == owner_id or ctx.author.id in dev_ids:
            return True
        else:
            if _ctx is None:
                raise NotAuthorized()
            else:
                return False

    if _ctx is None:
        return commands.check(check_func)
    else:
        return check_func(_ctx)


@dataclass
class CheckSubreddit:
    exist: bool = True
    nsfw: bool = False
    display_name: str | None = None


async def check_subreddit(subreddit: str | None) -> CheckSubreddit:
    """
    Check if the subreddit is valid.

    Parameters:
        subreddit (str | None): The subreddit to check.
    """
    subreddit = None if not subreddit else subreddit.replace("r/", "").lower().strip()
    if not subreddit:
        return CheckSubreddit(exist=False, display_name=subreddit)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://meme-api.com/gimme/{subreddit}") as response:
            try:
                data = await response.json()
            except Exception:
                return CheckSubreddit(exist=False, display_name=subreddit)
            if response.status != 200:
                return CheckSubreddit(exist=False, display_name=subreddit)
            else:
                return CheckSubreddit(
                    exist=True,
                    nsfw=data.get("nsfw", False),
                    display_name=str(data["subreddit"]).strip(),
                )
