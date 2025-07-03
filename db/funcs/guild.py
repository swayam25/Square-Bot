from ..schema import GuildTable


async def fetch_guild_ids() -> list[int]:
    """Fetches all guild IDs from the database."""
    guilds = await GuildTable.all().values_list("guild_id", flat=True)
    return list(guilds)


async def add_guild(guild_id: int) -> GuildTable:
    """
    Adds a guild to the database.

    Parameters:
        guild_id (int): The guild ID to perform action on.
    """
    return (await GuildTable.get_or_create(guild_id=guild_id))[0]


async def remove_guild(guild_id: int) -> None:
    """
    Removes a guild from the database.

    Parameters:
        guild_id (int): The guild ID to perform action on.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if guild:
        await guild.delete()
    else:
        pass


async def fetch_guild_settings(guild_id: int) -> GuildTable:
    """
    Fetches settings for a specific guild.

    Parameters:
        guild_id (int): The guild ID to fetch settings for.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = guild = await add_guild(guild_id)
    return guild


async def set_mod_log_channel(guild_id: int, channel_id: int) -> None:
    """
    Sets the mod log channel for a guild.

    Parameters:
        guild_id (int): The guild ID to perform action on.
        channel_id (int): The channel ID to set as the mod log channel.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    guild.mod_log_channel_id = channel_id
    await guild.save()


async def set_mod_cmd_log_channel(guild_id: int, channel_id: int) -> None:
    """
    Sets the mod command log channel for a guild.

    Parameters:
        guild_id (int): The guild ID to perform action on.
        channel_id (int): The channel ID to set as the mod command log channel.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    guild.mod_cmd_log_channel_id = channel_id
    await guild.save()


async def set_msg_log_channel(guild_id: int, channel_id: int) -> None:
    """
    Sets the message log channel for a guild.

    Parameters:
        guild_id (int): The guild ID to perform action on.
        channel_id (int): The channel ID to set as the message log channel.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    guild.msg_log_channel_id = channel_id
    await guild.save()


async def set_ticket_cmds(guild_id: int, enabled: bool) -> None:
    """
    Enables or disables ticket commands for a guild.

    Parameters:
        guild_id (int): The guild ID to perform action on.
        enabled (bool): Whether to enable or disable ticket commands.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    guild.ticket = enabled
    await guild.save()


async def set_ticket_log_channel(guild_id: int, channel_id: int) -> None:
    """
    Sets the ticket log channel for a guild.

    Parameters:
        guild_id (int): The guild ID to perform action on.
        channel_id (int): The channel ID to set as the ticket log channel.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    guild.ticket_log_channel_id = channel_id
    await guild.save()


async def set_media_only_channel(guild_id: int, channel_id: int) -> None:
    """
    Sets the media-only channel for a guild.

    Parameters:
        guild_id (int): The guild ID to perform action on.
        channel_id (int): The channel ID to set as the media-only channel.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    guild.media_only_channel_id = channel_id
    await guild.save()


async def set_autorole(guild_id: int, role_id: int) -> None:
    """
    Sets the autorole for a guild.

    Parameters:
        guild_id (int): The guild ID to perform action on.
        role_id (int): The role ID to set as the autorole.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    guild.autorole = role_id
    await guild.save()


async def set_auto_meme_channel(guild_id: int, channel_id: int) -> None:
    """
    Sets the auto meme channel for a guild.

    Parameters:
        guild_id (int): The guild ID to perform action on.
        channel_id (int): The channel ID to set as the auto meme channel.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        guild = await add_guild(guild_id)
    guild.auto_meme_channel_id = channel_id
    await guild.save()
