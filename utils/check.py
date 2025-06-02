import discord
from db.funcs.dev import fetch_dev_ids
from discord.ext import commands
from utils import config


def is_owner():
    """Check if the command invoker is the bot owner."""

    async def predicate(ctx: discord.ApplicationContext):
        owner_id = config.owner_id
        if ctx.author.id == owner_id:
            return True
        else:
            raise commands.CommandError("You are not authorized to use this command.")

    return commands.check(predicate)


def is_dev():
    """Check if the command invoker is a developer or the bot owner."""

    async def predicate(ctx: discord.ApplicationContext):
        owner_id = config.owner_id
        dev_ids = await fetch_dev_ids()
        if ctx.author.id == owner_id or ctx.author.id in dev_ids:
            return True
        else:
            raise commands.MissingPermissions("You are not authorized to use this command.")

    return commands.check(predicate)
