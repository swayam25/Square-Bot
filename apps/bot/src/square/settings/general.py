import discord
from square.db.funcs import guild as db
from square.settings.errors import SettingError


async def set_autorole(guild: discord.Guild, role: discord.Role | None) -> None:
    """Gives the role to every member who joins. `None` turns it off."""
    if role and (role.is_default() or role.managed or role >= guild.me.top_role):
        raise SettingError(f"I can't give out {role.mention}, it's above my role or managed.")
    await db.set_autorole(guild.id, role.id if role else None)


async def set_media_only(guild: discord.Guild, channel: discord.TextChannel | None) -> None:
    """Allows only media and links in the channel. `None` turns it off."""
    if channel:
        perms = channel.permissions_for(guild.me)
        if not (perms.send_messages and perms.manage_messages):
            raise SettingError(f"I need `Send Messages` and `Manage Messages` in {channel.mention}.")
    await db.set_media_only(guild.id, channel.id if channel else None)


async def reset(guild: discord.Guild) -> None:
    await db.set_autorole(guild.id, None)
    await db.set_media_only(guild.id, None)
