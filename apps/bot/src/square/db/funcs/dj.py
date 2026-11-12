from .guild import fetch_guild_settings
from square.db import cache
from square.db.schema import DJRoleTable, GuildTable


async def set_dj_mode(guild_id: int, enabled: bool) -> None:
    """
    Enables or disables DJ-only playback controls for a guild.

    Args:
        guild_id (int): The guild ID to perform action on.
        enabled (bool): Whether to restrict playback controls to DJs.
    """
    guild = await fetch_guild_settings(guild_id)
    guild.dj_mode = enabled
    await guild.save(update_fields=["dj_mode"])
    cache.entry(guild_id).dj_mode = enabled


async def set_dj_roles(guild_id: int, role_ids: list[int]) -> None:
    """
    Replaces the guild's DJ roles with the given ones.

    Args:
        guild_id (int): The guild ID to perform action on.
        role_ids (list[int]): The role IDs that should count as DJs.
    """
    guild = await fetch_guild_settings(guild_id)
    stale = DJRoleTable.filter(guild=guild)
    if role_ids:
        stale = stale.exclude(role_id__in=role_ids)
    await stale.delete()
    for role_id in role_ids:
        await DJRoleTable.get_or_create(guild=guild, role_id=role_id)
    cache.entry(guild_id).dj_roles = list(role_ids)


async def remove_dj(guild_id: int) -> None:
    """
    Turns DJ mode off and drops every DJ role.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    await DJRoleTable.filter(guild=guild).delete()
    guild.dj_mode = False
    await guild.save(update_fields=["dj_mode"])
    settings = cache.entry(guild_id)
    settings.dj_mode, settings.dj_roles = False, []
