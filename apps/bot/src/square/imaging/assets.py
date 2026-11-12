import aiohttp
import asyncio
import discord
from collections import OrderedDict

_CACHE_SIZE = 256
_MAX_DOWNLOAD = 8 * 1024 * 1024
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
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


async def fetch_many(assets: list[discord.Asset | None], size: int = 128) -> list[bytes | None]:
    return list(await asyncio.gather(*(fetch(asset, size) for asset in assets)))


def default_avatar(client: discord.Client, user_id: int) -> discord.Asset:
    return discord.Asset._from_default_avatar(client._connection, (user_id >> 22) % 6)
