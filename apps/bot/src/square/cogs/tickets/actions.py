"""What tickets do. Each action returns a result or an error message, and the caller decides how to reply."""

import asyncio
import discord
import logging
from discord import ui
from square.cogs.tickets import cards, snapshot
from square.core import Client
from square.core.view import DesignerView
from square.db import cache
from square.db.funcs import tickets as db
from square.db.schema import TicketTable
from square.utils import config, server_log
from square.utils.emoji import emoji

log = logging.getLogger(__name__)

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
_renames: dict[int, asyncio.Task] = {}


def is_support(member: discord.Member) -> bool:
    if member.guild_permissions.manage_channels:
        return True
    ids = set(cache.get(member.guild.id).ticket_support_role_ids)
    return any(role.id in ids for role in member.roles)


def _rename(channel: discord.TextChannel, closed: bool, reason: str) -> None:
    if pending := _renames.pop(channel.id, None):
        pending.cancel()

    async def run() -> None:
        # The cached channel, since `interaction.channel` is a copy that doesn't see later renames
        current = channel.guild.get_channel(channel.id) or channel
        name = cards.locked_name(current.name) if closed else cards.unlocked_name(current.name)
        if name == current.name:
            return
        try:
            await current.edit(name=name, reason=reason)
        except discord.HTTPException:
            log.warning("Couldn't rename ticket channel %s in guild %s", channel.id, channel.guild.id)

    task = asyncio.create_task(run())
    _renames[channel.id] = task
    task.add_done_callback(lambda done: _renames.pop(channel.id, None) if _renames.get(channel.id) is done else None)


async def _category(guild: discord.Guild) -> discord.CategoryChannel | None:
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
    log_id = await server_log.post(client, guild, server_log.LogType.TICKETS, cards.log_card(ticket, guild.id))
    await db.save_ticket(ticket, control_message_id=message.id, log_message_id=log_id)
    return channel


async def refresh(client: Client, guild: discord.Guild, ticket: TicketTable) -> None:
    channel = guild.get_channel(ticket.channel_id)
    if isinstance(channel, discord.TextChannel) and ticket.control_message_id:
        try:
            await channel.get_partial_message(ticket.control_message_id).edit(view=cards.controls(ticket, guild))
        except discord.HTTPException:
            log.warning("Couldn't update the controls of ticket %s in guild %s", ticket.number, guild.id)
    if ticket.log_message_id and ticket.status == "open":
        await server_log.edit(
            client, guild, server_log.LogType.TICKETS, ticket.log_message_id, cards.log_card(ticket, guild.id)
        )


async def claim(client: Client, guild: discord.Guild, ticket: TicketTable, member: discord.Member) -> str:
    await db.save_ticket(ticket, claimed_by=member.id)
    await refresh(client, guild, ticket)
    return f"Claimed ticket {cards.label(ticket)}."


async def unclaim(client: Client, guild: discord.Guild, ticket: TicketTable) -> str:
    await db.save_ticket(ticket, claimed_by=None)
    await refresh(client, guild, ticket)
    return f"Unclaimed ticket {cards.label(ticket)}."


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


async def save_transcript(
    guild: discord.Guild, channel: discord.TextChannel, ticket: TicketTable, *, unless_saved_after: int | None = None
) -> bool:
    """Saves what's in the channel right now. False when Discord wouldn't hand the messages over."""
    try:
        await snapshot.save(guild, channel, ticket, unless_saved_after=unless_saved_after)
    except discord.HTTPException:
        log.warning("Couldn't save the transcript of ticket %s in guild %s", ticket.number, guild.id)
        return False
    return True


async def _log(client: Client, guild: discord.Guild, ticket: TicketTable) -> None:
    card = cards.log_card(ticket, guild.id)
    if ticket.log_message_id and await server_log.edit(
        client, guild, server_log.LogType.TICKETS, ticket.log_message_id, card
    ):
        return
    log_id = await server_log.post(client, guild, server_log.LogType.TICKETS, card)
    await db.save_ticket(ticket, log_message_id=log_id)


async def close(
    client: Client, guild: discord.Guild, ticket: TicketTable, channel: discord.TextChannel, by: discord.Member
) -> None:
    await db.save_ticket(ticket, status="closed", closed_by=by.id)
    for user_id in [ticket.opener_id, *await db.fetch_ticket_members(ticket)]:
        if member := guild.get_member(user_id):
            await channel.set_permissions(member, overwrite=discord.PermissionOverwrite(view_channel=False))
    await save_transcript(guild, channel, ticket)
    await _log(client, guild, ticket)
    await refresh(client, guild, ticket)
    _rename(channel, True, f"Ticket closed by {by}")


async def reopen(client: Client, guild: discord.Guild, ticket: TicketTable, channel: discord.TextChannel) -> None:
    for user_id in [ticket.opener_id, *await db.fetch_ticket_members(ticket)]:
        if member := guild.get_member(user_id):
            await channel.set_permissions(member, overwrite=MEMBER)
    await db.save_ticket(ticket, status="open", closed_by=None, closed_at=None)
    await refresh(client, guild, ticket)
    _rename(channel, False, "Ticket reopened")


async def delete(
    client: Client,
    guild: discord.Guild,
    ticket: TicketTable,
    channel: discord.TextChannel,
    by: discord.Member,
) -> None:
    """Deletes the channel. The ticket and its transcript stay until someone removes them on the dashboard."""
    # Staff can keep talking in a closed ticket, so this is the last chance to save those messages
    await save_transcript(guild, channel, ticket)
    await db.save_ticket(ticket, status="deleted")
    if ticket.log_message_id:
        await server_log.edit(
            client, guild, server_log.LogType.TICKETS, ticket.log_message_id, cards.log_card(ticket, guild.id)
        )
    await channel.delete(reason=f"Ticket deleted by {by}")


async def close_legacy(client: Client, guild: discord.Guild, channel: discord.TextChannel, by: discord.Member) -> None:
    opener = channel.name.removeprefix("ticket-")
    view = DesignerView(
        ui.Container(
            ui.TextDisplay("## Ticket Closed"),
            ui.TextDisplay(
                f"{emoji.user_red} **Opened By**: <@{opener}>\n{emoji.lock_red} **Closed By**: {by.mention}"
            ),
            color=config.color.red,
        )
    )
    await server_log.post(client, guild, server_log.LogType.TICKETS, view)
    await channel.delete(reason=f"Ticket closed by {by}")
