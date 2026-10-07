import asyncio
import discord
import sonolink
import time
from core import Client
from sonolink.models import Filters, HistorySettings, InactivitySettings, Playable
from utils import config
from utils.emoji import emoji

INACTIVITY_TIMEOUT = 60
# Voice WS close codes Discord sends when it ends the bot's call, a channel move included.
_MOVE_CLOSE_CODES = (4014, 4022)


class SquarePlayer(sonolink.Player):
    """Custom Sonolink player with additional features for the bot."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("history_settings", HistorySettings(enabled=True, max_items=50))
        super().__init__(*args, **kwargs)
        self.presets: dict[str, Filters] = {}
        self._empty_task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        """Whether the player is bound to a voice channel."""
        return getattr(self, "channel", None) is not None

    async def resume(self) -> None:
        # Sonolink freezes the position on pause but never restarts its clock on resume, so the
        # interpolated position would jump by however long the player sat paused.
        await super().resume()
        self._last_update = time.monotonic()

    @property
    def shuffled(self) -> bool:
        """Whether the queue plays in shuffled order."""
        return self.queue.shuffle_mode is sonolink.ShuffleMode.PERSISTENT

    def toggle_shuffle(self) -> bool:
        """Flips shuffle and returns whether it is now on."""
        self.queue.shuffle_mode = sonolink.ShuffleMode.DEFAULT if self.shuffled else sonolink.ShuffleMode.PERSISTENT
        return self.shuffled

    @property
    def autoplay_on(self) -> bool:
        """Whether autoplay picks the next track once the queue runs dry."""
        return self.autoplay is sonolink.AutoPlayMode.ENABLED

    def toggle_autoplay(self) -> bool:
        """Flips autoplay and returns whether it is now on."""
        self.autoplay = sonolink.AutoPlayMode.DISABLED if self.autoplay_on else sonolink.AutoPlayMode.ENABLED
        return self.autoplay_on

    async def apply_presets(self) -> None:
        """Applies the combination of all active equalizer presets, or clean audio when none remain."""
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
        """Calls off a pending empty-channel stop, unless it is the one running right now."""
        task = self._empty_task
        self._empty_task = None
        if task and task is not asyncio.current_task():
            task.cancel()

    def _check_inactivity(self) -> None:
        # Sonolink's timer disconnects, so a 24/7 player swaps it for one that only stops playback.
        from music import stay

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
        from music.player import stop_player
        from music.utils import music_log

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
    """Forgets a guild's playback lock, unless something is holding it right now."""
    lock = _session_locks.get(guild_id)
    if lock is not None and not lock.locked():
        del _session_locks[guild_id]


def can_play_in(channel: discord.abc.Connectable) -> bool:
    """Whether the bot holds the permissions it needs to play in a voice channel."""
    permissions = channel.permissions_for(channel.guild.me)
    return permissions.connect and permissions.speak


def get_player(client: Client, guild_id: int) -> SquarePlayer | None:
    """Returns the guild's active player, or None when the bot isn't connected there."""
    guild = client.get_guild(guild_id)
    voice = guild.voice_client if guild else None
    return voice if isinstance(voice, SquarePlayer) else None


def requester_id(player: SquarePlayer, track: Playable) -> int | None:
    """Returns the requesting user's ID for a track; autoplay-discovered tracks belong to the bot."""
    rid = getattr(track.extras, "requester", None)
    if rid is None and track.autoplay:
        return player.client.user.id
    return rid


def tag_requester(client: Client, track: Playable, user_id: int) -> Playable:
    """Returns a fresh copy of the track tagged with its requester."""
    fresh = Playable(client=client.sonolink, data=track.data, playlist=track.playlist)
    fresh.extras.requester = user_id
    return fresh


async def fetch_node_info(node: sonolink.Node) -> tuple[sonolink.models.ServerInfo | None, str]:
    """Fetches a node's info and measures its REST round-trip latency; returns (None, "N/A") if unreachable."""
    start = time.monotonic()
    try:
        info = await node.fetch_info()
    except Exception:
        return None, "N/A"
    return info, f"{round((time.monotonic() - start) * 1000)}ms"


def register_nodes(client: Client) -> None:
    """Registers every configured lavalink node with the sonolink client. Safe to call repeatedly."""
    for node in config.lavalink:
        if client.sonolink.get_node(node["host"]) is not None:
            continue
        client.sonolink.create_node(
            host=node["host"],
            port=node["port"],
            secure=node["secure"],
            password=node["password"],
            id=node["host"],
            auto_reconnect=True,
            retries=None,
            inactivity_settings=InactivitySettings(timeout=INACTIVITY_TIMEOUT, mode=sonolink.InactivityMode.ALL_BOTS),
        )


LOOP_LABELS = {
    sonolink.QueueMode.NORMAL: "Disabled",
    sonolink.QueueMode.LOOP: "Track",
    sonolink.QueueMode.LOOP_ALL: "Queue",
}


def loop_emoji(mode: sonolink.QueueMode) -> str:
    """Returns the emoji for a loop mode."""
    if mode is sonolink.QueueMode.LOOP:
        return emoji.loop_one
    return emoji.loop if mode is sonolink.QueueMode.LOOP_ALL else emoji.loop_white


def loop_action(mode: sonolink.QueueMode) -> str:
    """Describes switching to a loop mode, e.g. "enabled track loop"."""
    if mode is sonolink.QueueMode.NORMAL:
        return "disabled loop"
    return f"enabled {LOOP_LABELS[mode].lower()} loop"


def fmt_time(ms: int | float) -> str:
    """Formats a duration in milliseconds as `H:MM:SS` or `M:SS`."""
    total_seconds = ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"
