"""
S3-compatible object storage, shared by every feature.

Keys are `{guild_id}/{area}/...` from `key()`
"""

import aiohttp
import logging
from aiobotocore.config import AioConfig
from aiobotocore.session import get_session
from botocore.exceptions import BotoCoreError, ClientError
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from dataclasses import dataclass
from square.utils.config import storage as settings
from urllib.parse import quote

log = logging.getLogger(__name__)

# S3 refuses multipart parts under 5 MiB, except the last one
PART_SIZE = 8 * 1024 * 1024
DELETE_BATCH = 1000
CHUNK = 256 * 1024
# Types served inline from the dashboard's origin. Anything else, SVG included since it can carry scripts, is stored as a download
INLINE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/mp4",
    "audio/flac",
}

_stack: AsyncExitStack | None = None
_client = None
_http: aiohttp.ClientSession | None = None


class StorageError(Exception):
    pass


class Oversized(StorageError):
    pass


class RangeNotSatisfiable(Exception):
    def __init__(self, total: int):
        super().__init__(f"The range is outside the object's {total} bytes")
        self.total = total


# Errors from storage calls and downloads
ERRORS = (BotoCoreError, ClientError, StorageError, aiohttp.ClientError, TimeoutError)


@dataclass(frozen=True)
class Object:
    chunks: AsyncIterator[bytes]
    content_type: str
    disposition: str
    length: int
    total: int
    content_range: str | None


def key(guild_id: int, area: str, *parts: int | str) -> str:
    return "/".join([str(guild_id), area, *map(str, parts)])


def prefix(guild_id: int, *parts: int | str) -> str:
    return "".join(f"{part}/" for part in (guild_id, *parts))


def describe(content_type: str | None, filename: str) -> tuple[str, str]:
    """The type and disposition to store an uploaded file with, so it can never be served as a page."""
    kind = (content_type or "").split(";", 1)[0].strip().lower()
    inline = kind in INLINE_TYPES
    disposition = f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(filename, safe='')}"
    return (kind if inline else "application/octet-stream"), disposition


def _s3():
    if _client is None:
        raise RuntimeError("Storage isn't started")
    return _client


def _code(error: ClientError) -> str:
    return error.response.get("Error", {}).get("Code", "")


