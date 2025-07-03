import aiohttp
import discord
from db.funcs.dev import fetch_dev_ids
from discord.ext import commands
from typing import TypedDict
from utils import config
from utils.emoji import emoji


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
                raise commands.MissingPermissions(["Bot Owner"])
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
                raise commands.MissingPermissions(["Bot Developer"])
            else:
                return False

    if _ctx is None:
        return commands.check(check_func)
    else:
        return check_func(_ctx)


async def author_interaction_check(ctx: discord.ApplicationContext, interaction: discord.Interaction):
    """Check if the interaction is from the author of the original command."""
    if interaction.user != ctx.author:
        em = discord.Embed(description=f"{emoji.error} You are not the author of this message.", color=config.color.red)
        await interaction.response.send_message(embed=em, ephemeral=True)
        return False
    else:
        return True


class CheckSubreddit(TypedDict):
    nsfw: bool
    display_name: str


async def check_subreddit(subreddit: str | None) -> CheckSubreddit | bool:
    """
    Check if the subreddit is valid.

    Parameters:
        subreddit (str | None): The subreddit to check.

    Returns:
        bool: True if the subreddit is valid, False otherwise.
    """
    if not subreddit:
        return False
    subreddit = None if not subreddit else subreddit.replace("r/", "").lower().strip()
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://reddit.com/r/{subreddit}/about.json", headers={"User-agent": "Chrome"}
        ) as response:
            try:
                data = await response.json()
            except Exception:
                return False
            if response.status != 200 or "data" not in data or "display_name" not in data["data"]:
                return False
            else:
                return {
                    "nsfw": data["data"].get("over18", False),
                    "display_name": str(data["data"]["display_name"]).strip(),
                }
