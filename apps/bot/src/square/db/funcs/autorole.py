from square.db import cache
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import AutoroleUserTable, StickyRoleTable
from tortoise.transactions import in_transaction
from typing import Any

_FIELDS = (
    "autorole_ids",
    "autorole_bot_ids",
    "autorole_split",
    "autorole_delay",
    "autorole_screening",
    "autorole_sticky",
    "autorole_sticky_ignore_ids",
)


async def save(guild_id: int, **values: Any) -> None:
    """Turning sticky roles off forgets every saved member."""
    if unknown := set(values) - set(_FIELDS):
        raise ValueError(f"Not an auto role setting: {', '.join(sorted(unknown))}")
    guild = await fetch_guild_settings(guild_id)
    guild.update_from_dict(values)
    await guild.save(update_fields=list(values))
    settings = cache.entry(guild_id)
    for key, value in values.items():
        setattr(settings, key, list(value) if isinstance(value, list) else value)
    if values.get("autorole_sticky") is False:
        await StickyRoleTable.filter(guild=guild).delete()


async def set_users(guild_id: int, users: dict[int, list[int]]) -> None:
    guild = await fetch_guild_settings(guild_id)
    async with in_transaction():
        await AutoroleUserTable.filter(guild=guild).delete()
        await AutoroleUserTable.bulk_create(
            [AutoroleUserTable(guild=guild, user_id=user_id, role_ids=role_ids) for user_id, role_ids in users.items()]
        )
    cache.entry(guild_id).autorole_users = {user_id: list(role_ids) for user_id, role_ids in users.items()}


async def reset(guild_id: int) -> None:
    await save(
        guild_id,
        autorole_ids=[],
        autorole_bot_ids=[],
        autorole_split=False,
        autorole_delay=0,
        autorole_screening=False,
        autorole_sticky=False,
        autorole_sticky_ignore_ids=[],
    )
    await set_users(guild_id, {})


async def keep_roles(guild_id: int, user_id: int, role_ids: list[int]) -> None:
    guild = await fetch_guild_settings(guild_id)
    await StickyRoleTable.update_or_create(guild=guild, user_id=user_id, defaults={"role_ids": role_ids})


async def take_roles(guild_id: int, user_id: int) -> list[int]:
    """The roles kept for someone who left, removed from storage once read."""
    row = await StickyRoleTable.filter(guild__guild_id=guild_id, user_id=user_id).first()
    if row is None:
        return []
    await row.delete()
    return row.role_ids


async def kept_count(guild_id: int) -> int:
    return await StickyRoleTable.filter(guild__guild_id=guild_id).count()
