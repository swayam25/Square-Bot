import discord
import logging
from itertools import islice
from litestar import Response, Router, delete, get, post
from litestar.di import Provide
from litestar.params import Parameter
from square.api.auth import provide_guild, provide_member, provide_member_guild
from square.api.resolve import SettingError
from square.api.routes.settings import REFUSED, refused
from square.api.schemas import Purged, TicketDetail, TicketEntry, TicketPage, TicketTranscript
from square.api.users import people_of
from square.cogs.tickets import actions, cards, snapshot
from square.core import Client
from square.db.funcs import tickets as tickets_db
from square.db.schema import TicketTable
from tortoise.expressions import Q
from typing import Annotated, Literal

log = logging.getLogger(__name__)

PAGE_SIZE = 25
PEOPLE_SHOWN = 100
# A transcript of a ticket that's still there is read again once the saved one is this old
FRESH_FOR_MS = 60_000
Number = Annotated[int, Parameter(ge=1, le=10_000_000)]
STATUSES = {"open": ["open"], "closed": ["closed"], "deleted": ["deleted"], "all": ["open", "closed", "deleted"]}


def _ms(when) -> int:
    return round(when.timestamp() * 1000)


def _channel(guild: discord.Guild, ticket: TicketTable) -> discord.TextChannel | None:
    channel = guild.get_channel(ticket.channel_id)
    return channel if isinstance(channel, discord.TextChannel) else None


def _search(guild: discord.Guild, text: str) -> Q:
    text = text.strip()
    found = Q(reason__icontains=text)
    if text.lstrip("#").isdigit():
        value = int(text.lstrip("#"))
        found |= Q(number=value) | Q(opener_id=value) | Q(channel_id=value)
    needle = text.casefold()
    matches = (m.id for m in guild.members if needle in m.display_name.casefold() or needle in m.name.casefold())
    if names := list(islice(matches, 500)):
        found |= Q(opener_id__in=names)
    return found


async def _entries(client: Client, guild: discord.Guild, tickets: list[TicketTable]) -> list[TicketEntry]:
    ids = list(dict.fromkeys(i for t in tickets for i in (t.opener_id, t.claimed_by) if i))
    people = dict(zip(ids, await people_of(client, guild, ids), strict=True))
    entries = []
    for ticket in tickets:
        channel = _channel(guild, ticket)
        entries.append(
            TicketEntry(
                number=ticket.number,
                label=cards.label(ticket),
                status=ticket.status,
                channel_id=str(channel.id) if channel else None,
                channel_name=channel.name if channel else None,
                opener=people[ticket.opener_id],
                claimed_by=people[ticket.claimed_by] if ticket.claimed_by else None,
                reason=ticket.reason,
                created_at=_ms(ticket.created_at),
                closed_at=_ms(ticket.closed_at) if ticket.closed_at else None,
                messages=ticket.message_count,
            )
        )
    return entries


async def _detail(client: Client, guild: discord.Guild, ticket: TicketTable) -> TicketDetail:
    (entry,) = await _entries(client, guild, [ticket])
    added = await tickets_db.fetch_ticket_members(ticket)
    everyone = list(dict.fromkeys([ticket.opener_id, *added, *ticket.participant_ids]))[:PEOPLE_SHOWN]
    closed_by = (await people_of(client, guild, [ticket.closed_by]))[0] if ticket.closed_by else None
    return TicketDetail(
        **{f: getattr(entry, f) for f in entry.__struct_fields__},
        closed_by=closed_by,
        people=await people_of(client, guild, everyone),
    )


async def _ticket(guild: discord.Guild, number: int) -> TicketTable:
    if (ticket := await tickets_db.fetch_ticket_by_number(guild.id, number)) is None:
        raise SettingError("That ticket doesn't exist.")
    return ticket


def _live_channel(guild: discord.Guild, ticket: TicketTable) -> discord.TextChannel:
    if (channel := _channel(guild, ticket)) is None:
        raise SettingError("That ticket's channel is gone.")
    return channel


def _audit(member: discord.Member, action: str, ticket: TicketTable) -> None:
    log.info("Dashboard: %s (%s) %s ticket %s in %s", member, member.id, action, ticket.number, member.guild.id)


