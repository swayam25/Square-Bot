from ..schema import DJRoleTable, GuildTable
from .guild import fetch_guild_settings


async def fetch_dj(guild_id: int) -> tuple[bool, list[int]]:
    """
    Fetches the guild's DJ mode flag and its DJ role IDs.

    Reads only, so the permission check on every playback action never creates a settings row.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return False, []
    role_ids = await DJRoleTable.filter(guild=guild).values_list("role_id", flat=True)
    return guild.dj_mode, list(role_ids)


async def set_dj_mode(guild_id: int, enabled: bool) -> None:
    """
    Enables or disables DJ-only playback controls for a guild.

    Args:
        guild_id (int): The guild ID to perform action on.
        enabled (bool): Whether to restrict playback controls to DJs.
    """
    guild = await fetch_guild_settings(guild_id)
    guild.dj_mode = enabled
    await guild.save()


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
    await guild.save()