async def init() -> None:
    global _stack, _client, _http
    _stack = AsyncExitStack()
    _client = await _stack.enter_async_context(
        get_session().create_client(
            "s3",
            endpoint_url=settings.endpoint,
            region_name=settings.region,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            config=AioConfig(
                s3={"addressing_style": "path"},
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
    )
    _http = await _stack.enter_async_context(
        aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(sock_connect=10, sock_read=30))
    )
    buckets = await _client.list_buckets()
    if not any(bucket["Name"] == settings.bucket for bucket in buckets.get("Buckets", [])):
        await _client.create_bucket(Bucket=settings.bucket)
        log.info("Created the storage bucket %s", settings.bucket)
    log.info("Storage ready")


async def close() -> None:
    global _stack, _client, _http
    if _stack is not None:
        await _stack.aclose()
    _stack = _client = _http = None


async def put(key: str, chunks: AsyncIterator[bytes], content_type: str, disposition: str) -> int:
    """Uploads a stream without holding more than one part in memory. Returns the bytes written."""
    s3 = _s3()
    headers = {"Bucket": settings.bucket, "Key": key}
    described = {**headers, "ContentType": content_type, "ContentDisposition": disposition}
    buffer = bytearray()
    upload_id: str | None = None
    parts: list[dict] = []
    total = 0

    async def flush(data: bytes) -> None:
        nonlocal upload_id
        if upload_id is None:
            upload_id = (await s3.create_multipart_upload(**described))["UploadId"]
        number = len(parts) + 1
        sent = await s3.upload_part(**headers, UploadId=upload_id, PartNumber=number, Body=data)
        parts.append({"PartNumber": number, "ETag": sent["ETag"]})

    try:
        async for chunk in chunks:
            buffer += chunk
            total += len(chunk)
            while len(buffer) >= PART_SIZE:
                await flush(bytes(buffer[:PART_SIZE]))
                del buffer[:PART_SIZE]
        if upload_id is None:
            await s3.put_object(**described, Body=bytes(buffer))
            return total
        if buffer:
            await flush(bytes(buffer))
        await s3.complete_multipart_upload(**headers, UploadId=upload_id, MultipartUpload={"Parts": parts})
        return total
    except BaseException:
        if upload_id is not None:
            try:
                await s3.abort_multipart_upload(**headers, UploadId=upload_id)
            except Exception:
                log.warning("Couldn't abort the upload of %s", key, exc_info=True)
        raise


async def put_url(key: str, url: str, *, limit: int, content_type: str | None, filename: str) -> int:
    """Streams a file from a trusted URL into storage, typed by `describe()`. Past `limit` bytes it raises `Oversized` and keeps nothing."""
    if _http is None:
        raise RuntimeError("Storage isn't started")
    stored_type, disposition = describe(content_type, filename)
    async with _http.get(url) as response:
        response.raise_for_status()

        async def chunks() -> AsyncIterator[bytes]:
            received = 0
            async for chunk in response.content.iter_chunked(CHUNK):
                received += len(chunk)
                if received > limit:
                    raise Oversized(f"{url} is bigger than {limit} bytes")
                yield chunk

        return await put(key, chunks(), stored_type, disposition)


async def get(key: str, byte_range: str | None = None) -> Object | None:
    """
    Opens an object for streaming, or None when it doesn't exist.

    Args:
        key (str): The object's key.
        byte_range (str | None): A single, already validated `bytes=` range.

    Raises:
        RangeNotSatisfiable: The range starts past the end of the object.
    """
    s3 = _s3()
    try:
        found = await s3.get_object(Bucket=settings.bucket, Key=key, **({"Range": byte_range} if byte_range else {}))
    except ClientError as e:
        if _code(e) in ("NoSuchKey", "404"):
            return None
        if _code(e) == "InvalidRange":
            head = await s3.head_object(Bucket=settings.bucket, Key=key)
            raise RangeNotSatisfiable(head["ContentLength"]) from None
        raise
    content_range = found.get("ContentRange")
    length = found["ContentLength"]
    body = found["Body"]

    async def chunks() -> AsyncIterator[bytes]:
        async with body:
            async for chunk in body.iter_chunks(CHUNK):
                yield chunk

    return Object(
        chunks=chunks(),
        content_type=found.get("ContentType", "application/octet-stream"),
        disposition=found.get("ContentDisposition", "attachment"),
        length=length,
        total=int(content_range.rsplit("/", 1)[1]) if content_range else length,
        content_range=content_range,
    )


async def sizes(prefix: str) -> dict[str, int]:
    found: dict[str, int] = {}
    async for page in _s3().get_paginator("list_objects_v2").paginate(Bucket=settings.bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            found[item["Key"]] = item["Size"]
    return found


async def delete(keys: list[str]) -> None:
    for start in range(0, len(keys), DELETE_BATCH):
        batch = keys[start : start + DELETE_BATCH]
        result = await _s3().delete_objects(
            Bucket=settings.bucket, Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True}
        )
        if errors := result.get("Errors"):
            raise StorageError(f"Couldn't delete {len(errors)} object(s), first {errors[0].get('Key')}")


async def delete_prefix(prefix: str) -> int:
    keys = list(await sizes(prefix))
    await delete(keys)
    return len(keys)


async def folders(under: str = "") -> list[str]:
    """The folder names directly under a prefix. Objects inside them aren't listed, so this stays cheap."""
    found: list[str] = []
    pages = _s3().get_paginator("list_objects_v2").paginate(Bucket=settings.bucket, Prefix=under, Delimiter="/")
    async for page in pages:
        found += [folder["Prefix"].removeprefix(under).rstrip("/") for folder in page.get("CommonPrefixes", [])]
    return found


async def guilds() -> list[int]:
    return [int(name) for name in await folders() if name.isdigit()]


async def purge_guild(guild_id: int) -> None:
    """Deletes a guild's files from every area. Failures are logged, not raised."""
    try:
        await delete_prefix(prefix(guild_id))
    except ERRORS:
        log.warning("Couldn't delete the files of guild %s", guild_id, exc_info=True)


async def sweep_guilds(known: set[int]) -> None:
    """
    Deletes the files of every guild outside `known`.

    Only safe before anything can write, since a guild that gains files after `known` was read would be deleted.
    """
    try:
        gone = [guild_id for guild_id in await guilds() if guild_id not in known]
        for guild_id in gone:
            await delete_prefix(prefix(guild_id))
    except ERRORS:
        log.warning("Couldn't sweep the files of removed guilds", exc_info=True)
        return
    if gone:
        log.info("Deleted the files of %d removed guild(s)", len(gone))
