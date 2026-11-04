import discord
import math
from discord import ui
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from square.cogs.invites.settings import InvitesPage
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, success_view
from square.db import cache
from square.db.funcs.invites import (
    add_bonus,
    fetch_counts,
    fetch_join,
    fetch_leaderboard,
    record_join,
    record_leave,
    reset_invites,
)
from square.utils import config, invites, server_log
from square.utils.emoji import emoji

LEADERBOARD_PAGE = 10


class ResetAllView(DesignerView):
    """Asks before wiping every invite count in the server."""

    def __init__(self, ctx: discord.ApplicationContext):
        super().__init__(ctx=ctx, check_author_interaction=True, timeout=60)
        confirm = ui.Button(label="Reset every count", emoji=emoji.bin_white, style=discord.ButtonStyle.red)
        confirm.callback = self._confirm
        self.add_item(
            ui.Container(
                ui.TextDisplay("## Reset Invites"),
                ui.TextDisplay("This clears every member's invites and bonus in this server. It can't be undone."),
                color=config.color.red,
            )
        )
        self.add_item(ui.ActionRow(confirm))

    async def _confirm(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await reset_invites(interaction.guild.id)
        await interaction.response.edit_message(view=success_view("Reset every invite count in this server."))


class Invites(Cog, name="Invites", description="See who invited whom, with leaderboards.", emoji=emoji.invite, order=8):
    settings_pages = (InvitesPage,)

    def __init__(self, client: Client):
        self.client = client

    invites = SlashCommandGroup(name="invites", description="Invite tracker commands.")

    @staticmethod
    async def _tracked_guild(ctx: discord.ApplicationContext) -> discord.Guild | None:
        """The server, or None (after replying) when the tracker is off there."""
        if ctx.guild is not None and cache.get(ctx.guild.id).invite_tracker:
            return ctx.guild
        await ctx.respond(view=error_view("The invite tracker is off. Turn it on in `/settings`."), ephemeral=True)
        return None

    @staticmethod
    async def _managed_guild(ctx: discord.ApplicationContext) -> discord.Guild | None:
        """The server, or None (after replying) when the member lacks Manage Server."""
        # Subcommands can't carry their own default permissions, so the stricter ones check here
        if (
            ctx.guild is not None
            and isinstance(ctx.author, discord.Member)
            and ctx.author.guild_permissions.manage_guild
        ):
            return ctx.guild
        await ctx.respond(view=error_view("You need the `Manage Server` permission for this."), ephemeral=True)
        return None

    @invites.command(name="user")
    @option("member", description="Whose invites to show. Defaults to you.", required=False)
    async def invites_user(self, ctx: discord.ApplicationContext, member: discord.Member | None = None):
        """Shows how many members someone has invited."""
        if not (guild := await self._tracked_guild(ctx)):
            return
        target = member or ctx.author
        counts = await fetch_counts(guild.id, target.id)
        view = DesignerView(
            ui.Container(
                ui.Section(
                    ui.TextDisplay(f"## {target.display_name}'s Invites"),
                    ui.TextDisplay(
                        f"{emoji.joins} **Regular**: `{counts.regular}`\n"
                        f"{emoji.left} **Left**: `{counts.left}`\n"
                        f"{emoji.fake} **Fake**: `{counts.fake}`\n"
                        f"{emoji.bonus} **Bonus**: `{counts.bonus}`\n"
                        f"{emoji.invite} **Total**: `{counts.total}`"
                    ),
                    accessory=ui.Thumbnail(url=target.display_avatar.url),
                )
            )
        )
        await ctx.respond(view=view)

    @invites.command(name="leaderboard")
    @option("page", description="The page to show.", min_value=1, required=False)
    async def invites_leaderboard(self, ctx: discord.ApplicationContext, page: int = 1):
        """Shows the server's top inviters."""
        if not (guild := await self._tracked_guild(ctx)):
            return
        board = await fetch_leaderboard(guild.id)
        if not board:
            await ctx.respond(view=error_view("Nobody has invited anyone yet."), ephemeral=True)
            return
        pages = math.ceil(len(board) / LEADERBOARD_PAGE)
        page = min(page, pages)
        start = (page - 1) * LEADERBOARD_PAGE
        lines = [
            f"`{rank}.` <@{user_id}> · `{counts.total}` invites"
            for rank, (user_id, counts) in enumerate(board[start : start + LEADERBOARD_PAGE], start=start + 1)
        ]
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"## {emoji.leaderboard} Invite Leaderboard"),
                ui.TextDisplay("\n".join(lines)),
                ui.TextDisplay(f"-# Page {page} of {pages}"),
            )
        )
        await ctx.respond(view=view)

    @invites.command(name="who")
    @option("member", description="The member to look up.")
    async def invites_who(self, ctx: discord.ApplicationContext, member: discord.Member):
        """Shows who invited a member."""
        if not (guild := await self._tracked_guild(ctx)):
            return
        join = await fetch_join(guild.id, member.id)
        if join is None or join.inviter_id is None:
            await ctx.respond(view=error_view(f"I don't know who invited {member.mention}."), ephemeral=True)
            return
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"## How {member.display_name} Joined"),
                ui.TextDisplay(
                    f"{emoji.user} **Invited By**: <@{join.inviter_id}>\n"
                    f"{emoji.invite} **Code**: `{join.code or 'unknown'}`\n"
                    f"{emoji.date} **Joined**: {discord.utils.format_dt(join.joined_at, 'R')}"
                    + (f"\n{emoji.fake} **Counted As Fake**: account was too new" if join.fake else "")
                ),
            )
        )
        await ctx.respond(view=view)

    @invites.command(name="bonus")
    @option("member", description="Who gets the bonus invites.")
    @option("amount", description="How many to add. Negative numbers take some away.", min_value=-1000, max_value=1000)
    async def invites_bonus(self, ctx: discord.ApplicationContext, member: discord.Member, amount: int):
        """Adds or removes bonus invites."""
        if not await self._tracked_guild(ctx) or not (guild := await self._managed_guild(ctx)):
            return
        bonus = await add_bonus(guild.id, member.id, amount)
        await ctx.respond(view=success_view(f"Successfully set {member.mention}'s bonus invites to `{bonus}`."))

    @invites.command(name="reset")
    @option("member", description="Whose invites to reset. Leave empty for the whole server.", required=False)
    async def invites_reset(self, ctx: discord.ApplicationContext, member: discord.Member | None = None):
        """Resets invite counts for a member or the whole server."""
        if not (guild := await self._managed_guild(ctx)):
            return
        if member is None:
            await ctx.respond(view=ResetAllView(ctx), ephemeral=True)
            return
        await reset_invites(guild.id, member.id)
        await ctx.respond(view=success_view(f"Successfully reset {member.mention}'s invites."))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot or not cache.get(member.guild.id).invite_tracker:
            return
        used = await invites.used_invite(member)  # Shared with the member log, one lookup per join
        inviter_id, code = (used.inviter_id, used.code) if used else (None, None)
        fake = await record_join(member.guild.id, member, inviter_id, code)
        if inviter_id is None:
            return
        total = (await fetch_counts(member.guild.id, inviter_id)).total
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Invite Used"),
                ui.TextDisplay(
                    f"{emoji.joins_green} **Member**: {member.mention} (`{member.name}`)\n"
                    f"{emoji.user_green} **Invited By**: <@{inviter_id}>\n"
                    f"{emoji.description_green} **Code**: `{code}`\n"
                    f"{emoji.members_green} **Their Invites**: `{total}`"
                    + ("\n-# Counted as fake, the account is too new." if fake else "")
                ),
                color=config.color.green,
            )
        )
        await server_log.send(self.client, member.guild, server_log.LogType.INVITES, view)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not member.bot and cache.get(member.guild.id).invite_tracker:
            await record_leave(member.guild.id, member.id)


def setup(client: Client):
    client.add_cog(Invites(client))