@get("/", summary="Tickets, newest first, filtered by status and search")
async def list_tickets(
    client: Client,
    guild: discord.Guild,
    status: Literal["open", "closed", "deleted", "all"] = "open",
    q: Annotated[str | None, Parameter(max_length=100)] = None,
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Parameter(ge=1, le=100_000)] = 1,
) -> TicketPage:
    search = _search(guild, q) if q and q.strip() else None
    counts = await tickets_db.count_by_status(guild.id)
    total = await tickets_db.count_tickets(guild.id, statuses=STATUSES[status], search=search)
    pages = max(1, -(-total // PAGE_SIZE))
    page = min(page, pages)
    tickets = await tickets_db.list_tickets(
        guild.id,
        statuses=STATUSES[status],
        search=search,
        newest_first=order == "desc",
        offset=(page - 1) * PAGE_SIZE,
        limit=PAGE_SIZE,
    )
    return TicketPage(
        entries=await _entries(client, guild, tickets),
        page=page,
        pages=pages,
        total=total,
        open=counts.get("open", 0),
        closed=counts.get("closed", 0),
        deleted=counts.get("deleted", 0),
    )


@get("/{number:int}", summary="One ticket with its members", responses=REFUSED)
async def get_ticket(client: Client, guild: discord.Guild, number: Number) -> TicketDetail:
    return await _detail(client, guild, await _ticket(guild, number))


@post("/{number:int}/close", summary="Close a ticket and save its transcript", status_code=200, responses=REFUSED)
async def close_ticket(client: Client, guild: discord.Guild, member: discord.Member, number: Number) -> TicketDetail:
    ticket = await _ticket(guild, number)
    if ticket.status != "open":
        raise SettingError("That ticket is already closed.")
    await actions.close(client, guild, ticket, _live_channel(guild, ticket), member)
    _audit(member, "closed", ticket)
    return await _detail(client, guild, ticket)


@post("/{number:int}/reopen", summary="Reopen a closed ticket", status_code=200, responses=REFUSED)
async def reopen_ticket(client: Client, guild: discord.Guild, member: discord.Member, number: Number) -> TicketDetail:
    ticket = await _ticket(guild, number)
    if ticket.status != "closed":
        raise SettingError("Only a closed ticket can be reopened.")
    await actions.reopen(client, guild, ticket, _live_channel(guild, ticket))
    _audit(member, "reopened", ticket)
    return await _detail(client, guild, ticket)


@delete(
    "/{number:int}", summary="Delete a ticket's channel, keeping its transcript", status_code=200, responses=REFUSED
)
async def delete_ticket(client: Client, guild: discord.Guild, member: discord.Member, number: Number) -> TicketDetail:
    ticket = await _ticket(guild, number)
    if ticket.status == "deleted":
        raise SettingError("That ticket is already deleted.")
    await actions.delete(client, guild, ticket, _live_channel(guild, ticket), member, delay=0)
    _audit(member, "deleted", ticket)
    return await _detail(client, guild, ticket)


@delete(
    "/{number:int}/record",
    summary="Remove a deleted ticket for good, with its transcript",
    status_code=200,
    responses=REFUSED,
)
async def purge_ticket(guild: discord.Guild, member: discord.Member, number: Number) -> Purged:
    ticket = await _ticket(guild, number)
    if _channel(guild, ticket):
        raise SettingError("That ticket still has its channel. Delete the ticket first.")
    await tickets_db.purge_ticket(ticket)
    _audit(member, "permanently removed", ticket)
    return Purged(removed=1)


@delete("/deleted", summary="Remove every deleted ticket for good, with their transcripts", status_code=200)
async def purge_deleted_tickets(guild: discord.Guild, member: discord.Member) -> Purged:
    removed = await tickets_db.purge_deleted_tickets(guild.id)
    log.info("Dashboard: %s (%s) permanently removed %s deleted tickets in %s", member, member.id, removed, guild.id)
    return Purged(removed=removed)


async def _readable(guild: discord.Guild, member: discord.Member, number: int) -> TicketTable:
    """The ticket, for the people who could read it in Discord: staff and whoever opened it."""
    ticket = await tickets_db.fetch_ticket_by_number(guild.id, number)
    allowed = ticket is not None and (
        member.guild_permissions.manage_guild or actions.is_support(member) or member.id == ticket.opener_id
    )
    if ticket is None or not allowed:
        raise SettingError("That ticket doesn't exist, or you aren't allowed to read it.")
    return ticket


# These two answer anyone in the server, and `_readable` decides who gets a ticket
MEMBERS = {"guild": Provide(provide_member_guild, sync_to_thread=False)}


@get(
    "/{number:int}/transcript",
    summary="A ticket and its saved messages, for staff and the ticket's opener",
    dependencies=MEMBERS,
    responses=REFUSED,
)
async def ticket_transcript(
    client: Client, guild: discord.Guild, member: discord.Member, number: Number
) -> TicketTranscript:
    ticket = await _readable(guild, member, number)
    saved = await snapshot.load(ticket)
    channel = _channel(guild, ticket)
    stale_before = round(discord.utils.utcnow().timestamp() * 1000) - FRESH_FOR_MS
    if channel and (saved is None or saved[1] < stale_before):
        if await actions.save_transcript(guild, channel, ticket, unless_saved_after=stale_before):
            saved = await snapshot.load(ticket)
    return TicketTranscript(
        ticket=await _detail(client, guild, ticket),
        live=channel is not None,
        transcript=saved[0] if saved else None,
    )


@get(
    "/{number:int}/files/{attachment_id:str}",
    summary="A picture copied from a ticket",
    dependencies=MEMBERS,
    media_type="application/octet-stream",
    responses=REFUSED,
)
async def ticket_file(
    guild: discord.Guild,
    member: discord.Member,
    number: Number,
    attachment_id: Annotated[str, Parameter(pattern=r"^\d{17,20}$")],
) -> Response[bytes]:
    ticket = await _readable(guild, member, number)
    if (file := await tickets_db.fetch_file(ticket, int(attachment_id))) is None:
        raise SettingError("That picture wasn't kept.")
    content_type, data = file
    return Response(data, media_type=content_type)


router = Router(
    "/guilds/{guild_id:str}/tickets",
    tags=["Tickets"],
    exception_handlers={SettingError: refused},
    dependencies={
        "guild": Provide(provide_guild, sync_to_thread=False),
        "member": Provide(provide_member, sync_to_thread=False),
    },
    route_handlers=[
        list_tickets,
        get_ticket,
        close_ticket,
        reopen_ticket,
        delete_ticket,
        purge_ticket,
        purge_deleted_tickets,
        ticket_transcript,
        ticket_file,
    ],
)
