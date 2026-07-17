import aiohttp
import asyncio
import discord
import lavalink
from core import Client
from discord.voice import VoiceProtocol
from lavalink.errors import ClientError, RequestError
from time import monotonic
from utils import config

# Errors meaning the node itself is unreachable (dead host, refused/timed out connection),
# as opposed to RequestError where the node responded but rejected the request.
NODE_CONNECTION_ERRORS = (ClientError, aiohttp.ClientError, asyncio.TimeoutError, OSError)


class Player(lavalink.DefaultPlayer):
    """
    DefaultPlayer with an accurate local position estimate.

    lavalink.py only refreshes its position base (`_last_position`/`_last_update`) on node player-update events, which arrive ~5s apart.
    That leaves `position` stale right after play, seek, and pause/resume - breaking anything that reads it live (synced lyrics, progress bar).
    These overrides reset the base locally the moment the state-changing request completes.
    """

    async def play(self, *args, **kwargs):
        try:
            await super().play(*args, **kwargs)
        except RequestError:
            raise  # lavalink already dispatches PlayerErrorEvent for its own request errors
        except NODE_CONNECTION_ERRORS as error:
            # The node died mid-request: retry once on another available node before giving up.
            if not await self._failover_play():
                self.client._dispatch_event(lavalink.PlayerErrorEvent(self, error))
                raise
        except Exception as error:
            # Raw connection errors (node died) escape lavalink's transport unwrapped, skipping
            # its PlayerErrorEvent path - dispatch it ourselves so the player gets cleaned up.
            self.client._dispatch_event(lavalink.PlayerErrorEvent(self, error))
            raise
        self._last_update = int(monotonic() * 1000)

    async def _failover_play(self) -> bool:
        """
        Moves the player to another available node and replays the track the dead node dropped.

        `_next` holds the track of the failed request - the transport only clears it once a track
        actually starts, so it's None when the failure happened outside a track request (e.g. the
        queue-end `stop()` call), in which case there is nothing to replay and no failover happens.
        """
        track = self._next
        backup = self.client.node_manager.find_ideal_node(exclude=[self.node] if self.node else None)
        if track is None or backup is None:
            return False
        try:
            self.current = None  # change_node would otherwise resume the pre-failure track; we replay `_next` ourselves
            await self.change_node(backup)
            await self.play_track(track)
        except Exception:
            return False
        return True

    async def seek(self, position: int):
        await super().seek(position)
        self._last_position = position
        self._last_update = int(monotonic() * 1000)

    async def set_pause(self, pause: bool):
        if pause:
            self._last_position = self.position
        await super().set_pause(pause)
        self._last_update = int(monotonic() * 1000)


async def load_tracks(player: lavalink.DefaultPlayer, query: str) -> lavalink.LoadResult:
    """
    Loads tracks with automatic node failover.

    Tries the player's node first, then every other available node (least loaded first) when a node
    is unreachable or reports a load error. On success via a fallback node the player is moved to it,
    so playback and later requests stop hitting the dead node.

    Raises :class:`ClientError` when every node is unreachable.
    """
    candidates = [player.node] if player.node is not None and player.node.available else []
    for node in sorted(player.client.node_manager.available_nodes, key=lambda n: n.penalty):
        if node not in candidates:
            candidates.append(node)
    if not candidates and player.node is not None:
        candidates = [player.node]  # No node is marked available; its REST API may still respond

    error_result: lavalink.LoadResult | None = None
    last_error: Exception | None = None
    for node in candidates:
        try:
            result = await node.get_tracks(query)
        except NODE_CONNECTION_ERRORS as error:
            last_error = error
            continue
        if result.load_type == lavalink.LoadType.ERROR:
            error_result = result  # The node answered but its source failed; another node may serve it
            continue
        if node is not player.node:
            try:
                await player.change_node(node)
            except NODE_CONNECTION_ERRORS as error:
                last_error = error
                continue
        return result

    if error_result is not None:
        return error_result
    raise ClientError("All lavalink nodes are unavailable.") from last_error


def add_nodes(client: lavalink.Client):
    """Registers every configured lavalink node with the client."""
    for node in config.lavalink:
        client.add_node(
            host=node["host"],
            port=node["port"],
            password=node["password"],
            region=node["region"],
            ssl=node["secure"],
            name=node["host"],
        )


class LavalinkVoiceClient(VoiceProtocol):
    def __init__(self, client: Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False

        if self.client.lavalink is None:
            self.client.lavalink = lavalink.Client(client.user.id, player=Player)
            add_nodes(self.client.lavalink)
        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        await self.lavalink.voice_update_handler({"t": "VOICE_SERVER_UPDATE", "d": data})

    async def on_voice_state_update(self, data):
        channel_id = data["channel_id"]
        if not channel_id:
            await self._destroy()
            return
        self.channel = self.client.get_channel(int(channel_id))
        await self.lavalink.voice_update_handler({"t": "VOICE_STATE_UPDATE", "d": data})

    async def connect(
        self, *, timeout: float, reconnect: bool, self_deaf: bool = True, self_mute: bool = False
    ) -> None:
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_deaf=self_deaf, self_mute=self_mute)

    async def disconnect(self, *, force: bool = False) -> None:
        player: lavalink.DefaultPlayer = self.lavalink.player_manager.get(self.channel.guild.id)
        if not force and (not player or not player.is_connected):
            return
        await self.channel.guild.change_voice_state(channel=None)
        if player:
            player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()
        if self._destroyed:
            return
        self._destroyed = True
        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except Exception:
            pass  # Player is already removed from cache; the node request may fail if it's unreachable
