"""Buttons use fixed `giveaway:*` IDs routed by the cog's listener, so they survive restarts without persistent views."""

import discord
from discord import ui
from square.core.view import DesignerView, error_view
from square.db import cache
from square.db.schema import GiveawayTable
from square.modules import Module
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count

STYLES = {
    "blurple": discord.ButtonStyle.blurple,
    "green": discord.ButtonStyle.green,
    "grey": discord.ButtonStyle.grey,
    "red": discord.ButtonStyle.red,
}
_WINNERS_SHOWN = 40


def role_mention(guild_id: int, role_id: int) -> str:
    return "@everyone" if role_id == guild_id else f"<@&{role_id}>"


def mentions(user_ids: list[int]) -> str:
    shown = ", ".join(f"<@{user_id}>" for user_id in user_ids[:_WINNERS_SHOWN])
    more = len(user_ids) - _WINNERS_SHOWN
    return f"{shown} and `{more}` more" if more > 0 else shown


def days(count: int) -> str:
    return f"`{count} day{'' if count == 1 else 's'}`"


def invites(count: int) -> str:
    return f"`{count}` invite{'' if count == 1 else 's'}"


def needs_invites(giveaway: GiveawayTable, guild_id: int) -> bool:
    """Invite counts stop updating while the Invites module is off, so the requirement only applies while it's on."""
    return giveaway.min_invites > 0 and cache.enabled(guild_id, Module.INVITES)


def _color(giveaway: GiveawayTable) -> int | None:
    return int(giveaway.color[1:], 16) if giveaway.color else None


def enter_button(giveaway: GiveawayTable, *, disabled: bool = False) -> ui.Button:
    count = fmt_count(giveaway.entry_count)
    label = giveaway.button_label.strip()
    icon = discord.PartialEmoji.from_str(giveaway.button_emoji) if giveaway.button_emoji else emoji.giveaway_white
    return ui.Button(
        custom_id="giveaway:enter",
        label=f"{label} · {count}" if label else count,
        emoji=icon,
        style=STYLES.get(giveaway.button_style, discord.ButtonStyle.blurple),
        disabled=disabled,
    )


def _rules(giveaway: GiveawayTable, guild_id: int) -> list[str]:
    lines: list[str] = []
    if required := giveaway.required_role_ids:
        roles = ", ".join(role_mention(guild_id, role_id) for role_id in required)
        label = "Needs" if len(required) == 1 else "Needs All Of" if giveaway.require_all_roles else "Needs One Of"
        lines.append(f"{emoji.role} **{label}**: {roles}")
    if blocked := giveaway.blocked_role_ids:
        lines.append(f"{emoji.perms} **Not For**: {', '.join(role_mention(guild_id, role_id) for role_id in blocked)}")
    if giveaway.min_account_days:
        lines.append(f"{emoji.user} **Account Age**: at least {days(giveaway.min_account_days)}")
    if giveaway.min_member_days:
        lines.append(f"{emoji.members} **In Server For**: at least {days(giveaway.min_member_days)}")
    if needs_invites(giveaway, guild_id):
        lines.append(f"{emoji.invite} **Invites**: at least {invites(giveaway.min_invites)}")
    if bonus := giveaway.bonus_roles:
        extra = ", ".join(f"{role_mention(guild_id, role_id)} `+{entries}`" for role_id, entries in bonus)
        lines.append(f"{emoji.add} **Bonus Entries**: {extra}")
    return lines


def giveaway_card(giveaway: GiveawayTable, guild_id: int) -> DesignerView:
    ended = giveaway.status == "ended"
    items: list[ui.ViewItem] = []
    if giveaway.ping_role_id and not ended:
        items.append(ui.TextDisplay(role_mention(guild_id, giveaway.ping_role_id)))

    container = ui.Container(ui.TextDisplay(f"## {giveaway.prize}"), color=_color(giveaway))
    if giveaway.description.strip():
        container.add_item(ui.TextDisplay(giveaway.description))
    if ended:
        winners = mentions(giveaway.winner_ids) if giveaway.winner_ids else "Nobody could win"
        ended_at = giveaway.ended_at or giveaway.ends_at
        lines = [
            f"{emoji.crown} **{'Winner' if len(giveaway.winner_ids) == 1 else 'Winners'}**: {winners}",
            f"{emoji.user} **Hosted By**: <@{giveaway.host_id}>",
            f"{emoji.duration} **Ended**: {discord.utils.format_dt(ended_at, 'R')}",
        ]
    else:
        lines = [
            f"{emoji.duration} **Ends**: {discord.utils.format_dt(giveaway.ends_at, 'R')}",
            f"{emoji.crown} **Winners**: `{giveaway.winner_count}`",
            f"{emoji.user} **Hosted By**: <@{giveaway.host_id}>",
            *_rules(giveaway, guild_id),
        ]
    container.add_item(ui.TextDisplay("\n".join(lines)))
    if image := (f"attachment://{giveaway.image_file}" if giveaway.image_file else giveaway.image_url):
        container.add_item(ui.MediaGallery(discord.MediaGalleryItem(url=image)))
    items += [container, ui.ActionRow(enter_button(giveaway, disabled=ended))]
    return DesignerView(*items, timeout=None, store=False)


def winners_card(giveaway: GiveawayTable, winner_ids: list[int], *, reroll: bool = False) -> DesignerView:
    if not winner_ids:
        return error_view(f"Nobody could win **{giveaway.prize}**.")
    who = mentions(winner_ids)
    if reroll:
        text = f"{emoji.giveaway_green} Rerolled! Congratulations {who}, you won **{giveaway.prize}**."
    else:
        text = f"{emoji.giveaway_green} Congratulations {who}! You won **{giveaway.prize}**."
    return DesignerView(ui.Container(ui.TextDisplay(text), color=config.color.green))


def leave_card(giveaway: GiveawayTable, refusal: str | None = None) -> DesignerView:
    text = f"{emoji.success} You've already entered **{giveaway.prize}**."
    if refusal:
        text += f"\n-# You can't win right now. {refusal}"
    return DesignerView(
        ui.Container(ui.TextDisplay(text), color=config.color.green),
        ui.ActionRow(
            ui.Button(
                custom_id=f"giveaway:leave:{giveaway.id}",
                label="Leave giveaway",
                emoji=emoji.bin_white,
                style=discord.ButtonStyle.red,
            )
        ),
        timeout=None,
        store=False,
    )


def dashboard_url(guild_id: int, giveaway_id: int | None = None) -> str:
    base = f"{config.dashboard_url}/guild/{guild_id}/giveaways"
    return f"{base}/{giveaway_id}" if giveaway_id else base


def dashboard_row(guild_id: int, giveaway_id: int | None = None, label: str = "Open dashboard") -> ui.ActionRow:
    return ui.ActionRow(
        ui.Button(
            label=label,
            emoji=emoji.settings_white,
            style=discord.ButtonStyle.link,
            url=dashboard_url(guild_id, giveaway_id),
        )
    )
