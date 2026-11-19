from .guild import fetch_guild_settings
from square.db import cache
from square.db.schema import GuildTable, LogChannelTable
from tortoise.transactions import in_transaction
from typing import Any


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


_SETTINGS = ("log_disabled_events", "log_ignored_channel_ids", "log_ignored_role_ids", "log_skip_bots")


async def save_settings(guild_id: int, **values: Any) -> None:
    if unknown := set(values) - set(_SETTINGS):
        raise ValueError(f"Not a log setting: {', '.join(sorted(unknown))}")
    guild = await fetch_guild_settings(guild_id)
    guild.update_from_dict(values)
    await guild.save(update_fields=list(values))
    settings = cache.entry(guild_id)
    for key, value in values.items():
        setattr(settings, key, list(value) if isinstance(value, list) else value)


async def reset(guild_id: int) -> None:
    await remove_log_channel(guild_id)
    await save_settings(
        guild_id, log_disabled_events=[], log_ignored_channel_ids=[], log_ignored_role_ids=[], log_skip_bots=True
    )
