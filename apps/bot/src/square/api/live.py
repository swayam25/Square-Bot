"""
Live updates for the dashboard, over one WebSocket from the dashboard server.

The server subscribes for a user, a guild and a topic, gets a snapshot right away, then a new one whenever it changes.
Snapshots are whole pieces of state, never diffs: the browser only keeps the latest value, so a dropped one is harmless.
"""

import asyncio
import discord
import logging
import msgspec
from collections.abc import Callable
from dataclasses import dataclass
from litestar import WebSocket, websocket
from litestar.exceptions import NotFoundException, PermissionDeniedException, WebSocketDisconnect
from square.api.auth import provide_guild
from square.api.schemas import PlayerState, QueueState, Snowflake, player_out, queue_out
from square.core import Client
from typing import Literal

log = logging.getLogger(__name__)

Topic = Literal["player", "queue"]
_SNAPSHOTS: dict[Topic, Callable[[Client, discord.Guild], PlayerState | QueueState]] = {
    "player": player_out,
    "queue": queue_out,
}


class Subscribe(msgspec.Struct, tag="sub", tag_field="op"):
    id: int
    guild: Snowflake
    actor: Snowflake
    topic: Topic


class Unsubscribe(msgspec.Struct, tag="unsub", tag_field="op"):
    id: int


class Update(msgspec.Struct, omit_defaults=True):
    id: int
    data: PlayerState | QueueState | None = None
    # The subscription is over: the guild is gone for this user, or they lost Manage Server
    error: Literal["not_found", "forbidden"] | None = None


_decoder = msgspec.json.Decoder(Subscribe | Unsubscribe)
_encoder = msgspec.json.Encoder()


@dataclass
class _Subscription:
    guild_id: int
    actor: int
    topic: Topic
    last: bytes | None = None


class _Connection:
    def __init__(self, socket: WebSocket, client: Client):
        self.socket = socket
        self.client = client
        self.subscriptions: dict[int, _Subscription] = {}
        self._send_lock = asyncio.Lock()  # Pushes come from bot events as well as this socket's own loop

    async def push(self, sub_id: int) -> None:
        """Sends the subscription's snapshot, unless nothing changed since the last one."""
        if (sub := self.subscriptions.get(sub_id)) is None:
            return
        # Access is checked on every push, so losing Manage Server ends the stream instead of leaking updates
        try:
            guild = provide_guild(self.client, str(sub.guild_id), sub.actor)
        except NotFoundException:
            await self._end(sub_id, "not_found")
            return
        except PermissionDeniedException:
            await self._end(sub_id, "forbidden")
            return
        data = _SNAPSHOTS[sub.topic](self.client, guild)
        key = _dedupe_key(data)
        if key == sub.last:
            return
        sub.last = key
        await self._send(Update(id=sub_id, data=data))

    async def _end(self, sub_id: int, error: Literal["not_found", "forbidden"]) -> None:
        del self.subscriptions[sub_id]
        await self._send(Update(id=sub_id, error=error))

    async def _send(self, update: Update) -> None:
        async with self._send_lock:
            await self.socket.send_data(_encoder.encode(update).decode(), mode="text")


def _dedupe_key(data: PlayerState | QueueState) -> bytes:
    """
    The snapshot minus the clock.

    The card re-renders every few seconds just to move its progress bar, and a playing track's position only matters
    when it jumps (a seek), so playback time is compared as when the track started.
    """
    if isinstance(data, PlayerState):
        started = (data.position_at - data.position_ms) // 1000 if data.track and not data.paused else data.position_ms
        data = msgspec.structs.replace(data, position_ms=started, position_at=0)
    return _encoder.encode(data)


_connections: set[_Connection] = set()


async def on_music_update(guild_id: int) -> None:
    """Pushes to every subscription for the guild. Registered as the bot's `music_update` listener."""
    for connection in list(_connections):
        for sub_id, sub in list(connection.subscriptions.items()):
            if sub.guild_id != guild_id:
                continue
            try:
                await connection.push(sub_id)
            except Exception:  # A dropped socket is cleaned up by its own loop
                break


@websocket("/live")
async def live(socket: WebSocket, client: Client) -> None:
    await socket.accept()
    connection = _Connection(socket, client)
    _connections.add(connection)
    try:
        while True:
            try:
                message = _decoder.decode(await socket.receive_data(mode="text"))
            except msgspec.DecodeError:
                await socket.close(code=1008, reason="Bad message")  # Only our own server talks here, so this is a bug
                return
            match message:
                case Subscribe(id=sub_id, guild=guild_id, actor=actor, topic=topic):
                    connection.subscriptions[sub_id] = _Subscription(int(guild_id), int(actor), topic)
                    await connection.push(sub_id)
                case Unsubscribe(id=sub_id):
                    connection.subscriptions.pop(sub_id, None)
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(connection)
