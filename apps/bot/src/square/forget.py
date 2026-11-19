import discord
from square.core import Client
from square.db.funcs.guild import remove_guild
from square.logs import memory as log_memory
from square.logs import sender as log_sender
from square.music import request, stay
from square.music.player import cleanup_guild as release_music
from square.utils import invites, storage, webhook


async def forget_guild(client: Client, guild: discord.Guild) -> None:
    """Drops every row, file and bit of memory the bot keeps for a server. Used when the bot leaves and by the full reset."""
    await remove_guild(guild.id)
    await storage.purge_guild(guild.id)
    webhook.cleanup({channel.id for channel in guild.channels})
    log_sender.forget(guild.id)
    log_memory.forget(guild.id)
    request.forget(guild.id)
    stay.forget(guild.id)
    release_music(client, guild.id)
    invites.forget(guild.id)
