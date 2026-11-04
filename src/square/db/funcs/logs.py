from .guild import fetch_guild_settings
from square.db import cache
from square.db.schema import GuildTable, LogChannelTable
from tortoise.transactions import in_transaction


async def fetch_log_channel(guild_id: int, log_type: str) -> int | None:
    """
    Gets the log channel ID set for a log type, or None if not set. Served from the settings cache.

    Args:
        guild_id (int): The guild ID to perform action on.
        log_type (str): The log type key (e.g. "moderation").
    """
    return cache.get(guild_id).log_channels.get(log_type)


async def fetch_log_guild_ids(log_type: str) -> set[int]:
    """
    Gets the IDs of every guild that has a log channel set for a log type. Served from the settings cache.

    Args:
        log_type (str): The log type key (e.g. "members").
    """
    return cache.guild_ids_with_log(log_type)


async def fetch_log_channels(guild_id: int) -> dict[str, int]:
    """
    Gets all configured log channels for a guild as a `{log_type: channel_id}` mapping. Served from the cache.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    return dict(cache.get(guild_id).log_channels)


async def set_log_channel(guild_id: int, log_type: str, channel_id: int) -> None:
    """
    Sets the log channel for a log type, creating or updating its row.

    Args:
        guild_id (int): The guild ID to perform action on.
        log_type (str): The log type key (e.g. "moderation").
        channel_id (int): The channel ID to log in.
    """
    guild = await fetch_guild_settings(guild_id)
    await LogChannelTable.update_or_create(guild=guild, log_type=log_type, defaults={"channel_id": channel_id})
    cache.entry(guild_id).log_channels[log_type] = channel_id


async def set_all_log_channels(guild_id: int, log_types: list[str], channel_id: int) -> None:
    """
    Sets every given log type to the same channel, replacing the guild's rows in one transaction.

    Args:
        guild_id (int): The guild ID to perform action on.
        log_types (list[str]): The log type keys to set.
        channel_id (int): The channel ID to log in.
    """
    guild = await fetch_guild_settings(guild_id)
    async with in_transaction():
        await LogChannelTable.filter(guild=guild, log_type__in=log_types).delete()
        await LogChannelTable.bulk_create(
            [LogChannelTable(guild=guild, log_type=log_type, channel_id=channel_id) for log_type in log_types]
        )
    cache.entry(guild_id).log_channels.update(dict.fromkeys(log_types, channel_id))


async def remove_log_channel(guild_id: int, log_type: str | None = None) -> None:
    """
    Removes a log channel setting, or all of them if no log type is given.

    Args:
        guild_id (int): The guild ID to perform action on.
        log_type (str | None): The log type key to remove, or None for all.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    query = LogChannelTable.filter(guild=guild)  # Deletes can't join across relations
    if log_type is not None:
        query = query.filter(log_type=log_type)
    await query.delete()
    channels = cache.entry(guild_id).log_channels
    if log_type is None:
        channels.clear()
    else:
        channels.pop(log_type, None)
