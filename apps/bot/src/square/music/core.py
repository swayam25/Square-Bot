import asyncio
import discord
import sonolink
import time
from sonolink.gateway.player.handlers._autoplay import AutoPlayHandler
from sonolink.models import Filters, HistorySettings, InactivitySettings, Playable
from square.core import Client
from square.utils import config
from square.utils.emoji import Icon, emoji

INACTIVITY_TIMEOUT = 60
_MOVE_CLOSE_CODES = (4014, 4022)


class SquareAutoPlay(AutoPlayHandler):
    """Seeds autoplay from the track's own service. Sonolink builds a YouTube radio from any ID, Spotify ones included."""

    _twin: str | None = None
    _staging = False

    async def stage(self) -> None:
        """Queues picks without playing one, so the Autoplay list fills the moment autoplay turns on."""
        queue = self._player.queue
        if self._player.current is None or len(queue) or queue.autoplay_tracks or self._lock.locked():
            return
        async with self._lock:
            self._staging = True
            try:
                await self._fill_auto_queue()
            finally:
                self._staging = False

    async def _fill_auto_queue(self) -> Playable | None:
        history = self._player.queue.history
        seed = self._player.current or (history[-1] if history else None)
        source = getattr(seed, "source_name", None)
        self._twin = await self._youtube_twin(seed) if source == "applemusic" else None
        if source == "spotify":
            self._settings.provider = sonolink.SearchProvider.SPOTIFY
        elif self._twin:
            self._settings.provider = sonolink.SearchProvider.YOUTUBE.format(identifier=self._twin)
        else:
            self._settings.provider = sonolink.SearchProvider.YOUTUBE
        return await super()._fill_auto_queue()

    async def _apply_discovery(self, tracks: list[Playable]) -> Playable | None:
        tracks = [track for track in tracks if track.identifier != self._twin]
        if not self._staging:
            return await super()._apply_discovery(tracks)
        self._player.queue.put_autoplay(tracks[: self._settings.discovery_count])
        return None

    async def _youtube_twin(self, track: Playable) -> str | None:
        try:
            search = await self._player.node.search_track(
                f"{track.author} - {track.title}", source=sonolink.TrackSourceType.YOUTUBE_MUSIC
            )
        except Exception:
            return None
        if search.is_error() or search.is_empty() or not isinstance(search.result, list):
            return None
        return search.result[0].identifier


class SquarePlayer(sonolink.Player):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("history_settings", HistorySettings(enabled=True, max_items=50))
        super().__init__(*args, **kwargs)
        self._autoplay_handler: SquareAutoPlay = SquareAutoPlay(self, settings=self._autoplay_handler._settings)
        self.presets: dict[str, Filters] = {}
        self._empty_task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return getattr(self, "channel", None) is not None

    async def resume(self) -> None:
        # Sonolink freezes the position on pause but never restarts its clock on resume, so the
        # interpolated position would jump by however long the player sat paused.
        await super().resume()
        self._last_update = time.monotonic()

    @property
    def shuffled(self) -> bool:
        return self.queue.shuffle_mode is sonolink.ShuffleMode.PERSISTENT

    def toggle_shuffle(self) -> bool:
        self.queue.shuffle_mode = sonolink.ShuffleMode.DEFAULT if self.shuffled else sonolink.ShuffleMode.PERSISTENT
        return self.shuffled

    @property
    def autoplay_on(self) -> bool:
        return self.autoplay is sonolink.AutoPlayMode.ENABLED

    async def toggle_autoplay(self) -> bool:
        self.autoplay = sonolink.AutoPlayMode.DISABLED if self.autoplay_on else sonolink.AutoPlayMode.ENABLED
        if self.autoplay_on:
            await self._autoplay_handler.stage()
        else:
            # Sonolink plays staged picks even with autoplay off, and has no public call to drop them
            self.queue._autoplay_items.clear()
        return self.autoplay_on

    async def settle(self, started: Playable, began: float) -> bool:
        """
        Waits for sonolink to catch up with a track Lavalink just started, and returns whether it is playing.

        Lavalink can announce a track before the play request returns, so `current` may still be the previous one and
        its last position update can land after the new track began.

        Args:
            started (:class:`Playable`): The track from the start event.
            began (float): `time.monotonic()` when the event arrived.
        """
        for _ in range(20):
            if self.current is None or self.current.identifier == started.identifier:
                break
            await asyncio.sleep(0.1)
        if self.current is None:
            return False
        self._last_position = started.position
        self._last_update = began
        return True

    async def apply_presets(self) -> None:
        combined = Filters()
        for preset in self.presets.values():
            combined = combined.combine(preset)
        await self.set_filters(combined, seek=True)

    def cleanup(self) -> None:
        self.cancel_empty_timer()
        super().cleanup()

    async def _dispatch_event(self, data: dict) -> None:
        # Sonolink disconnects on these closes, but a bot still in a channel was only moved.
        # A kick leaves no channel and falls through to the disconnect.
        if (
            data.get("type") == "WebSocketClosedEvent"
            and data.get("code") in _MOVE_CLOSE_CODES
            and self.guild.me.voice is not None
            and self.guild.me.voice.channel is not None
        ):
            await self._dispatch_voice_update()
            return
        await super()._dispatch_event(data)

    def cancel_empty_timer(self) -> None:
        task = self._empty_task
        self._empty_task = None
        if task and task is not asyncio.current_task():
            task.cancel()

    def _check_inactivity(self) -> None:
        # Sonolink's timer disconnects, so a 24/7 player swaps it for one that only stops playback.
        from square.music import stay

        if not stay.is_stay_channel(self.guild.id, getattr(self.channel, "id", None)):
            super()._check_inactivity()
            return
        self._stop_inactivity_timer()
        voice = self.guild.me.voice
        listening = bool(voice and voice.channel and any(not member.bot for member in voice.channel.members))
        if self.current is None or listening:
            self.cancel_empty_timer()
        elif self._empty_task is None:
            self._empty_task = asyncio.create_task(self._stop_when_empty())

    async def _stop_when_empty(self) -> None:
        from square.music.player import stop_player
        from square.music.utils import music_log

        await asyncio.sleep(INACTIVITY_TIMEOUT)
        # Detached before stopping: the stop ends the track, and the check that follows a track end
        # would otherwise cancel this task halfway through its own cleanup.
        self._empty_task = None
        if self.current is None:
            return
        await music_log(self.guild.id, f"{emoji.stop} Stopped the player since everyone left.", color=config.color.red)
        await stop_player(self, self.guild)


