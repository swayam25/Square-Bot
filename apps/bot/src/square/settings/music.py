import discord
from square.core import Client
from square.db import cache
from square.db.funcs import dj as db
from square.music import request, stay
from square.music.core import can_play_in, get_player
from square.music.dj import MAX_ROLES
from square.music.player import release_guild, render_player, stop_player
from square.settings.errors import SettingError

VoiceChannel = discord.VoiceChannel | discord.StageChannel


def request_channel(guild: discord.Guild) -> discord.abc.GuildChannel | None:
    channel_id = request.channel_id(guild.id)
    return guild.get_channel(channel_id) if channel_id else None


def stay_channel(guild: discord.Guild) -> discord.abc.GuildChannel | None:
    channel_id = stay.channel_id(guild.id)
    return guild.get_channel(channel_id) if channel_id else None


def dj_roles(guild: discord.Guild) -> list[discord.Role]:
    # Resolved against live roles, so a deleted role's leftover row never shows up
    return [role for role_id in cache.get(guild.id).dj_roles if (role := guild.get_role(role_id))]


async def create_request_channel(client: Client, guild: discord.Guild) -> discord.TextChannel:
    """Creates a channel where anything typed is queued, with the player pinned."""
    if channel := request_channel(guild):
        raise SettingError(f"{channel.mention} is already the music request channel.")
    if not guild.me.guild_permissions.manage_channels:
        raise SettingError("I need the `Manage Channels` permission to create the channel.")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            add_reactions=False,
            attach_files=False,
            embed_links=False,
            create_public_threads=False,
            create_private_threads=False,
            send_messages_in_threads=False,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
        ),
    }
    try:
        channel = await guild.create_text_channel(
            "music-requests", overwrites=overwrites, topic="Send a track name or a link here to queue it."
        )
    except discord.HTTPException as exc:
        raise SettingError(f"I couldn't create the music channel: {exc.text or exc}") from exc
    await request.bind(guild.id, channel.id)
    request.prime(client, guild.id)
    await render_player(client, guild.id, wait=True)
    return channel


async def remove_request_channel(client: Client, guild: discord.Guild, actor: discord.abc.User) -> str | None:
    """
    Unbinds the request channel and deletes it, card and all.

    The bot created the channel, so it's throwing away its own: everything in there is either the card or a
    request the bot already cleared. Returns a note when the channel had to be left behind.
    """
    channel_id = request.channel_id(guild.id)
    if channel_id is None:
        return None
    # Unbind first, so deleting the channel doesn't race the listener that watches for it
    await request.unbind(guild.id)
    note = None
    if (channel := guild.get_channel(channel_id)) is not None:
        try:
            await channel.delete(reason=f"Music channel removed by {actor}")
        except discord.HTTPException:
            note = f"I couldn't delete {channel.mention}, so it's yours to remove."
    await release_guild(client, guild.id)
    return note


async def set_stay_channel(client: Client, guild: discord.Guild, channel: VoiceChannel | None) -> None:
    """Keeps the bot in the voice channel around the clock. `None` turns 24/7 off."""
    if channel is None:
        await _clear_stay_channel(client, guild)
        return
    if not can_play_in(channel):
        raise SettingError(f"I need the `Connect` and `Speak` permissions in {channel.mention}.")
    await stay.bind(guild.id, channel.id)
    try:
        await stay.join(client, guild.id)
    except Exception:
        stay.schedule_rejoin(client, guild.id)  # Keeps trying in the background


async def _clear_stay_channel(client: Client, guild: discord.Guild) -> None:
    """
    Drops the 24/7 channel, so the bot leaves once it is no longer needed there.

    A session still playing is left to finish and is then torn down like any other.
    An idle bot was only there because of 24/7, so it leaves right away.
    """
    if stay.channel_id(guild.id) is None:
        return
    await stay.unbind(guild.id)
    if (player := get_player(client, guild.id)) is None:
        return
    if player.current:
        # Re-arms sonolink's disconnect timer, which 24/7 was holding off
        player.cancel_empty_timer()
        player._check_inactivity()
    else:
        await stop_player(player, guild, force=True)


async def set_dj_mode(guild: discord.Guild, enabled: bool) -> None:
    """Limits playback controls to DJs."""
    await db.set_dj_mode(guild.id, enabled)


async def set_dj_roles(guild: discord.Guild, roles: list[discord.Role]) -> None:
    """Replaces the DJ roles. Members with Manage Server are always DJs."""
    if len(roles) > MAX_ROLES:
        raise SettingError(f"Pick up to {MAX_ROLES} DJ roles.")
    role_ids = [role.id for role in roles]
    await db.set_dj_roles(guild.id, role_ids)
    # Picking the first role is the whole point, so don't make enabling DJ mode a second step
    if role_ids and not cache.get(guild.id).dj_mode:
        await db.set_dj_mode(guild.id, True)


async def reset(client: Client, guild: discord.Guild, actor: discord.abc.User) -> str | None:
    """Clears the page. Returns a note when the request channel had to be left behind."""
    note = await remove_request_channel(client, guild, actor)
    await _clear_stay_channel(client, guild)
    await db.remove_dj(guild.id)
    return note
