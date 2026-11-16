import discord
from square.core import Client
from square.db.funcs.guild import remove_guild
from square.music import request, stay
from square.music.player import cleanup_guild as release_music
from square.utils import invites, storage
from square.utils.server_log import cleanup_guild as release_webhooks


async def forget_guild(client: Client, guild: discord.Guild) -> None:
    """Drops every row, file and bit of memory Square keeps for a server. Used when Square leaves and by the full reset."""
    await remove_guild(guild.id)
    await storage.purge_guild(guild.id)
    await release_webhooks(guild.id, {channel.id for channel in guild.channels})
    request.forget(guild.id)
    stay.forget(guild.id)
    release_music(client, guild.id)
    invites.forget(guild.id)