_session_locks: dict[int, asyncio.Lock] = {}


def session_lock(guild_id: int) -> asyncio.Lock:
    """
    Returns the guild's playback lock, creating it on first use.

    Connecting the bot and starting the first track are both check-then-act across an await:
    ``get_player`` stays None until the voice handshake lands, and ``player.current`` stays None
    until the node answers. Two requests arriving together would otherwise connect twice, or both
    start a track and drop one from the queue. The request channel makes that ordinary, since the
    rate limit is per member and two people can type at once.

    Args:
        guild_id (int): The guild to serialize playback changes for.
    """
    return _session_locks.setdefault(guild_id, asyncio.Lock())


def drop_session_lock(guild_id: int) -> None:
    lock = _session_locks.get(guild_id)
    if lock is not None and not lock.locked():
        del _session_locks[guild_id]


def can_play_in(channel: discord.abc.Connectable) -> bool:
    permissions = channel.permissions_for(channel.guild.me)
    return permissions.connect and permissions.speak


def get_player(client: Client, guild_id: int) -> SquarePlayer | None:
    guild = client.get_guild(guild_id)
    voice = guild.voice_client if guild else None
    return voice if isinstance(voice, SquarePlayer) else None


def requester_id(player: SquarePlayer, track: Playable) -> int | None:
    rid = getattr(track.extras, "requester", None)
    if rid is None and track.autoplay:
        return player.client.user.id
    return rid


def tag_requester(client: Client, track: Playable, user_id: int) -> Playable:
    fresh = Playable(client=client.sonolink, data=track.data, playlist=track.playlist)
    fresh.extras.requester = user_id
    return fresh


async def fetch_node_info(node: sonolink.Node) -> tuple[sonolink.models.ServerInfo | None, str]:
    start = time.monotonic()
    try:
        info = await node.fetch_info()
    except Exception:
        return None, "N/A"
    return info, f"{round((time.monotonic() - start) * 1000)}ms"


def register_nodes(client: Client) -> None:
    for node in config.lavalink:
        if client.sonolink.get_node(node["host"]) is not None:
            continue
        client.sonolink.create_node(
            host=node["host"],
            port=node["port"],
            secure=node["secure"],
            password=node["password"],
            id=node["host"],
            regions=node.get("regions"),
            auto_reconnect=True,
            retries=None,
            inactivity_settings=InactivitySettings(timeout=INACTIVITY_TIMEOUT, mode=sonolink.InactivityMode.ALL_BOTS),
        )


LOOP_LABELS = {
    sonolink.QueueMode.NORMAL: "Disabled",
    sonolink.QueueMode.LOOP: "Track",
    sonolink.QueueMode.LOOP_ALL: "Queue",
}


def loop_emoji(mode: sonolink.QueueMode) -> Icon:
    if mode is sonolink.QueueMode.LOOP:
        return emoji.loop_one
    return emoji.loop if mode is sonolink.QueueMode.LOOP_ALL else emoji.loop_white


def loop_action(mode: sonolink.QueueMode) -> str:
    if mode is sonolink.QueueMode.NORMAL:
        return "disabled loop"
    return f"enabled {LOOP_LABELS[mode].lower()} loop"


def fmt_time(ms: int | float) -> str:
    total_seconds = ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"
