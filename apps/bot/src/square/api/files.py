"""Streams stored files to API callers, with range support."""

import logging
import re
from litestar.exceptions import HTTPException, ServiceUnavailableException
from litestar.openapi import ResponseSpec
from litestar.params import Parameter
from litestar.response import Stream
from square.api.resolve import SettingError
from square.utils import storage
from typing import Annotated

log = logging.getLogger(__name__)

SINGLE_RANGE = re.compile(r"bytes=(\d{1,15}-\d{0,15}|-\d{1,15})")
RESPONSES = {
    206: ResponseSpec(None, description="The requested part of the file"),
    416: ResponseSpec(None, description="The range starts past the end of the file"),
}
Range = Annotated[str | None, Parameter(header="range", required=False)]


async def serve(key: str, byte_range: str | None, missing: str) -> Stream:
    """
    Streams a stored object, or refuses with `missing` when it isn't there.

    Anything but one plain range is ignored, which HTTP allows, so the whole file is sent instead.
    """
    wanted = byte_range if byte_range and SINGLE_RANGE.fullmatch(byte_range) else None
    try:
        found = await storage.get(key, wanted)
    except storage.RangeNotSatisfiable as e:
        raise HTTPException(status_code=416, headers={"Content-Range": f"bytes */{e.total}"}) from None
    except storage.ERRORS:
        log.warning("Couldn't read %s from storage", key, exc_info=True)
        raise ServiceUnavailableException(
            "The saved files can't be reached right now. Try again in a moment."
        ) from None
    if found is None:
        raise SettingError(missing)
    headers = {
        # Litestar prefers the handler's media type over a Stream's, so the type is set as a header
        "Content-Type": found.content_type,
        "Content-Length": str(found.length),
        "Content-Disposition": found.disposition,
        "Accept-Ranges": "bytes",
    }
    if found.content_range:
        headers["Content-Range"] = found.content_range
    return Stream(found.chunks, status_code=206 if found.content_range else 200, headers=headers)
