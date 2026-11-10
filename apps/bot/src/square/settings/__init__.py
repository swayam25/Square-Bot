"""
The rules behind every server setting: what's allowed, what gets saved and what else has to happen.

Both the Discord `/settings` panel and the dashboard API change settings through here, so the two can't drift apart.
Refusals raise `SettingError` with a message for the person who asked.
"""

import discord
from square.core import Client
from square.db.funcs.guild import remove_guild
from square.music import request, stay
from square.settings import general, invites, logs, music, tickets
from square.settings.errors import SettingError

__all__ = ["SettingError", "general", "invites", "logs", "music", "reset_all", "tickets"]


async def reset_all(client: Client, guild: discord.Guild, actor: discord.abc.User) -> list[str]:
    """Resets every setting and drops the server's row. Returns notes about channels that had to be left behind."""
    await general.reset(guild)
    await logs.reset(client, guild)
    notes = [await music.reset(client, guild, actor), await tickets.reset(guild, actor)]
    await invites.reset(guild)
    await remove_guild(guild.id)
    request.forget(guild.id)
    stay.forget(guild.id)
    client.dispatch("log_channels_update", guild.id)
    return [note for note in notes if note]
