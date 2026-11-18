import datetime
import discord
import math
from babel.dates import format_timedelta
from contextlib import suppress
from dataclasses import dataclass
from discord import ui
from discord.commands import option, slash_command
from square.core import Client
from square.core.view import DesignerView, button, error_view, not_in_server, show_loading, success_view
from square.db.funcs import automod as automod_db
from square.db.schema import WarningTable, WarnPunishmentTable
from square.utils import config, mod_dm, server_log
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count, plural

PAGE_SIZE = 5
MAX_REASON = 500


def punishment_text(step: WarnPunishmentTable) -> str:
    match step.action:
        case "timeout":
            return f"Timed out for {format_timedelta(datetime.timedelta(seconds=step.seconds or 60), locale='en')}"
        case "kick":
            return "Kicked"
    return "Banned"


@dataclass
class Warned:
    warning: WarningTable
    total: int
    punishment: str | None
    punished: bool
    messaged: bool


def _can_punish(guild: discord.Guild, member: discord.Member) -> bool:
    return member != guild.owner and member.top_role < guild.me.top_role


async def _punish(
    guild: discord.Guild, member: discord.Member, step: WarnPunishmentTable, until: datetime.datetime | None
) -> bool:
    if not _can_punish(guild, member):
        return False
    reason = f"Reached {step.warnings} {plural(step.warnings, 'warning')}"
    try:
        match step.action:
            case "timeout":
                await member.timeout(until, reason=reason)
            case "kick":
                await member.kick(reason=reason)
            case "ban":
                await guild.ban(member, reason=reason, delete_message_seconds=0)
    except discord.Forbidden, discord.NotFound:
        return False
    return True


async def warn(
    client: Client,
    guild: discord.Guild,
    member: discord.Member,
    reason: str,
    moderator: discord.Member | None,
) -> Warned:
    """`moderator` is None when AutoMod gives the warning."""
    warning, total = await automod_db.add_warning(guild.id, member.id, moderator.id if moderator else None, reason)
    step = next((step for step in automod_db.punishments(guild.id) if step.warnings == total), None)
    punishment = punishment_text(step) if step else None

    rows = mod_dm.moderation_rows(reason, moderator) + [("warning", "Warnings", fmt_count(total))]
    until = None
    punishment_rows: list[mod_dm.Row] = []
    if step and step.action == "timeout":
        length = datetime.timedelta(seconds=step.seconds or 60)
        until = discord.utils.utcnow() + length
        punishment_rows = [("mod", "Punishment", "Timed out"), mod_dm.duration_row(until)]
    elif punishment:
        punishment_rows = [("mod", "Punishment", punishment)]
    removed = step is not None and step.action in ("kick", "ban")
    dm = mod_dm.view(guild, "You got warned", config.color.orange, rows + punishment_rows, member=not removed)
    # Before the punishment, so a kicked or banned member still shares a server with the bot
    sent = await mod_dm.send(member, dm)
    messaged = sent is not None

    punished = await _punish(guild, member, step, until) if step else False
    if sent and step and not punished:
        with suppress(discord.HTTPException):
            await sent.edit(view=mod_dm.view(guild, "You got warned", config.color.orange, rows))
    by = f"{moderator.mention} (`{moderator.name}`)" if moderator else "AutoMod"
    await server_log.send(
        client,
        guild,
        server_log.LogType.MODERATION,
        DesignerView(
            ui.Container(
                ui.TextDisplay("## Member Warned"),
                ui.TextDisplay(
                    f"{emoji.user_orange} **Member**: {member.mention} (`{member.name}`)\n"
                    f"{emoji.id_orange} **ID**: `{member.id}`\n"
                    f"{emoji.owner_orange} **Moderator**: {by}\n"
                    f"{emoji.description_orange} **Reason**: {reason or 'No reason given'}\n"
                    f"{emoji.warning_orange} **Warnings**: {fmt_count(total)}"
                    + (f"\n{emoji.mod_orange} **Punishment**: {punishment}" if punishment and punished else "")
                    + (
                        f"\n{emoji.mod_orange} **Punishment failed**: {punishment}"
                        if punishment and not punished
                        else ""
                    )
                ),
                color=config.color.orange,
            )
        ),
    )
    return Warned(warning, total, punishment, punished, messaged)


