import sonolink
import time
from core import Client
from sonolink.models import Filters, HistorySettings, InactivitySettings, Playable
from utils import config


class SquarePlayer(sonolink.Player):
    """Custom Sonolink player with additional features for the bot."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("history_settings", HistorySettings(enabled=True, max_items=50))
        super().__init__(*args, **kwargs)
        self.presets: dict[str, Filters] = {}

    @property
    def connected(self) -> bool:
        """Whether the player is bound to a voice channel."""
        return getattr(self, "channel", None) is not None

    async def pause(self) -> None:
        # Sonolink only refreshes its position base on node player-updates (~5s apart); snapshot it
        # here so the interpolated position doesn't jump while paused or right after resuming.
        self._last_position = self.position
        await super().pause()
        self._last_update = time.monotonic()

    async def resume(self) -> None:
        await super().resume()
        self._last_update = time.monotonic()

    async def apply_presets(self) -> None:
        """Applies the combination of all active equalizer presets, or clean audio when none remain."""
        combined = Filters()
        for preset in self.presets.values():
            combined = combined.combine(preset)
        await self.set_filters(combined, seek=True)


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
        scheme = "https" if node["secure"] else "http"
        client.sonolink.create_node(
            uri=f"{scheme}://{node['host']}:{node['port']}",
            password=node["password"],
            id=node["host"],
            auto_reconnect=True,
            retries=None,
            inactivity_settings=InactivitySettings(timeout=60, mode=sonolink.InactivityMode.ALL_BOTS),
        )


def fmt_time(ms: int | float) -> str:
    """Formats a duration in milliseconds as `H:MM:SS` or `M:SS`."""
    total_seconds = ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"
