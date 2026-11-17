import datetime
import discord
from babel.dates import format_timedelta
from dataclasses import dataclass
from discord import ui
from discord.commands import SlashCommandGroup, option, slash_command
from square.core import Client
from square.core.view import DesignerView, error_view, success_view
from square.db.funcs import automod as automod_db
from square.db.schema import WarningTable, WarnPunishmentTable
from square.utils import config, server_log
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count

LIST_LIMIT = 10
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


async def _punish(guild: discord.Guild, member: discord.Member, step: WarnPunishmentTable) -> bool:
    if not _can_punish(guild, member):
        return False
    reason = f"Reached {step.warnings} warnings"
    try:
        match step.action:
            case "timeout":
                await member.timeout_for(datetime.timedelta(seconds=step.seconds or 60), reason=reason)
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

    # Before the punishment, so a kicked or banned member still shares a server with the bot
    dm = DesignerView(
        ui.Container(
            ui.TextDisplay(f"## Warned in {guild.name}"),
            ui.TextDisplay(
                f"{emoji.description_orange} **Reason**: {reason or 'No reason given'}\n"
                f"{emoji.id} **Warnings**: {fmt_count(total)}"
                + (f"\n{emoji.mod} **Punishment**: {punishment}" if punishment else "")
            ),
            color=config.color.orange,
        )
    )
    try:
        await member.send(view=dm)
        messaged = True
    except discord.Forbidden, discord.HTTPException:
        messaged = False

    punished = await _punish(guild, member, step) if step else False
    by = moderator.mention if moderator else "AutoMod"
    await server_log.send(
        client,
        guild,
        server_log.LogType.MODERATION,
        DesignerView(
            ui.Container(
                ui.TextDisplay("## Member Warned"),
                ui.TextDisplay(
                    f"{emoji.user_orange} **Member**: {member.mention} (`{member.name}`)\n"
                    f"{emoji.mod} **By**: {by}\n"
                    f"{emoji.description_orange} **Reason**: {reason or 'No reason given'}\n"
                    f"{emoji.id} **Warnings**: {fmt_count(total)}"
                    + (f"\n{emoji.mod_red} **Punishment**: {punishment}" if punishment and punished else "")
                    + (f"\n{emoji.mod_red} **Punishment failed**: {punishment}" if punishment and not punished else "")
                ),
                color=config.color.orange,
            )
        ),
    )
    return Warned(warning, total, punishment, punished, messaged)


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
        if problem := _refusal(ctx, user):
            await ctx.respond(view=error_view(problem), ephemeral=True)
            return
        await ctx.defer()
        warned = await warn(self.client, ctx.guild, user, reason, ctx.author)
        lines = [
            f"{emoji.description_green} **Reason**: {reason or 'No reason given'}",
            f"{emoji.id_green} **Warnings**: {fmt_count(warned.total)}",
        ]
        if warned.punishment:
            lines.append(
                f"{emoji.mod} **Punishment**: {warned.punishment}"
                if warned.punished
                else f"{emoji.mod_red} **Punishment failed**: I couldn't apply `{warned.punishment}`, "
                "their role is above mine or I'm missing the permission."
            )
        if not warned.messaged:
            lines.append(f"-# {user.display_name} has DMs closed, so they weren't told.")
        view = DesignerView(
            ui.Container(
                ui.Section(
                    ui.TextDisplay("## Warned User"),
                    ui.TextDisplay(f"Warned {user.mention}.\n" + "\n".join(lines)),
                    accessory=ui.Thumbnail(url=user.display_avatar.url),
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view, allowed_mentions=discord.AllowedMentions.none())

    warnings = SlashCommandGroup(
        name="warnings",
        description="Warning related commands.",
        default_member_permissions=discord.Permissions(moderate_members=True),
    )

    @warnings.command(name="list")
    @option("user", description="Mention the user whose warnings you want to see")
    async def warnings_list(self, ctx: discord.ApplicationContext, user: discord.User):
        """Shows a user's latest warnings."""
        found, total = await automod_db.fetch_warnings(ctx.guild.id, user.id, LIST_LIMIT)
        if not total:
            await ctx.respond(view=success_view(f"{user.mention} has no warnings."), ephemeral=True)
            return
        rows = [
            f"`#{warning.id}` · {discord.utils.format_dt(warning.created_at, 'R')} · "
            f"{f'<@{warning.moderator_id}>' if warning.moderator_id else 'AutoMod'}\n"
            f"-# {discord.utils.escape_markdown(warning.reason) or 'No reason given'}"
            for warning in found
        ]
        more = f"\n-# Showing the latest {LIST_LIMIT}." if total > LIST_LIMIT else ""
        view = DesignerView(
            ui.Container(
                ui.Section(
                    ui.TextDisplay(f"## Warnings · {fmt_count(total)}"),
                    ui.TextDisplay(f"{user.mention}\n\n" + "\n".join(rows) + more),
                    accessory=ui.Thumbnail(url=user.display_avatar.url),
                ),
                color=config.color.orange,
            )
        )
        await ctx.respond(view=view, ephemeral=True)

    @warnings.command(name="remove")
    @option("warning", description="Enter the warning number, shown as #number in the list", min_value=1)
    async def warnings_remove(self, ctx: discord.ApplicationContext, warning: int):
        """Removes one warning."""
        removed = await automod_db.remove_warning(ctx.guild.id, warning)
        if removed is None:
            await ctx.respond(view=error_view(f"There's no warning `#{warning}` in this server."), ephemeral=True)
            return
        await ctx.respond(view=success_view(f"Removed warning `#{warning}` from <@{removed.user_id}>."))

    @warnings.command(name="clear")
    @option("user", description="Mention the user whose warnings you want to clear")
    async def warnings_clear(self, ctx: discord.ApplicationContext, user: discord.User):
        """Removes every warning a user has."""
        count = await automod_db.clear_warnings(ctx.guild.id, user.id)
        if not count:
            await ctx.respond(view=error_view(f"{user.mention} has no warnings."), ephemeral=True)
            return
        await ctx.respond(view=success_view(f"Cleared {fmt_count(count)} warnings from {user.mention}."))
