import discord
from collections import defaultdict
from collections.abc import Mapping
from square.core import Client
from square.db.funcs import logs as db
from square.settings.errors import SettingError
from square.utils.server_log import LogType


async def set_channels(
    client: Client, guild: discord.Guild, changes: Mapping[LogType, discord.TextChannel | None]
) -> None:
    """Sends each log type to its channel, or turns it off with `None`. Every channel is checked before any change."""
    for channel in {channel for channel in changes.values() if channel}:
        perms = channel.permissions_for(guild.me)
        if not (perms.send_messages and perms.manage_webhooks):
            # Logs are posted through a webhook named after the bot
            raise SettingError(f"I need `Send Messages` and `Manage Webhooks` in {channel.mention}.")

    by_channel: defaultdict[discord.TextChannel, list[str]] = defaultdict(list)
    for log_type, channel in changes.items():
        if channel:
            by_channel[channel].append(log_type.key)
        else:
            await db.remove_log_channel(guild.id, log_type.key)
    for channel, keys in by_channel.items():
        await db.set_all_log_channels(guild.id, keys, channel.id)
    client.dispatch("log_channels_update", guild.id)


async def reset(client: Client, guild: discord.Guild) -> None:
    await db.remove_log_channel(guild.id)
    client.dispatch("log_channels_update", guild.id)
