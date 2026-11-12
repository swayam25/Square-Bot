from .guild import fetch_guild_settings
from square.db import cache
from square.db.schema import GuildTable, LogChannelTable
from tortoise.transactions import in_transaction


async def fetch_log_channel(guild_id: int, log_type: str) -> int | None:
    return cache.get(guild_id).log_channels.get(log_type)


async def fetch_log_guild_ids(log_type: str) -> set[int]:
    return cache.guild_ids_with_log(log_type)


async def fetch_log_channels(guild_id: int) -> dict[str, int]:
    return dict(cache.get(guild_id).log_channels)


async def set_log_channel(guild_id: int, log_type: str, channel_id: int) -> None:
    guild = await fetch_guild_settings(guild_id)
    await LogChannelTable.update_or_create(guild=guild, log_type=log_type, defaults={"channel_id": channel_id})
    cache.entry(guild_id).log_channels[log_type] = channel_id


async def set_all_log_channels(guild_id: int, log_types: list[str], channel_id: int) -> None:
    guild = await fetch_guild_settings(guild_id)
    async with in_transaction():
        await LogChannelTable.filter(guild=guild, log_type__in=log_types).delete()
        await LogChannelTable.bulk_create(
            [LogChannelTable(guild=guild, log_type=log_type, channel_id=channel_id) for log_type in log_types]
        )
    cache.entry(guild_id).log_channels.update(dict.fromkeys(log_types, channel_id))


async def remove_log_channel(guild_id: int, log_type: str | None = None) -> None:
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
