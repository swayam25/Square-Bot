"""Storage holds a scheduled giveaway's image only until it posts. After that it lives on the message."""

import logging
from collections.abc import AsyncIterator
from square.db.schema import GiveawayTable
from square.utils import storage

log = logging.getLogger(__name__)

AREA = "giveaways"


def key(guild_id: int, giveaway_id: int, name: str) -> str:
    return storage.key(guild_id, AREA, giveaway_id, name)


def _prefix(guild_id: int, giveaway_id: int) -> str:
    return storage.prefix(guild_id, AREA, giveaway_id)


async def stash(guild_id: int, giveaway_id: int, name: str, raw: bytes, content_type: str) -> None:
    """The old image is deleted only once the new one is stored."""

    async def chunks() -> AsyncIterator[bytes]:
        yield raw

    new = key(guild_id, giveaway_id, name)
    await storage.put(new, chunks(), *storage.describe(content_type, name))
    if old := [found for found in await storage.sizes(_prefix(guild_id, giveaway_id)) if found != new]:
        await storage.delete(old)


async def load(guild_id: int, giveaway_id: int, name: str) -> bytes | None:
    found = await storage.get(key(guild_id, giveaway_id, name))
    if found is None:
        return None
    return b"".join([chunk async for chunk in found.chunks])


async def drop(guild_id: int, giveaway_id: int) -> None:
    try:
        await storage.delete_prefix(_prefix(guild_id, giveaway_id))
    except storage.ERRORS:
        log.warning("Couldn't delete the image of giveaway %s, the next sweep will", giveaway_id, exc_info=True)


async def sweep() -> None:
    try:
        # Listed before the giveaways are read, so one scheduled in between can't look orphaned
        listed = {
            guild_id: await storage.folders(storage.prefix(guild_id, AREA)) for guild_id in await storage.guilds()
        }
        waiting = set(
            await GiveawayTable.filter(status="scheduled", image_file__isnull=False).values_list(
                "guild__guild_id", "id"
            )
        )
        orphans = [
            storage.prefix(guild_id, AREA, name)
            for guild_id, names in listed.items()
            for name in names
            if not name.isdigit() or (guild_id, int(name)) not in waiting
        ]
        for orphan in orphans:
            await storage.delete_prefix(orphan)
    except storage.ERRORS:
        log.warning("Couldn't sweep orphaned giveaway images", exc_info=True)
