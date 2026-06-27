import asyncio
import lavalink
import random
from music import store

_MIN_POOL = 5  # Fetch fallbacks only when primary yields fewer than this

# Per-guild locks: rapid skipping fires multiple concurrent QueueEndEvent tasks.
# Without a lock, a failing task can flush the store mid-fetch, leaving a None seed.
_locks: dict[int, asyncio.Lock] = {}


def get_lock(guild_id: int) -> asyncio.Lock:
    if guild_id not in _locks:
        _locks[guild_id] = asyncio.Lock()
    return _locks[guild_id]


def cleanup(guild_id: int) -> None:
    _locks.pop(guild_id, None)


async def _fetch(player: lavalink.DefaultPlayer, query: str) -> list[lavalink.AudioTrack]:
    try:
        result = await player.node.get_tracks(query)
    except Exception:
        return []
    if not result or not result.tracks:
        return []
    return list(result.tracks)


def _dedup(tracks: list[lavalink.AudioTrack]) -> list[lavalink.AudioTrack]:
    seen: set[str] = set()
    out: list[lavalink.AudioTrack] = []
    for t in tracks:
        if t.identifier not in seen:
            seen.add(t.identifier)
            out.append(t)
    return out


def _build_queries(track: lavalink.AudioTrack) -> tuple[list[str], list[str]]:
    """
    Return (`primary_queries`, `fallback_queries`) for the track's source.

    Primary queries target the same source so recommendations stay consistent.
    Fallback queries cross to YouTube Music only when primary yields nothing.
    """
    source = (track.source_name or "").lower()
    title_author = f"{track.title} {track.author}"

    if source == "spotify":
        return (
            [f"sprec:seed_tracks={track.identifier}&limit=10"],
            [f"ytmsearch:{title_author}"],
        )
    elif source == "soundcloud":
        return (
            [f"scsearch:{track.author}", f"scsearch:{title_author}"],
            [f"ytmsearch:{title_author}"],
        )
    else:
        return (
            [
                f"https://music.youtube.com/watch?v={track.identifier}&list=RD{track.identifier}",
                f"ytrec:{track.identifier}",
            ],
            [f"ytmsearch:{title_author}"],
        )


async def fetch_recommendations(
    player: lavalink.DefaultPlayer,
    guild_id: int,
) -> list[lavalink.AudioTrack]:
    """
    Return a shuffled pool of recommended tracks that aren't in recent history.

    Strategy:
      1. Build source-specific primary queries (Spotify → `sprec:`, SoundCloud → `scsearch:`, YouTube → YTM radio + `ytrec:`) so recommendations stay on the same platform.
      2. If the primary pool is thin, fall back to ytmsearch: concurrently.
      3. Filter against autoplay history, deduplicate, then shuffle.
    """
    last = store.last_track(guild_id)
    if last is None:
        return []

    history_ids: set[str] = set(store.autoplay_history(guild_id))
    primary_queries, fallback_queries = _build_queries(last)

    primary_results = await asyncio.gather(*[_fetch(player, q) for q in primary_queries])
    primary = [t for batch in primary_results for t in batch]

    primary_filtered = [t for t in primary if t.identifier not in history_ids]
    if len(primary_filtered) >= _MIN_POOL:
        pool = primary_filtered
    else:
        fallback_results = await asyncio.gather(*[_fetch(player, q) for q in fallback_queries])
        fallback = [t for batch in fallback_results for t in batch]
        merged = primary + fallback
        pool = [t for t in merged if t.identifier not in history_ids]

    pool = _dedup(pool)
    random.shuffle(pool)
    return pool
