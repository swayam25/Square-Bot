import discord
from discord.ext import commands
from square.utils import config

# Spread into a top-level command so it also works from a user install: any server, DMs and group DMs
ANYWHERE = {
    "integration_types": {discord.IntegrationType.guild_install, discord.IntegrationType.user_install},
    "contexts": {
        discord.InteractionContextType.guild,
        discord.InteractionContextType.bot_dm,
        discord.InteractionContextType.private_channel,
    },
}
# Like `ANYWHERE`, but only for people who added the bot to their account, never for a server that added it
USER_INSTALL = {**ANYWHERE, "integration_types": {discord.IntegrationType.user_install}}


class NotAuthorized(commands.CheckFailure):
    pass


class NotInServer(commands.CheckFailure):
    pass


def is_owner():
    async def check_func(ctx: discord.ApplicationContext) -> bool:
        if ctx.author.id != config.owner_id:
            raise NotAuthorized()
        return True

    return commands.check(check_func)


async def bot_in_server(ctx: discord.ApplicationContext) -> bool:
    """
    For `ANYWHERE` commands that need the bot in the server. Add it with `@commands.check(check.bot_in_server)`.

    A user install also runs in servers the bot isn't in, where `ctx.guild` is a bare stand-in without channels, roles
    or members.
    """
    if ctx.guild is None:
        raise commands.NoPrivateMessage()
    if ctx.bot.get_guild(ctx.guild.id) is None:
        raise NotInServer()
    return True
