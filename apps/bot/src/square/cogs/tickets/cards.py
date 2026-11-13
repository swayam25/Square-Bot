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
_PARTICIPANTS_SHOWN = 40


def unlocked_name(name: str) -> str:
    return name.removeprefix(_LOCK)


def locked_name(name: str) -> str:
    return (_LOCK + unlocked_name(name))[:100]


def support_roles(guild: discord.Guild) -> list[discord.Role]:
    ids = cache.get(guild.id).ticket_support_role_ids
    return [role for role_id in ids if (role := guild.get_role(role_id))]


def _button(custom_id: str, text: str, icon: Icon, style: discord.ButtonStyle = discord.ButtonStyle.grey) -> ui.Button:
    return ui.Button(custom_id=f"ticket:{custom_id}", label=text, emoji=icon, style=style)


def _who(user_id: int | None, fallback: str = "Nobody yet") -> str:
    return f"<@{user_id}>" if user_id else fallback


def controls(ticket: TicketTable, guild: discord.Guild) -> DesignerView:
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


def transcript_url(guild_id: int, ticket: TicketTable) -> str:
    return f"{config.dashboard_url}/guild/{guild_id}/tickets/{ticket.number}"


def _transcript_button(guild_id: int, ticket: TicketTable) -> ui.ActionRow:
    return ui.ActionRow(
        ui.Button(
            label="Show Transcript",
            emoji=emoji.transcript_white,
            style=discord.ButtonStyle.link,
            url=transcript_url(guild_id, ticket),
        )
    )


def log_card(ticket: TicketTable, guild_id: int) -> DesignerView:
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
    if ticket.message_count is not None:
        lines.append(f"{emoji.messages_red} **Messages**: `{ticket.message_count}`")
    if participants := ticket.participant_ids:
        shown = ", ".join(f"<@{user_id}>" for user_id in participants[:_PARTICIPANTS_SHOWN])
        more = len(participants) - _PARTICIPANTS_SHOWN
        lines.append(f"{emoji.members_red} **Participants**: {shown}{f' and `{more}` more' if more > 0 else ''}")
    state = "Deleted" if ticket.status == "deleted" else "Closed"
    items: list[ui.ViewItem] = [
        ui.Container(
            ui.TextDisplay(f"## Ticket {label(ticket)} {state}"),
            ui.TextDisplay("\n".join(lines)),
            color=config.color.red,
        )
    ]
    if ticket.message_count is not None:
        items.append(_transcript_button(guild_id, ticket))
    return DesignerView(*items)


def panel() -> DesignerView:
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
    return DesignerView(
        ui.Container(ui.TextDisplay(text), color=config.color.red),
        ui.ActionRow(_button(f"confirm-{action}", f"Yes, {action}", emoji.bin_white, discord.ButtonStyle.red)),
        timeout=None,
        store=False,
    )


def transcript_reply(ticket: TicketTable, guild_id: int) -> DesignerView:
    return DesignerView(
        ui.Container(
            ui.TextDisplay(f"{emoji.success} Saved the transcript of ticket {label(ticket)}."), color=config.color.green
        ),
        _transcript_button(guild_id, ticket),
    )
