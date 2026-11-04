"""What tickets do. Each action returns a result or an error message, and the caller decides how to reply."""

import asyncio
import discord
import io
import logging
from babel.dates import format_timedelta
from discord import ui
from square.cogs.tickets import cards
from square.core import Client
from square.core.view import DesignerView
from square.db import cache
from square.db.funcs import tickets as db
from square.db.schema import TicketTable
from square.transcript import render_transcript
from square.utils import config, server_log
from square.utils.emoji import emoji

log = logging.getLogger(__name__)

TRANSCRIPT_LIMIT = 5000
_MEMBER_PERMISSIONS = {
    "view_channel": True,
    "send_messages": True,
    "read_message_history": True,
    "attach_files": True,
    "embed_links": True,
    "add_reactions": True,
    "external_emojis": True,
}
MEMBER = discord.PermissionOverwrite(**_MEMBER_PERMISSIONS)
STAFF = discord.PermissionOverwrite(**_MEMBER_PERMISSIONS, manage_messages=True)
BOT = discord.PermissionOverwrite(**_MEMBER_PERMISSIONS, manage_messages=True, manage_channels=True)


def is_support(member: discord.Member) -> bool:
    """Support roles and anyone with Manage Channels can see and manage every ticket."""
    if member.guild_permissions.manage_channels:
        return True
    ids = set(cache.get(member.guild.id).ticket_support_role_ids)
    return any(role.id in ids for role in member.roles)


async def _category(guild: discord.Guild) -> discord.CategoryChannel | None:
    """The configured ticket category, created (and remembered) on first use."""
    category_id = cache.get(guild.id).ticket_category_id
    if category_id and isinstance(category := guild.get_channel(category_id), discord.CategoryChannel):
        return category
    if not guild.me.guild_permissions.manage_channels:
        return None
    category = await guild.create_category(
        "Tickets",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
        },
        reason="Category for tickets",
    )
    await db.set_ticket_category(guild.id, category.id)
    return category


async def open_ticket(
    client: Client, guild: discord.Guild, opener: discord.Member, reason: str
) -> discord.abc.GuildChannel | str:
    """
    Opens a numbered ticket channel only the opener and staff can see.

    Returns:
        The new channel, or an error message.
    """
    settings = cache.get(guild.id)
    if len(open_ids := await db.count_open_tickets(guild.id, opener.id)) >= settings.ticket_max_open:
        return "You already have an open ticket: " + ", ".join(f"<#{channel_id}>" for channel_id in open_ids)
    if (category := await _category(guild)) is None:
        return "I need the `Manage Channels` permission to open tickets."
    number = await db.reserve_ticket_number(guild.id)
    overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: BOT,
        opener: MEMBER,
        **dict.fromkeys(cards.support_roles(guild), STAFF),
    }
    try:
        channel = await category.create_text_channel(
            cards.channel_name(number), overwrites=overwrites, topic=reason[:1024], reason=f"Ticket opened by {opener}"
        )
    except discord.HTTPException as exc:
        return f"I couldn't create the ticket channel: {exc.text or exc}"
    ticket = await db.create_ticket(guild.id, channel.id, opener.id, reason, number)
    message = await channel.send(
        view=cards.controls(ticket, guild), allowed_mentions=discord.AllowedMentions(users=True, roles=True)
    )
    try:
        await message.pin(reason=f"Ticket {cards.label(ticket)} opened")
    except discord.HTTPException:
        # Needs `pin_messages`, which `manage_messages` stopped covering. A ticket still works without the pin.
        log.warning("Couldn't pin the card of ticket %s in guild %s", ticket.number, guild.id)
    log_id = await server_log.post(client, guild, server_log.LogType.TICKETS, cards.log_card(ticket))
    await db.save_ticket(ticket, control_message_id=message.id, log_message_id=log_id)
    return channel


async def refresh(client: Client, guild: discord.Guild, ticket: TicketTable) -> None:
    """Redraws the ticket's control card and its log card after a change."""
    channel = guild.get_channel(ticket.channel_id)
    if isinstance(channel, discord.TextChannel) and ticket.control_message_id:
        try:
            await channel.get_partial_message(ticket.control_message_id).edit(view=cards.controls(ticket, guild))
        except discord.HTTPException:
            log.warning("Couldn't update the controls of ticket %s in guild %s", ticket.number, guild.id)
    if ticket.log_message_id and ticket.status == "open":
        await server_log.edit(client, guild, server_log.LogType.TICKETS, ticket.log_message_id, cards.log_card(ticket))


async def claim(client: Client, guild: discord.Guild, ticket: TicketTable, member: discord.Member) -> str:
    """Claims the ticket for a staff member, or releases it when they already hold it."""
    releasing = ticket.claimed_by == member.id
    await db.save_ticket(ticket, claimed_by=None if releasing else member.id)
    await refresh(client, guild, ticket)
    return f"{'Unclaimed' if releasing else 'Claimed'} ticket {cards.label(ticket)}."


async def add_members(
    ticket: TicketTable, channel: discord.TextChannel, members: list[discord.Member], by: discord.Member
) -> str:
    for member in members:
        await channel.set_permissions(member, overwrite=MEMBER, reason=f"Added to the ticket by {by}")
        await db.add_ticket_member(ticket, member.id, by.id)
    return f"Added {', '.join(member.mention for member in members)} to this ticket."


