import asyncio
import discord
import itertools
import logging
from square.core import Client
from square.db.funcs.music import fetch_all_stay_channels, remove_stay_channel, set_stay_channel
from square.music.core import SquarePlayer, can_play_in, get_player, session_lock

log = logging.getLogger(__name__)

_REJOIN_BACKOFF = (5, 15, 30, 60)

# Kept out of `music/store.py`, whose keys `flush_store` wipes on every teardown.
_bindings: dict[int, int] = {}
_rejoin_tasks: dict[int, asyncio.Task] = {}


class StayError(Exception): ...


async def seed() -> None:
    bindings = await fetch_all_stay_channels()
    _bindings.clear()
    _bindings.update(bindings)


def channel_id(guild_id: int) -> int | None:
    return _bindings.get(guild_id)


def is_stay_channel(guild_id: int, channel_id: int | None) -> bool:
    return channel_id is not None and _bindings.get(guild_id) == channel_id


async def bind(guild_id: int, channel_id: int) -> None:
    await set_stay_channel(guild_id, channel_id)
    _bindings[guild_id] = channel_id


def _cancel_rejoin(guild_id: int) -> None:
    task = _rejoin_tasks.pop(guild_id, None)
    if task and task is not asyncio.current_task():
        task.cancel()


async def unbind(guild_id: int) -> None:
    # Cache first, so a disconnect landing during the DB write doesn't schedule a rejoin.
    _bindings.pop(guild_id, None)
    _cancel_rejoin(guild_id)
    await remove_stay_channel(guild_id)


def forget(guild_id: int) -> None:
    _bindings.pop(guild_id, None)
    _cancel_rejoin(guild_id)


async def move(player: SquarePlayer, channel: discord.VoiceChannel) -> None:
    await channel.guild.change_voice_state(channel=channel)
    # Sonolink only tracks the new channel ID on a move, never the `channel` attribute that every
    # "are you in my voice channel" check reads.
    player.channel = channel


async def resolve(guild: discord.Guild) -> discord.VoiceChannel | None:
    cid = _bindings.get(guild.id)
    if cid is None:
        return None
    channel = guild.get_channel(cid)
    if isinstance(channel, discord.VoiceChannel):
        return channel
    await unbind(guild.id)
    return None


async def join(client: Client, guild_id: int) -> SquarePlayer | None:
    from square.music.player import clear_status, discard_stale

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
                log.warning("24/7 rejoin failed in guild %s: %s", guild_id, exc)
    finally:
        if _rejoin_tasks.get(guild_id) is asyncio.current_task():
            del _rejoin_tasks[guild_id]


def schedule_rejoin(client: Client, guild_id: int) -> None:
    if guild_id not in _bindings:
        return
    task = _rejoin_tasks.get(guild_id)
    if task and not task.done():
        return
    _rejoin_tasks[guild_id] = asyncio.create_task(_rejoin(client, guild_id))


async def join_all(client: Client) -> None:
    for guild_id in list(_bindings):
        try:
            await join(client, guild_id)
        except Exception:
            schedule_rejoin(client, guild_id)
