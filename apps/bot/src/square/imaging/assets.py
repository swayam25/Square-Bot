import aiohttp
import asyncio
import discord
from collections import OrderedDict

_CACHE_SIZE = 256
_MAX_DOWNLOAD = 8 * 1024 * 1024
# Keyed by asset key and size. The key changes with the picture, so entries never go stale. URLs use size 0.
_cache: OrderedDict[tuple[str, int], bytes] = OrderedDict()
_session: aiohttp.ClientSession | None = None


def _remember(key: tuple[str, int], data: bytes) -> bytes:
    _cache[key] = data
    if len(_cache) > _CACHE_SIZE:
        _cache.popitem(last=False)
    return data


def _cached(key: tuple[str, int]) -> bytes | None:
    if (data := _cache.get(key)) is not None:
        _cache.move_to_end(key)
    return data


async def fetch(asset: discord.Asset | None, size: int = 128) -> bytes | None:
    """
    Downloads an avatar or icon as a static PNG, cached across renders.

    Args:
        asset (:class:`discord.Asset` | None): The asset, e.g. `member.display_avatar` or `guild.icon`.
        size (int): The size to request, a power of 2 between 16 and 4096.

    Returns:
        bytes | None: The PNG, or None when there's no asset or Discord couldn't serve it.
    """
    if asset is None:
        return None
    key = (asset.key, size)
    if (cached := _cached(key)) is not None:
        return cached
    try:
        data = await asset.with_size(size).with_format("png").read()
    except discord.HTTPException:
        return None
    return _remember(key, data)


async def fetch_url(url: str | None) -> bytes | None:
    """
    Downloads an image from outside Discord, like a track's artwork, cached across renders.

    Returns:
        bytes | None: The file, or None when there's no URL, it fails, or it's bigger than 8 MB.
    """
    global _session
    if not url:
        return None
    if (cached := _cached((url, 0))) is not None:
        return cached
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
    try:
        async with _session.get(url) as response:
            if response.status != 200 or (response.content_length or 0) > _MAX_DOWNLOAD:
                return None
            data = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                data += chunk
                if len(data) > _MAX_DOWNLOAD:
                    return None
    except aiohttp.ClientError, TimeoutError:
        return None
    return _remember((url, 0), bytes(data))


async def close() -> None:
    """Closes the session `fetch_url` uses. Called on bot shutdown."""
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


async def fetch_many(assets: list[discord.Asset | None], size: int = 128) -> list[bytes | None]:
    return list(await asyncio.gather(*(fetch(asset, size) for asset in assets)))


def default_avatar(client: discord.Client, user_id: int) -> discord.Asset:
    """
    Discord's default avatar for an account the bot can't look up any more, e.g. a deleted one.

    Picked from the ID the way Discord does for accounts on the new username system, the same as pycord's
    `User.default_avatar`. Users the bot can see already get this through `display_avatar`.
    """
    return discord.Asset._from_default_avatar(client._connection, (user_id >> 22) % 6)
