from ..schema import GuildTable
from .guild import fetch_guild_settings


async def fetch_music_channel(guild_id: int) -> tuple[int | None, int | None]:
    """
    Fetches the guild's music request channel and the ID of the player card living in it.

    Reads only, so looking the binding up never creates a settings row.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return None, None
    return guild.music_channel_id, guild.music_message_id


async def fetch_all_music_channels() -> dict[int, tuple[int, int | None]]:
    """
    Fetches every configured music request channel, keyed by guild ID.

    One query, used to seed the in-memory binding cache at startup.
    """
    rows = await GuildTable.filter(music_channel_id__isnull=False).values_list(
        "guild_id", "music_channel_id", "music_message_id"
    )
    return {guild_id: (channel_id, message_id) for guild_id, channel_id, message_id in rows}


async def set_music_channel(guild_id: int, channel_id: int) -> None:
    """
    Binds a guild's music request channel, clearing any card ID left over from a previous binding.

    Args:
        guild_id (int): The guild ID to perform action on.
        channel_id (int): The channel ID to bind.
    """
    guild = await fetch_guild_settings(guild_id)
    guild.music_channel_id = channel_id
    guild.music_message_id = None
    await guild.save()


async def set_music_message(guild_id: int, message_id: int | None) -> None:
    """
    Records which message currently holds the guild's player card.

    Args:
        guild_id (int): The guild ID to perform action on.
        message_id (int | None): The card's message ID, or None once it is gone.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    guild.music_message_id = message_id
    await guild.save()


async def remove_music_channel(guild_id: int) -> None:
    """
    Unbinds the guild's music request channel and forgets its card.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    guild.music_channel_id = None
    guild.music_message_id = None
    await guild.save()
