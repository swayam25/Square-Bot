"""
Ticket messages.

Buttons carry fixed `ticket:*` IDs that the cog's interaction listener routes, so they keep working after restarts
without registering persistent views.
"""

import discord
from babel.dates import format_timedelta
from discord import ui
from square.core.view import DesignerView
from square.db import cache
from square.db.schema import TicketTable
from square.utils import config
from square.utils.emoji import Icon, emoji


def label(ticket: TicketTable) -> str:
    return f"#{ticket.number:04d}"


def channel_name(number: int) -> str:
    return f"ticket-{number:04d}"


_LOCK = "🔒-"
_PARTICIPANTS_SHOWN = 40  # Mentions past this could push the log card over the text limit


def unlocked_name(name: str) -> str:
    return name.removeprefix(_LOCK)


def locked_name(name: str) -> str:
    """The channel's current name behind a lock, so a ticket staff renamed keeps its name when closed."""
    return (_LOCK + unlocked_name(name))[:100]


def support_roles(guild: discord.Guild) -> list[discord.Role]:
    ids = cache.get(guild.id).ticket_support_role_ids
    return [role for role_id in ids if (role := guild.get_role(role_id))]


def _button(custom_id: str, text: str, icon: Icon, style: discord.ButtonStyle = discord.ButtonStyle.grey) -> ui.Button:
    return ui.Button(custom_id=f"ticket:{custom_id}", label=text, emoji=icon, style=style)


def _who(user_id: int | None, fallback: str = "Nobody yet") -> str:
    return f"<@{user_id}>" if user_id else fallback


def controls(ticket: TicketTable, guild: discord.Guild) -> DesignerView:
    """The card pinned at the top of a ticket channel, with the actions for its current state."""
    if ticket.status == "open":
        staff = ", ".join(role.mention for role in support_roles(guild)) or "Staff"
        return DesignerView(
            ui.Container(
                ui.TextDisplay(f"## Ticket {label(ticket)}"),
                ui.TextDisplay(f"Hey <@{ticket.opener_id}>, {staff} will be with you soon."),
                ui.TextDisplay(
                    f"{emoji.ticket} **Reason**: {ticket.reason}\n{emoji.claim} **Claimed By**: {_who(ticket.claimed_by)}"
                ),
            ),
            ui.ActionRow(
                _button(
                    "claim",
                    "Unclaim" if ticket.claimed_by else "Claim",
                    emoji.claim_white,
                    discord.ButtonStyle.green if ticket.claimed_by else discord.ButtonStyle.grey,
                ),
                _button("add", "Add user", emoji.user_add_white),
                _button("remove", "Remove user", emoji.user_remove_white),
                _button("close", "Close", emoji.lock_white, discord.ButtonStyle.red),
            ),
            timeout=None,
            store=False,
        )
    return DesignerView(
        ui.Container(
            ui.TextDisplay(f"## Ticket {label(ticket)} Closed"),
            ui.TextDisplay(f"{emoji.lock_red} **Closed By**: {_who(ticket.closed_by, 'Unknown')}"),
            color=config.color.red,
        ),
        ui.ActionRow(
            _button("reopen", "Reopen", emoji.unlock_white),
            _button("transcript", "Transcript", emoji.transcript_white),
            _button("delete", "Delete", emoji.bin_white, discord.ButtonStyle.red),
        ),
        timeout=None,
        store=False,
    )


def log_card(
    ticket: TicketTable,
    *,
    transcript: str | None = None,
    messages: int | None = None,
    participants: list[int] | None = None,
) -> DesignerView:
    """
    The one Ticket Log message per ticket.

    It's edited as the ticket is claimed and closed, so the log reads one card per ticket instead of a stream of events.

    Args:
        ticket (:class:`TicketTable`): The ticket.
        transcript (str | None): The attached transcript's filename, shown as a file inside the card.
        messages (int | None): How many messages the ticket had, once it's closed.
        participants (list[int] | None): Members who wrote in it, once it's closed.
    """
    if ticket.status == "open":
        lines = [
            f"{emoji.user} **Opened By**: <@{ticket.opener_id}>",
            f"{emoji.ticket} **Reason**: {ticket.reason}",
            f"{emoji.claim} **Claimed By**: {_who(ticket.claimed_by)}",
            f"{emoji.channel} **Channel**: <#{ticket.channel_id}>",
            f"{emoji.date} **Opened**: {discord.utils.format_dt(ticket.created_at, 'R')}",
        ]
        return DesignerView(
            ui.Container(ui.TextDisplay(f"## Ticket {label(ticket)}"), ui.TextDisplay("\n".join(lines)))
        )
    lines = [
        f"{emoji.user_red} **Opened By**: <@{ticket.opener_id}>",
        f"{emoji.ticket_red} **Reason**: {ticket.reason}",
        f"{emoji.support_red} **Claimed By**: {_who(ticket.claimed_by)}",
        f"{emoji.lock_red} **Closed By**: {_who(ticket.closed_by, 'Unknown')}",
    ]
    if ticket.closed_at:
        open_for = format_timedelta(ticket.closed_at - ticket.created_at, locale="en")
        lines.append(f"{emoji.duration_red} **Open For**: {open_for}")
    if messages is not None:
        lines.append(f"{emoji.messages_red} **Messages**: `{messages}`")
    if participants:
        shown = ", ".join(f"<@{user_id}>" for user_id in participants[:_PARTICIPANTS_SHOWN])
        more = len(participants) - _PARTICIPANTS_SHOWN
        lines.append(f"{emoji.members_red} **Participants**: {shown}{f' and `{more}` more' if more > 0 else ''}")
    state = "Deleted" if ticket.status == "deleted" else "Closed"
    items: list[ui.ViewItem] = [ui.TextDisplay(f"## Ticket {label(ticket)} {state}"), ui.TextDisplay("\n".join(lines))]
    if transcript:
        items.append(ui.File(f"attachment://{transcript}"))
    return DesignerView(ui.Container(*items, color=config.color.red))


def panel() -> DesignerView:
    """The message members press to open a ticket."""
    return DesignerView(
        ui.Container(
            ui.TextDisplay("## Need Help?"),
            ui.TextDisplay("Press the button below to open a ticket. Staff will reply in a private channel."),
        ),
        ui.ActionRow(_button("open", "Open a ticket", emoji.ticket_white, discord.ButtonStyle.blurple)),
        timeout=None,
        store=False,
    )


def confirm(action: str, text: str) -> DesignerView:
    """An ephemeral second click before closing or deleting a ticket."""
    return DesignerView(
        ui.Container(ui.TextDisplay(text), color=config.color.red),
        ui.ActionRow(_button(f"confirm-{action}", f"Yes, {action}", emoji.bin_white, discord.ButtonStyle.red)),
        timeout=None,
        store=False,
    )


def transcript_reply(filename: str) -> DesignerView:
    """A reply carrying a transcript. Components messages only show attachments they reference."""
    return DesignerView(
        ui.Container(
            ui.TextDisplay(f"{emoji.success} Here's the transcript."),
            ui.File(f"attachment://{filename}"),
            color=config.color.green,
        )
    )
