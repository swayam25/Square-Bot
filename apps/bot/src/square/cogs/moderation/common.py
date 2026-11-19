import discord
from collections.abc import Awaitable, Callable
from discord import ui
from square.core.view import DesignerView, error_view, modal, not_in_server
from square.utils import config

Refusal = Callable[[discord.Member, discord.Member | discord.User], str | None]


def outranked(moderator: discord.Member, user: discord.Member | discord.User) -> str | None:
    if user == moderator:
        return "You cannot use it on yourself."
    if isinstance(user, discord.Member) and user.top_role.position >= moderator.top_role.position:
        return "Given user has same role or higher role than you."
    return None


def dms_closed(messaged: bool) -> str:
    return "" if messaged else "\n-# They have DMs closed, so they weren't told."


def result_view(title: str, user: discord.abc.User, text: str) -> DesignerView:
    return DesignerView(
        ui.Container(
            ui.Section(
                ui.TextDisplay(f"## {title}"),
                ui.TextDisplay(text),
                accessory=ui.Thumbnail(url=user.display_avatar.url),
            ),
            color=config.color.green,
        )
    )


def field(*, required: bool = False, long: bool = False, max_length: int = 512, **kwargs) -> ui.InputText:
    style = discord.InputTextStyle.long if long else discord.InputTextStyle.short
    return ui.InputText(style=style, required=required, max_length=max_length, **kwargs)


def answer(item: ui.InputText) -> str | None:
    return (item.value or "").strip() or None


async def prompt(
    ctx: discord.ApplicationContext,
    user: discord.Member | discord.User,
    title: str,
    fields: dict[str, ui.InputText],
    run: Callable[[discord.Interaction], Awaitable[None]],
    *,
    refuse: Refusal = outranked,
    members_only: bool = True,
) -> None:
    """Opens the modal behind a right-click command, refusing first so nobody fills in a form for nothing."""
    if members_only and await not_in_server(ctx, user):
        return
    if problem := refuse(ctx.author, user):
        await ctx.respond(view=error_view(problem), ephemeral=True)
        return
    labels = (ui.Label(label, item) for label, item in fields.items())
    await ctx.send_modal(modal(title, *labels, on_submit=run))
