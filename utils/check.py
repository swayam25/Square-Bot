import discord
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
