from .guild import fetch_guild_settings
from square.db import cache
from square.db.schema import GuildTable


async def fetch_music_channel(guild_id: int) -> tuple[int | None, int | None]:
    settings = cache.get(guild_id)
    return settings.music_channel_id, settings.music_message_id


async def fetch_all_music_channels() -> dict[int, tuple[int, int | None]]:
    rows = await GuildTable.filter(music_channel_id__isnull=False).values_list(
        "guild_id", "music_channel_id", "music_message_id"
    )
    return {guild_id: (channel_id, message_id) for guild_id, channel_id, message_id in rows}


async def set_music_channel(guild_id: int, channel_id: int) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.music_channel_id = channel_id
    guild.music_message_id = None
    await guild.save(update_fields=["music_channel_id", "music_message_id"])
    settings = cache.entry(guild_id)
    settings.music_channel_id, settings.music_message_id = channel_id, None


async def set_music_message(guild_id: int, message_id: int | None) -> None:
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    guild.music_message_id = message_id
    await guild.save(update_fields=["music_message_id"])
    cache.entry(guild_id).music_message_id = message_id


async def remove_music_channel(guild_id: int) -> None:
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    guild.music_channel_id = None
    guild.music_message_id = None
    await guild.save(update_fields=["music_channel_id", "music_message_id"])
    settings = cache.entry(guild_id)
    settings.music_channel_id = settings.music_message_id = None


async def fetch_all_stay_channels() -> dict[int, int]:
    rows = await GuildTable.filter(music_stay_channel_id__isnull=False).values_list("guild_id", "music_stay_channel_id")
    return dict(rows)


async def set_stay_channel(guild_id: int, channel_id: int) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.music_stay_channel_id = channel_id
    await guild.save(update_fields=["music_stay_channel_id"])
    cache.entry(guild_id).music_stay_channel_id = channel_id


async def remove_stay_channel(guild_id: int) -> None:
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    guild.music_stay_channel_id = None
    await guild.save(update_fields=["music_stay_channel_id"])
    cache.entry(guild_id).music_stay_channel_id = None
