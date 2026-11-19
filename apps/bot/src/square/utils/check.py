import discord
from discord.ext import commands
from square.utils import config


class NotAuthorized(commands.CheckFailure):
    pass


def is_owner():
    async def check_func(ctx: discord.ApplicationContext) -> bool:
        if ctx.author.id != config.owner_id:
            raise NotAuthorized()
        return True

    return commands.check(check_func)
