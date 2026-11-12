from square.db import cache
from square.db.schema import GuildTable
from square.modules import Module


async def fetch_guild_ids() -> list[int]:
    guilds = await GuildTable.all().values_list("guild_id", flat=True)
    return list(guilds)


async def add_guild(guild_id: int) -> GuildTable:
    return (await GuildTable.get_or_create(guild_id=guild_id))[0]


async def remove_guild(guild_id: int) -> None:
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if guild:
        await guild.delete()
    cache.drop(guild_id)


async def fetch_guild_settings(guild_id: int) -> GuildTable:
    """
    Fetches the guild's database row for writing, creating it if missing. Read settings with `cache.get` instead.

    Args:
        guild_id (int): The guild ID to fetch settings for.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    return guild


async def set_module(guild_id: int, module: Module, on: bool) -> None:
    guild = await fetch_guild_settings(guild_id)
    modules = [value for value in guild.modules if value != module]
    guild.modules = [*modules, module.value] if on else modules
    await guild.save(update_fields=["modules"])
    cache.entry(guild_id).modules = list(guild.modules)


async def set_media_only(guild_id: int, channel_id: int | None) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.media_only_channel_id = channel_id
    await guild.save(update_fields=["media_only_channel_id"])
    cache.entry(guild_id).media_only_channel_id = channel_id


async def set_autorole(guild_id: int, role_id: int | None) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.autorole = role_id
    await guild.save(update_fields=["autorole"])
    cache.entry(guild_id).autorole = role_id
