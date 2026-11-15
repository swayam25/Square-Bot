"""A ticket's attachments, kept in storage since Discord's attachment links stop working after about a day."""

import asyncio
import discord
import logging
from collections.abc import Iterable, Sequence
from square.db.schema import TicketTable
from square.utils import storage

log = logging.getLogger(__name__)

AREA = "tickets"
FILE_LIMIT = 100 * 1024 * 1024
TICKET_BUDGET = 500 * 1024 * 1024
PARALLEL = 4


def key(guild_id: int, ticket_id: int, attachment_id: int) -> str:
    return storage.key(guild_id, AREA, ticket_id, attachment_id)


async def copy(guild_id: int, ticket_id: int, messages: Sequence[discord.Message]) -> set[int]:
    """Copies the ticket's attachments that aren't stored yet, drops the ones whose message is gone, and returns what's kept."""
    prefix = storage.prefix(guild_id, AREA, ticket_id)
    try:
        listed = await storage.sizes(prefix)
    except storage.ERRORS:
        log.warning("Couldn't list the stored files of ticket %s", ticket_id, exc_info=True)
        return set()
    have = {int(name): size for found, size in listed.items() if (name := found.removeprefix(prefix)).isdigit()}
    wanted = [attachment for message in messages for attachment in message.attachments]
    wanted_ids = {attachment.id for attachment in wanted}
    if gone := set(have) - wanted_ids:
        try:
            await storage.delete([key(guild_id, ticket_id, attachment_id) for attachment_id in gone])
        except storage.ERRORS:
            log.warning("Couldn't drop removed files of ticket %s", ticket_id, exc_info=True)
    kept = set(have) & wanted_ids
    budget = TICKET_BUDGET - sum(have[attachment_id] for attachment_id in kept)
    picked: list[discord.Attachment] = []
    for attachment in wanted:
        if attachment.id not in kept and attachment.size <= min(FILE_LIMIT, budget):
            picked.append(attachment)
            budget -= attachment.size
    semaphore = asyncio.Semaphore(PARALLEL)

    async def one(attachment: discord.Attachment) -> int | None:
        async with semaphore:
            try:
                # Capped at the size Discord reported, since the budget was counted from it
                await storage.put_url(
                    key(guild_id, ticket_id, attachment.id),
                    attachment.url,
                    limit=attachment.size,
                    content_type=attachment.content_type,
                    filename=attachment.filename,
                )
            except storage.ERRORS:
                log.warning("Couldn't copy attachment %s of ticket %s", attachment.id, ticket_id, exc_info=True)
                return None
        return attachment.id

    copied = await asyncio.gather(*(one(attachment) for attachment in picked))
    return kept | {attachment_id for attachment_id in copied if attachment_id}


async def purge(guild_id: int, ticket_ids: Iterable[int]) -> None:
    """Deletes the files of tickets whose rows are already gone."""
    for ticket_id in ticket_ids:
        try:
            await storage.delete_prefix(storage.prefix(guild_id, AREA, ticket_id))
        except storage.ERRORS:
            log.warning("Couldn't delete the files of ticket %s, the next sweep will", ticket_id, exc_info=True)


async def sweep() -> None:
    """Deletes the folders of tickets that no longer exist, left behind when a purge couldn't reach storage."""
    try:
        # Listed before the tickets are read, so a ticket made in between can't look orphaned
        listed = {
            guild_id: await storage.folders(storage.prefix(guild_id, AREA)) for guild_id in await storage.guilds()
        }
        tickets = set(await TicketTable.all().values_list("guild__guild_id", "id"))
        orphans = [
            storage.prefix(guild_id, AREA, name)
            for guild_id, names in listed.items()
            for name in names
            if not name.isdigit() or (guild_id, int(name)) not in tickets
        ]
        for orphan in orphans:
            await storage.delete_prefix(orphan)
    except storage.ERRORS:
        log.warning("Couldn't sweep orphaned ticket files", exc_info=True)
        return
    if orphans:
        log.info("Deleted the files of %d orphaned ticket(s)", len(orphans))
