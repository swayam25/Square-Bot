from square.db import cache
from square.db.schema import AutoroleUserTable, GuildTable
from square.modules import Module
from tortoise.transactions import in_transaction


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


async def set_autoroles(
    guild_id: int, *, humans: list[int] | None = None, bots: list[int] | None = None, split: bool | None = None
) -> None:
    guild = await fetch_guild_settings(guild_id)
    if humans is not None:
        guild.autorole_ids = list(humans)
    if bots is not None:
        guild.autorole_bot_ids = list(bots)
    if split is not None:
        guild.autorole_split = split
    await guild.save(update_fields=["autorole_ids", "autorole_bot_ids", "autorole_split"])
    settings = cache.entry(guild_id)
    settings.autorole_ids, settings.autorole_bot_ids = list(guild.autorole_ids), list(guild.autorole_bot_ids)
    settings.autorole_split = guild.autorole_split


async def set_autorole_users(guild_id: int, users: dict[int, list[int]]) -> None:
    guild = await fetch_guild_settings(guild_id)
    async with in_transaction():
        await AutoroleUserTable.filter(guild=guild).delete()
        await AutoroleUserTable.bulk_create(
            [AutoroleUserTable(guild=guild, user_id=user_id, role_ids=role_ids) for user_id, role_ids in users.items()]
        )
    cache.entry(guild_id).autorole_users = {user_id: list(role_ids) for user_id, role_ids in users.items()}
