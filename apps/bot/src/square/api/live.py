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
from square.api.auth import provide_member_guild
from square.api.schemas import (
    PlayerState,
    QueueState,
    Snowflake,
    Track,
    history_out,
    live_player,
    player_for,
    player_shared,
    queue_out,
)
from square.core import Client
from typing import Literal

log = logging.getLogger(__name__)

Topic = Literal["player", "queue", "history"]
Snapshot = PlayerState | QueueState | list[Track]
# What every viewer of a guild gets. The player topic adds the viewer's own part on top, see `_Connection.push`
_SNAPSHOTS: dict[Topic, Callable[[Client, discord.Guild], Snapshot]] = {
    "player": player_shared,
    "queue": queue_out,
    "history": lambda client, guild: history_out(live_player(client, guild.id)),
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
    data: Snapshot | None = None
    # The subscription is over: the guild is gone for this user, or they lost access to the topic
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

    async def push(self, sub_id: int, shared: _Shared | None = None) -> None:
        """Sends the subscription's snapshot, unless nothing changed since the last one."""
        if (sub := self.subscriptions.get(sub_id)) is None:
            return
        # Access is checked on every push, so leaving the server ends the stream instead of leaking updates.
        # Every topic so far is music, which any member may watch
        try:
            guild = provide_member_guild(self.client, str(sub.guild_id), sub.actor)
        except NotFoundException:
            await self._end(sub_id, "not_found")
            return
        except PermissionDeniedException:
            await self._end(sub_id, "forbidden")
            return
        data, key = (shared or _Shared()).get(self.client, guild, sub.topic)
        if isinstance(data, PlayerState):
            data = player_for(self.client, guild, guild.get_member(sub.actor), data)
            key += _encoder.encode(data.viewer)
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


def _dedupe_key(data: Snapshot) -> bytes:
    """
    The snapshot minus the clock.

    The card re-renders every few seconds just to move its progress bar, and a playing track's position only matters
    when it jumps (a seek), so playback time is compared as when the track started.
    """
    if isinstance(data, PlayerState):
        started = (data.position_at - data.position_ms) // 1000 if data.track and not data.paused else data.position_ms
        data = msgspec.structs.replace(data, position_ms=started, position_at=0)
    return _encoder.encode(data)


class _Shared:
    """A guild's snapshots for one update, built and encoded once however many tabs are watching."""

    def __init__(self) -> None:
        self._built: dict[Topic, tuple[Snapshot, bytes]] = {}

    def get(self, client: Client, guild: discord.Guild, topic: Topic) -> tuple[Snapshot, bytes]:
        if topic not in self._built:
            data = _SNAPSHOTS[topic](client, guild)
            self._built[topic] = (data, _dedupe_key(data))
        return self._built[topic]


_connections: set[_Connection] = set()


async def on_music_update(guild_id: int) -> None:
    """Pushes to every subscription for the guild. Registered as the bot's `music_update` listener."""
    shared = _Shared()
    for connection in list(_connections):
        for sub_id, sub in list(connection.subscriptions.items()):
            if sub.guild_id != guild_id:
                continue
            try:
                await connection.push(sub_id, shared)
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
