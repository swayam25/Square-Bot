import asyncio
import discord
import itertools
from core import Client, console
from db.funcs.music import fetch_all_stay_channels, remove_stay_channel, set_stay_channel
from music.core import SquarePlayer, can_play_in, get_player, session_lock

_REJOIN_BACKOFF = (5, 15, 30, 60)

# Kept out of `music/store.py`, whose keys `flush_store` wipes on every teardown.
_bindings: dict[int, int] = {}
_rejoin_tasks: dict[int, asyncio.Task] = {}


class StayError(Exception):
    """Raised when the bot can't take its place in a 24/7 channel right now."""


async def seed() -> None:
    """
    Rebuilds the binding cache from the database.

    Called on every ready, including resumes, so it replaces the dict wholesale rather than merging.
    """
    bindings = await fetch_all_stay_channels()
    _bindings.clear()
    _bindings.update(bindings)


def channel_id(guild_id: int) -> int | None:
    """Returns the guild's 24/7 voice channel ID, or None when it has none."""
    return _bindings.get(guild_id)


def is_stay_channel(guild_id: int, channel_id: int | None) -> bool:
    """Whether a channel is the guild's 24/7 voice channel."""
    return channel_id is not None and _bindings.get(guild_id) == channel_id


async def bind(guild_id: int, channel_id: int) -> None:
    """
    Makes a voice channel the guild's 24/7 channel.

    Args:
        guild_id (int): The guild to bind the channel for.
        channel_id (int): The voice channel the bot should stay in.
    """
    await set_stay_channel(guild_id, channel_id)
    _bindings[guild_id] = channel_id


def _cancel_rejoin(guild_id: int) -> None:
    task = _rejoin_tasks.pop(guild_id, None)
    if task and task is not asyncio.current_task():
        task.cancel()


async def unbind(guild_id: int) -> None:
    """
    Drops the guild's 24/7 channel, so the bot goes back to leaving when playback ends.

    Args:
        guild_id (int): The guild to unbind.
    """
    # Cache first, so a disconnect landing during the DB write doesn't schedule a rejoin.
    _bindings.pop(guild_id, None)
    _cancel_rejoin(guild_id)
    await remove_stay_channel(guild_id)


def forget(guild_id: int) -> None:
    """
    Drops the cached binding without touching the database.

    For when the row is already gone - the guild was left, or `/settings reset all` deleted it.
    """
    _bindings.pop(guild_id, None)
    _cancel_rejoin(guild_id)


async def move(player: SquarePlayer, channel: discord.VoiceChannel) -> None:
    """
    Moves a connected player into another voice channel without interrupting playback.

    Args:
        player (:class:`SquarePlayer`): The connected player.
        channel (:class:`VoiceChannel`): The channel to move into.
    """
    await channel.guild.change_voice_state(channel=channel)
    # Sonolink only tracks the new channel ID on a move, never the `channel` attribute that every
    # "are you in my voice channel" check reads.
    player.channel = channel


async def resolve(guild: discord.Guild) -> discord.VoiceChannel | None:
    """
    Returns the guild's 24/7 channel, dropping the binding when the channel no longer exists.

    Args:
        guild (:class:`Guild`): The guild to look the channel up in.
    """
    cid = _bindings.get(guild.id)
    if cid is None:
        return None
    channel = guild.get_channel(cid)
    if isinstance(channel, discord.VoiceChannel):
        return channel
    await unbind(guild.id)
    return None


async def join(client: Client, guild_id: int) -> SquarePlayer | None:
    """
    Puts the bot in the guild's 24/7 channel, connecting or moving it there as needed.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to join the 24/7 channel of.

    Returns:
        :class:`SquarePlayer` | None: The player sitting in the channel, or None when there is
        nothing to join because the guild is unbound, gone, or its channel was deleted.

    Raises:
        StayError: The bot lacks permissions for the channel.
        Exception: Whatever connecting raised, e.g. no Lavalink node is up yet.
    """
    from music.player import clear_status, discard_stale

    guild = client.get_guild(guild_id)
    channel = await resolve(guild) if guild else None
    if channel is None:
        return None
    if not can_play_in(channel):
        raise StayError(f"Missing Connect or Speak in {channel.name}")
    async with session_lock(guild_id):
        player = get_player(client, guild_id)
        if player is not None and guild.me.voice is not None:
            if guild.me.voice.channel != channel:
                await move(player, channel)
            return player
        await discard_stale(client, guild)
        player = await channel.connect(cls=SquarePlayer)
        # Whatever a kick or a crash left on the channel; `clear_status` held off until now.
        await clear_status(player)
        return player


async def _rejoin(client: Client, guild_id: int) -> None:
    try:
        for attempt in itertools.count():
            await asyncio.sleep(_REJOIN_BACKOFF[min(attempt, len(_REJOIN_BACKOFF) - 1)])
            if guild_id not in _bindings:
                return
            try:
                await join(client, guild_id)
                return
            except Exception as exc:
                console.print(f"[yellow]24/7 rejoin failed in guild[/] [cyan]{guild_id}[/]:", exc)
    finally:
        if _rejoin_tasks.get(guild_id) is asyncio.current_task():
            del _rejoin_tasks[guild_id]


def schedule_rejoin(client: Client, guild_id: int) -> None:
    """
    Keeps trying to get back into the guild's 24/7 channel, backing off between attempts.

    A rejoin already underway absorbs the call, so a burst of disconnect signals costs one loop.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to rejoin.
    """
    if guild_id not in _bindings:
        return
    task = _rejoin_tasks.get(guild_id)
    if task and not task.done():
        return
    _rejoin_tasks[guild_id] = asyncio.create_task(_rejoin(client, guild_id))


async def join_all(client: Client) -> None:
    """
    Joins every bound guild's 24/7 channel, one at a time so a broken guild can't take the rest down.

    Args:
        client (:class:`Client`): The Discord bot client.
    """
    for guild_id in list(_bindings):
        try:
            await join(client, guild_id)
        except Exception:
            schedule_rejoin(client, guild_id)