async def remove_members(
    ticket: TicketTable, channel: discord.TextChannel, members: list[discord.Member], by: discord.Member
) -> str:
    removable = [member for member in members if member.id != ticket.opener_id]
    for member in removable:
        await channel.set_permissions(member, overwrite=None, reason=f"Removed from the ticket by {by}")
        await db.remove_ticket_member(ticket, member.id)
    if not removable:
        return "The opener can't be removed from their own ticket."
    return f"Removed {', '.join(member.mention for member in removable)} from this ticket."


async def _transcript(
    guild: discord.Guild, channel: discord.TextChannel, ticket: TicketTable | None
) -> tuple[bytes, int, list[int]]:
    """The channel as an HTML transcript, with its message count and the members who wrote in it."""
    messages = [message async for message in channel.history(limit=TRANSCRIPT_LIMIT)]
    summary: list[tuple[str, str]] = []
    if ticket is not None:

        def name(user_id: int | None) -> str:
            member = guild.get_member(user_id) if user_id else None
            return member.display_name if member else ("Nobody" if user_id is None else str(user_id))

        summary = [
            ("Opened By", name(ticket.opener_id)),
            ("Reason", ticket.reason),
            ("Claimed By", name(ticket.claimed_by)),
        ]
        if ticket.closed_by:
            summary.append(("Closed By", name(ticket.closed_by)))
        if ticket.closed_at:
            summary.append(("Open For", format_timedelta(ticket.closed_at - ticket.created_at, locale="en")))
    page = await render_transcript(
        messages,
        guild=guild,
        channel_name=channel.name,
        title=f"Ticket {cards.label(ticket)}" if ticket else channel.name,
        summary=summary,
    )
    participants = sorted({message.author.id for message in messages if not message.author.bot})
    return page.encode(), len(messages), participants


async def transcript(guild: discord.Guild, channel: discord.TextChannel, ticket: TicketTable | None) -> discord.File:
    """A transcript to hand to someone who asked for it."""
    page, _, _ = await _transcript(guild, channel, ticket)
    return discord.File(io.BytesIO(page), filename=f"{channel.name}.html")


async def close(
    client: Client, guild: discord.Guild, ticket: TicketTable, channel: discord.TextChannel, by: discord.Member
) -> None:
    """Locks the opener and added members out, saves the transcript into the log card and swaps the controls."""
    await db.save_ticket(ticket, status="closed", closed_by=by.id)
    for user_id in [ticket.opener_id, *await db.fetch_ticket_members(ticket)]:
        if member := guild.get_member(user_id):
            await channel.set_permissions(member, overwrite=discord.PermissionOverwrite(view_channel=False))
    page, count, participants = await _transcript(guild, channel, ticket)
    filename = f"{channel.name}.html"
    card = cards.log_card(ticket, transcript=filename, messages=count, participants=participants)
    edited = ticket.log_message_id is not None and await server_log.edit(
        client,
        guild,
        server_log.LogType.TICKETS,
        ticket.log_message_id,
        card,
        file=discord.File(io.BytesIO(page), filename),
    )
    if not edited:  # The open card is gone, e.g. the log channel was changed meanwhile
        log_id = await server_log.post(
            client, guild, server_log.LogType.TICKETS, card, file=discord.File(io.BytesIO(page), filename)
        )
        await db.save_ticket(ticket, log_message_id=log_id)
    await refresh(client, guild, ticket)


async def reopen(client: Client, guild: discord.Guild, ticket: TicketTable, channel: discord.TextChannel) -> None:
    for user_id in [ticket.opener_id, *await db.fetch_ticket_members(ticket)]:
        if member := guild.get_member(user_id):
            await channel.set_permissions(member, overwrite=MEMBER)
    await db.save_ticket(ticket, status="open", closed_by=None, closed_at=None)
    await refresh(client, guild, ticket)


async def delete(
    client: Client, guild: discord.Guild, ticket: TicketTable, channel: discord.TextChannel, by: discord.Member
) -> None:
    """Deletes the channel. The ticket row and its log card stay, so the record survives."""
    await db.save_ticket(ticket, status="deleted")
    if ticket.log_message_id:
        # No new file: the closed card keeps the transcript it already has
        await server_log.edit(client, guild, server_log.LogType.TICKETS, ticket.log_message_id, cards.log_card(ticket))
    await asyncio.sleep(5)
    await channel.delete(reason=f"Ticket deleted by {by}")


async def close_legacy(client: Client, guild: discord.Guild, channel: discord.TextChannel, by: discord.Member) -> None:
    """Closes a ticket from before v2 (`ticket-<user id>`, no database row): transcript to the log, then delete."""
    page, count, _ = await _transcript(guild, channel, None)
    opener = channel.name.removeprefix("ticket-")
    filename = f"{channel.name}.html"
    view = DesignerView(
        ui.Container(
            ui.TextDisplay("## Ticket Closed"),
            ui.TextDisplay(
                f"{emoji.user_red} **Opened By**: <@{opener}>\n{emoji.lock_red} **Closed By**: {by.mention}\n"
                f"{emoji.messages_red} **Messages**: `{count}`"
            ),
            ui.File(f"attachment://{filename}"),
            color=config.color.red,
        )
    )
    await server_log.post(
        client, guild, server_log.LogType.TICKETS, view, file=discord.File(io.BytesIO(page), filename)
    )
    await asyncio.sleep(5)
    await channel.delete(reason=f"Ticket closed by {by}")