class WarningsList(DesignerView):
    def __init__(self, guild: discord.Guild, user: discord.User):
        super().__init__()
        self.guild = guild
        self.user = user
        self.page = 0
        self.confirming = False

    def empty(self) -> DesignerView:
        return success_view(f"{self.user.mention} (`{self.user.name}`) has no warnings.")

    async def build(self) -> bool:
        """Returns False when the user has no warnings left."""
        total = await automod_db.count_warnings(self.guild.id, self.user.id)
        if not total:
            return False
        pages = math.ceil(total / PAGE_SIZE)
        self.page = min(self.page, pages - 1)
        start = self.page * PAGE_SIZE
        found = await automod_db.fetch_warnings(self.guild.id, self.user.id, start, PAGE_SIZE)

        self.clear_items()
        container = ui.Container(
            ui.Section(
                ui.TextDisplay(f"## Warnings · {fmt_count(total)}"),
                ui.TextDisplay(f"{self.user.mention} (`{self.user.name}`)"),
                accessory=ui.Thumbnail(url=self.user.display_avatar.url),
            ),
            color=config.color.orange,
        )
        for index, warning in enumerate(found):
            number = total - start - index
            by = f"<@{warning.moderator_id}> (`{warning.moderator_id}`)" if warning.moderator_id else "AutoMod"
            reason = discord.utils.escape_markdown(warning.reason) or "No reason given"
            container.add_item(
                ui.Section(
                    ui.TextDisplay(
                        f"`{number}.` {discord.utils.format_dt(warning.created_at, 'R')} · {by}\n"
                        f"-# {emoji.bottom_right_orange} {reason}"
                    ),
                    accessory=button(
                        lambda i, warning_id=warning.id: self._remove(i, warning_id),
                        emoji=emoji.bin_white,
                        disabled=self.confirming,
                    ),
                )
            )
        if pages > 1:
            container.add_item(ui.Separator())
            container.add_item(ui.TextDisplay(f"-# Viewing Page {self.page + 1}/{pages}"))
        self.add_item(container)
        if self.confirming:
            self.add_item(
                ui.ActionRow(
                    button(lambda i: self._confirm(i, False), label="Cancel"),
                    button(
                        self._clear,
                        label=f"Yes, clear {fmt_count(total)} {plural(total, 'warning')}",
                        emoji=emoji.bin_white,
                        style=discord.ButtonStyle.red,
                    ),
                )
            )
            return True
        clear = button(
            lambda i: self._confirm(i, True), label="Clear all", emoji=emoji.bin_white, style=discord.ButtonStyle.red
        )
        if pages == 1:
            self.add_item(ui.ActionRow(clear))
            return True
        last = pages - 1
        arrows = [
            button(lambda i, page=page: self._go(i, page), emoji=icon)
            for icon, page in (
                (emoji.start_white, 0),
                (emoji.previous_white, last if self.page == 0 else self.page - 1),
                (emoji.next_white, 0 if self.page == last else self.page + 1),
                (emoji.end_white, last),
            )
        ]
        self.add_item(ui.ActionRow(*arrows[:2], clear, *arrows[2:]))
        return True

    async def _redraw(self, interaction: discord.Interaction) -> None:
        await interaction.edit_original_response(view=self if await self.build() else self.empty())

    async def _go(self, interaction: discord.Interaction, page: int) -> None:
        if not await show_loading(self, interaction):
            return
        self.page = page
        await self._redraw(interaction)

    async def _remove(self, interaction: discord.Interaction, warning_id: int) -> None:
        if not await show_loading(self, interaction):
            return
        await automod_db.remove_warning(self.guild.id, self.user.id, warning_id)
        await self._redraw(interaction)

    async def _confirm(self, interaction: discord.Interaction, confirming: bool) -> None:
        if not await show_loading(self, interaction):
            return
        self.confirming = confirming
        await self._redraw(interaction)

    async def _clear(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self, interaction):
            return
        count = await automod_db.clear_warnings(self.guild.id, self.user.id)
        await interaction.edit_original_response(
            view=success_view(
                f"Cleared {fmt_count(count)} {plural(count, 'warning')} from {self.user.mention} (`{self.user.name}`)."
            )
            if count
            else self.empty()
        )


def _refusal(ctx: discord.ApplicationContext, member: discord.Member) -> str | None:
    if member == ctx.author:
        return "You cannot use it on yourself."
    if member.bot:
        return "Bots can't be warned."
    if ctx.author != ctx.guild.owner and member.top_role.position >= ctx.author.top_role.position:
        return "Given user has same role or higher role than you."
    return None


class Warnings:
    client: Client

    @slash_command(name="warn")
    @discord.default_permissions(moderate_members=True)
    @option("user", description="Mention the user whom you want to warn")
    @option("reason", description="Enter the reason for the warning", required=False, max_length=MAX_REASON)
    async def warn_user(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str = ""):
        """Warns the mentioned user. Enough warnings set off the punishments from the dashboard."""
        if await not_in_server(ctx, user):
            return
        if problem := _refusal(ctx, user):
            await ctx.respond(view=error_view(problem), ephemeral=True)
            return
        await ctx.defer()
        warned = await warn(self.client, ctx.guild, user, reason, ctx.author)
        lines = [
            f"{emoji.description_green} **Reason**: {reason or 'No reason given'}",
            f"{emoji.warning_green} **Warnings**: {fmt_count(warned.total)}",
        ]
        if warned.punishment:
            lines.append(
                f"{emoji.mod_green} **Punishment**: {warned.punishment}"
                if warned.punished
                else f"{emoji.mod_green} **Punishment failed**: I couldn't apply `{warned.punishment}`, "
                "their role is above mine or I'm missing the permission."
            )
        if not warned.messaged:
            lines.append("-# They have DMs closed, so they weren't told.")
        view = DesignerView(
            ui.Container(
                ui.Section(
                    ui.TextDisplay("## Warned User"),
                    ui.TextDisplay(f"Warned {user.mention} (`{user.name}`).\n" + "\n".join(lines)),
                    accessory=ui.Thumbnail(url=user.display_avatar.url),
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view, allowed_mentions=discord.AllowedMentions.none())

    @slash_command(name="warnings")
    @discord.default_permissions(moderate_members=True)
    @option("user", description="Mention the user whose warnings you want to see")
    async def warnings(self, ctx: discord.ApplicationContext, user: discord.User):
        """Shows a user's warnings, with buttons to remove one or clear them all."""
        view = WarningsList(ctx.guild, user)
        if not await view.build():
            await ctx.respond(view=view.empty(), ephemeral=True)
            return
        await ctx.respond(view=view, ephemeral=True)
