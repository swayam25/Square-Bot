import aiohttp
import re
from bisect import bisect_right
from sonolink.models import Playable

API_URL = "https://lrclib.net/api"
HEADERS = {"User-Agent": "Square (Discord Bot)"}

# LRC timestamp tag, e.g. [01:23.45]
_lrc_rx = re.compile(r"\[(\d+):(\d{1,2}(?:\.\d+)?)\]")
# Title/author noise that breaks lyrics lookups
_noise_rx = re.compile(
    r"\s*[(\[][^)\]]*(official|video|audio|lyric|visuali[sz]er|remaster|hd|4k|mv)[^)\]]*[)\]]",
    re.IGNORECASE,
)


def _clean_query(track: Playable) -> tuple[str, str]:
    """
    Returns a (title, artist) pair stripped of upload noise like "(Official Video)" or "- Topic".

    Args:
        track (:class:`Playable`): The track to build the lookup query from.
    """
    title = _noise_rx.sub("", track.title).strip()
    artist = re.sub(r"\s*-\s*Topic$", "", track.author or "").strip()
    return title, artist


def parse_lrc(text: str) -> list[tuple[int, str]]:
    """
    Parses LRC-formatted lyrics into a timestamp-sorted list of (position_ms, line) pairs.

    Handles multiple timestamp tags on a single line (repeated choruses).

    Args:
        text (str): The raw LRC lyrics text.

    Returns:
        list[tuple[int, str]]: Timestamped lines sorted by position.
    """
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        tags = list(_lrc_rx.finditer(raw))
        if not tags:
            continue
        content = raw[tags[-1].end() :].strip()
        for tag in tags:
            position = int(int(tag.group(1)) * 60_000 + float(tag.group(2)) * 1000)
            lines.append((position, content))
    lines.sort(key=lambda line: line[0])
    return lines


async def fetch(track: Playable) -> list[tuple[int, str]]:
    """
    Fetches synced lyrics for a track from LRCLIB.

    Tries an exact signature match (title + artist + duration) first, then falls back to a search, keeping only results whose duration is within 10 seconds of the track.

    Args:
        track (:class:`Playable`): The track to fetch lyrics for.

    Returns:
        list[tuple[int, str]]: Timestamped lyric lines, or an empty list if none were found.
    """
    if track.is_stream:
        return []
    title, artist = _clean_query(track)
    duration_sec = round(track.length / 1000)
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
            async with session.get(
                f"{API_URL}/get",
                params={"track_name": title, "artist_name": artist, "duration": str(duration_sec)},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("syncedLyrics"):
                        return parse_lrc(data["syncedLyrics"])
            async with session.get(
                f"{API_URL}/search",
                params={"track_name": title, "artist_name": artist},
            ) as resp:
                if resp.status != 200:
                    return []
                results = await resp.json()
        for result in results:
            if result.get("syncedLyrics") and abs(result.get("duration", 0) - duration_sec) <= 10:
                return parse_lrc(result["syncedLyrics"])
    except Exception:
        return []
    return []


def window(lines: list[tuple[int, str]], position_ms: int) -> tuple[int, str, str, str]:
    """
    Returns the lyrics window around the playback position.

    Args:
        lines (list[tuple[int, str]]): Timestamped lyric lines sorted by position.
        position_ms (int): The current playback position in milliseconds.

    Returns:
        tuple[int, str, str, str]: (index, previous, current, next) where index is -1 before the first line and absent lines are empty strings.
    """
    idx = bisect_right([ts for ts, _ in lines], position_ms) - 1
    prev = lines[idx - 1][1] if idx > 0 else ""
    current = lines[idx][1] if idx >= 0 else ""
    upcoming = lines[idx + 1][1] if idx + 1 < len(lines) else ""
    return idx, prev, current, upcoming
