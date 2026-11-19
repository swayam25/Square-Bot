import contextlib
import datetime
import discord
from collections.abc import Awaitable
from discord import ui
from square.core.view import DesignerView
from square.utils import config
from square.utils.emoji import emoji

type Row = tuple[str, str, str]

# Discord caps button labels at 80 characters, server names run to 100
LABEL_LIMIT = 80


def _icon(name: str, color: int) -> str:
    suffix = {config.color.red: "_red", config.color.orange: "_orange", config.color.green: "_green"}[color]
    return str(getattr(emoji, f"{name}{suffix}"))


def moderation_rows(reason: str | None, moderator: discord.abc.User | None) -> list[Row]:
    """`moderator` is None when AutoMod acts."""
    by = f"{moderator.mention} (`{moderator.name}`)" if moderator else "AutoMod"
    return [("note", "Reason", reason or "No reason given"), ("owner", "Moderator", by)]


def view(
    guild: discord.Guild, title: str, color: int, rows: list[Row], *, note: str | None = None, member: bool = True
) -> DesignerView:
    """`member` False greys out the server link, since it can't open a server the user was removed from."""
    body = "\n".join(f"{_icon(name, color)} **{label}**: {value}" for name, label, value in rows)
    if note:
        body = f"{body}\n{note}" if body else note
    label = f"Sent from {guild.name}"
    return DesignerView(
        ui.Container(ui.TextDisplay(f"## {title}"), ui.TextDisplay(body), color=color),
        ui.ActionRow(
            ui.Button(
                label=label if len(label) <= LABEL_LIMIT else label[: LABEL_LIMIT - 1] + "…",
                url=f"https://discord.com/channels/{guild.id}",
                disabled=not member,
            )
        ),
    )


def duration_row(until: datetime.datetime) -> Row:
    return ("duration", "Duration", discord.utils.format_dt(until, "R"))


def timed_out(
    guild: discord.Guild,
    until: datetime.datetime,
    reason: str | None,
    moderator: discord.abc.User | None,
) -> DesignerView:
    rows = moderation_rows(reason, moderator) + [duration_row(until)]
    return view(guild, "You got timed out", config.color.orange, rows)


async def send(user: discord.abc.User, dm: DesignerView) -> discord.Message | None:
    """None when the user has DMs closed."""
    try:
        return await user.send(view=dm)
    except discord.Forbidden, discord.HTTPException:
        return None


async def send_before(user: discord.abc.User, dm: DesignerView, removal: Awaitable) -> bool:
    """
    DMs first, since a kicked or banned user no longer shares a server with the bot, then runs `removal`.

    Deletes the DM again if `removal` fails, so nobody is told about a kick or ban that never happened.
    """
    sent = await send(user, dm)
    try:
        await removal
    except BaseException:
        if sent:
            with contextlib.suppress(discord.HTTPException):
                await sent.delete()
        raise
    return sent is not None
