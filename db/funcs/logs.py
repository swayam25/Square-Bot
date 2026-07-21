from ..schema import GuildTable, LogChannelTable
from .guild import fetch_guild_settings


async def fetch_log_channel(guild_id: int, log_type: str) -> int | None:
    """
    Fetches the log channel ID set for a log type, or None if not set.

    Args:
        guild_id (int): The guild ID to perform action on.
        log_type (str): The log type key (e.g. "moderation").
    """
    row = await LogChannelTable.filter(guild__guild_id=guild_id, log_type=log_type).first()
    return row.channel_id if row else None


async def fetch_log_channels(guild_id: int) -> dict[str, int]:
    """
    Fetches all configured log channels for a guild as a `{log_type: channel_id}` mapping.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    rows = await LogChannelTable.filter(guild__guild_id=guild_id)
    return {row.log_type: row.channel_id for row in rows}


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


async def set_all_log_channels(guild_id: int, log_types: list[str], channel_id: int) -> None:
    """
    Sets every given log type to the same channel.

    Args:
        guild_id (int): The guild ID to perform action on.
        log_types (list[str]): The log type keys to set.
        channel_id (int): The channel ID to log in.
    """
    for log_type in log_types:
        await set_log_channel(guild_id, log_type, channel_id)


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
