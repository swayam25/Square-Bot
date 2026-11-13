import discord
from datetime import datetime
from square.db import cache
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import GuildTable, TicketFileTable, TicketMemberTable, TicketTable, TicketTranscriptTable
from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.functions import Count
from tortoise.transactions import in_transaction


async def set_ticket_setup(
    guild_id: int, *, category_id: int | None, support_role_ids: list[int], max_open: int, confirm_close: bool
) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.ticket_category_id = category_id
    guild.ticket_support_role_ids = support_role_ids
    guild.ticket_max_open = max_open
    guild.ticket_confirm_close = confirm_close
    await guild.save(
        update_fields=["ticket_category_id", "ticket_support_role_ids", "ticket_max_open", "ticket_confirm_close"]
    )
    settings = cache.entry(guild_id)
    settings.ticket_category_id, settings.ticket_support_role_ids = category_id, list(support_role_ids)
    settings.ticket_max_open, settings.ticket_confirm_close = max_open, confirm_close


async def set_ticket_category(guild_id: int, category_id: int | None) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.ticket_category_id = category_id
    await guild.save(update_fields=["ticket_category_id"])
    cache.entry(guild_id).ticket_category_id = category_id


async def set_ticket_panel(guild_id: int, channel_id: int | None, message_id: int | None) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.ticket_panel_channel_id, guild.ticket_panel_message_id = channel_id, message_id
    await guild.save(update_fields=["ticket_panel_channel_id", "ticket_panel_message_id"])
    settings = cache.entry(guild_id)
    settings.ticket_panel_channel_id, settings.ticket_panel_message_id = channel_id, message_id


async def reset_ticket_settings(guild_id: int) -> None:
    await set_ticket_setup(guild_id, category_id=None, support_role_ids=[], max_open=1, confirm_close=True)
    await set_ticket_panel(guild_id, None, None)


async def create_ticket(guild_id: int, channel_id: int, opener_id: int, reason: str, number: int) -> TicketTable:
    guild = await fetch_guild_settings(guild_id)
    return await TicketTable.create(
        guild=guild, number=number, channel_id=channel_id, opener_id=opener_id, reason=reason
    )


async def reserve_ticket_number(guild_id: int) -> int:
    """
    Hands out the guild's next ticket number. The row lock means two tickets opened at once can't share a number.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    await fetch_guild_settings(guild_id)
    async with in_transaction() as conn:
        guild = await GuildTable.filter(guild_id=guild_id).select_for_update().using_db(conn).get()
        number = guild.ticket_next_number
        guild.ticket_next_number = number + 1
        await guild.save(using_db=conn, update_fields=["ticket_next_number"])
    return number


async def fetch_ticket(channel_id: int) -> TicketTable | None:
    return await TicketTable.filter(channel_id=channel_id).first()


async def count_open_tickets(guild_id: int, opener_id: int) -> list[int]:
    rows = await TicketTable.filter(guild__guild_id=guild_id, opener_id=opener_id, status="open").values("channel_id")
    return [row["channel_id"] for row in rows]


async def fetch_ticket_members(ticket: TicketTable) -> list[int]:
    return [row["user_id"] for row in await TicketMemberTable.filter(ticket=ticket).values("user_id")]


async def add_ticket_member(ticket: TicketTable, user_id: int, added_by: int) -> None:
    await TicketMemberTable.get_or_create(ticket=ticket, user_id=user_id, defaults={"added_by": added_by})


async def remove_ticket_member(ticket: TicketTable, user_id: int) -> None:
    await TicketMemberTable.filter(ticket=ticket, user_id=user_id).delete()


async def save_ticket(ticket: TicketTable, **changes) -> None:
    if changes.get("status") == "closed":
        changes.setdefault("closed_at", discord.utils.utcnow())
    for name, value in changes.items():
        setattr(ticket, name, value)
    await ticket.save(update_fields=list(changes))


async def fetch_ticket_by_number(guild_id: int, number: int) -> TicketTable | None:
    return await TicketTable.filter(guild__guild_id=guild_id, number=number).first()


async def count_by_status(guild_id: int) -> dict[str, int]:
    rows = (
        await TicketTable.filter(guild__guild_id=guild_id)
        .annotate(n=Count("id"))
        .group_by("status")
        .values("status", "n")
    )
    return {row["status"]: row["n"] for row in rows}


def _tickets(guild_id: int, statuses: list[str], search: Q | None):
    query = TicketTable.filter(guild__guild_id=guild_id, status__in=statuses)
    return query.filter(search) if search is not None else query


async def count_tickets(guild_id: int, *, statuses: list[str], search: Q | None) -> int:
    return await _tickets(guild_id, statuses, search).count()


async def list_tickets(
    guild_id: int, *, statuses: list[str], search: Q | None, newest_first: bool, offset: int, limit: int
) -> list[TicketTable]:
    query = _tickets(guild_id, statuses, search).order_by("-number" if newest_first else "number")
    return list(await query.offset(offset).limit(limit))


async def save_transcript(ticket: TicketTable, data: dict, messages: int, participants: list[int]) -> None:
    async with in_transaction() as conn:
        await TicketTranscriptTable.update_or_create(defaults={"data": data}, using_db=conn, ticket=ticket)
        ticket.message_count, ticket.participant_ids = messages, participants
        await ticket.save(using_db=conn, update_fields=["message_count", "participant_ids"])


async def fetch_transcript(ticket: TicketTable) -> TicketTranscriptTable | None:
    return await TicketTranscriptTable.filter(ticket=ticket).first()


async def stored_file_sizes(ticket: TicketTable) -> dict[int, int]:
    rows = await TicketFileTable.filter(ticket=ticket).values("attachment_id", "size")
    return {row["attachment_id"]: row["size"] for row in rows}


async def add_file(ticket: TicketTable, attachment_id: int, content_type: str, data: bytes) -> None:
    try:
        await TicketFileTable.create(
            ticket=ticket, attachment_id=attachment_id, content_type=content_type, size=len(data), data=data
        )
    except IntegrityError:
        pass  # two saves raced, and the other one stored it


async def delete_files(ticket: TicketTable, attachment_ids: set[int]) -> None:
    await TicketFileTable.filter(ticket=ticket, attachment_id__in=list(attachment_ids)).delete()


async def fetch_file(ticket: TicketTable, attachment_id: int) -> tuple[str, bytes] | None:
    row = await TicketFileTable.filter(ticket=ticket, attachment_id=attachment_id).first()
    return (row.content_type, bytes(row.data)) if row else None


async def purge_ticket(ticket: TicketTable) -> None:
    await ticket.delete()


async def purge_deleted_tickets(guild_id: int) -> int:
    guild = await fetch_guild_settings(guild_id)
    return await TicketTable.filter(guild=guild, status="deleted").delete()


async def ticket_times_since(guild_id: int, since: datetime) -> tuple[list[datetime], list[datetime]]:
    tickets = TicketTable.filter(guild__guild_id=guild_id)
    opened = await tickets.filter(created_at__gte=since).values_list("created_at", flat=True)
    closed = await tickets.filter(closed_at__gte=since).values_list("closed_at", flat=True)
    return list(opened), list(closed)
