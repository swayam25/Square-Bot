import aiohttp


async def read(session: aiohttp.ClientSession, url: str, limit: int) -> bytes | None:
    try:
        async with session.get(url) as response:
            if response.status != 200 or (response.content_length or 0) > limit:
                return None
            data = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                data += chunk
                if len(data) > limit:
                    return None
    except aiohttp.ClientError, TimeoutError:
        return None
    return bytes(data)
