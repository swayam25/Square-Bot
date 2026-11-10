import asyncio
import discord
import math
from discord import ui
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from square import imaging
from square.cogs.invites.settings import InvitesPage
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, show_loading, success_view
from square.db import cache
from square.db.funcs.invites import (
    InviteCounts,
    add_bonus,
    fetch_counts,
    fetch_join,
    fetch_leaderboard,
    record_join,
    record_leave,
    reset_invites,
)
from square.imaging import assets
from square.imaging.templates import invite_card, leaderboard
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


async def _resolve_users(
    client: Client, guild: discord.Guild, user_ids: list[int]
) -> list[discord.User | discord.Member | None]:
    """Members or users by ID, from cache when possible. Inviters who left the server are fetched."""

    async def resolve(user_id: int) -> discord.User | discord.Member | None:
        if user := guild.get_member(user_id) or client.get_user(user_id):
            return user
        try:
            return await client.fetch_user(user_id)
        except discord.HTTPException:  # Deleted account
            return None

    return list(await asyncio.gather(*(resolve(user_id) for user_id in user_ids)))


def _shown_image_url(message: discord.Message) -> str | None:
    """The URL a message's media gallery is showing right now, falling back to its first attachment."""
    for component in message.components:
        for inner in component.walk_components() if isinstance(component, discord.Container) else [component]:
            if isinstance(inner, discord.MediaGallery) and inner.items:
                return inner.items[0].url
    return message.attachments[0].url if message.attachments else None


class LeaderboardView(DesignerView):
    """The invite leaderboard image, with start/previous/next/end buttons once there's more than one page."""

    def __init__(
        self,
        client: Client,
        ctx: discord.ApplicationContext,
        guild: discord.Guild,
        board: list[tuple[int, InviteCounts]],
        page: int = 1,
    ):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client, self.guild, self.board = client, guild, board
        self.pages = math.ceil(len(board) / LEADERBOARD_PAGE)
        self.page = min(page, self.pages)
        self._height: float | None = None

    async def _page_height(self) -> float:
        """
        The height of the fullest page, so every page renders at it.

        Discord sizes the image box to the image, so pages of different heights resize the message on every flip.
        """
        if self._height is None:
            if self.pages == 1:
                self._height = 0
            else:
                filler = [leaderboard.Inviter(rank, "", None, 0, 0, 0, 0, 0) for rank in range(1, LEADERBOARD_PAGE + 1)]
                full = [
                    leaderboard.Leaderboard(self.guild.name, None, 0, 0, page, self.pages, filler) for page in (1, 2)
                ]  # Page 1 has the podium, later pages only rows
                self._height = await imaging.tallest(leaderboard.build, full)
        return self._height

    async def _data(self) -> leaderboard.Leaderboard:
        start = (self.page - 1) * LEADERBOARD_PAGE
        entries = self.board[start : start + LEADERBOARD_PAGE]
        users = await _resolve_users(self.client, self.guild, [user_id for user_id, _ in entries])
        pictures = [
            user.display_avatar if user else assets.default_avatar(self.client, user_id)
            for (user_id, _), user in zip(entries, users, strict=True)
        ]
        *avatars, icon = await assets.fetch_many([*pictures, self.guild.icon])
        return leaderboard.Leaderboard(
            guild_name=self.guild.name,
            guild_icon=icon,
            member_count=self.guild.member_count or 0,
            fake_days=cache.get(self.guild.id).invite_fake_days,
            page=self.page,
            pages=self.pages,
            inviters=[
                leaderboard.Inviter(
                    rank=rank,
                    name=user.display_name if user else "Unknown user",
                    avatar=avatar,
                    total=counts.total,
                    regular=counts.regular,
                    left=counts.left,
                    fake=counts.fake,
                    bonus=counts.bonus,
                )
                for rank, (_, counts), user, avatar in zip(
                    range(start + 1, start + len(entries) + 1), entries, users, avatars, strict=True
                )
            ],
        )

    async def render(self) -> discord.File:
        """Draws the current page and rebuilds the view around it. Send the file along with the view."""
        data = await self._data()
        file = await imaging.render(
            leaderboard.build, data, filename="leaderboard.png", height=await self._page_height()
        )
        alt = ", ".join(f"{inviter.rank}. {inviter.name}: {inviter.total}" for inviter in data.inviters)
        self._image = discord.MediaGalleryItem("attachment://leaderboard.png", description=alt[:1024])
        self.clear_items()
        self.add_item(ui.Container(ui.MediaGallery(self._image)))
        if self.pages > 1:
            row = ui.ActionRow()
            for btn_emoji, action in (
                (emoji.start_white, "start"),
                (emoji.previous_white, "previous"),
                (emoji.next_white, "next"),
                (emoji.end_white, "end"),
            ):
                btn = ui.Button(emoji=btn_emoji, style=discord.ButtonStyle.grey, custom_id=f"leaderboard_{action}")
                btn.callback = lambda interaction, action=action: self._flip(interaction, action)
                row.add_item(btn)
            self.add_item(row)
        return file

    async def _flip(self, interaction: discord.Interaction, action: str) -> None:
        # An `attachment://` reference in the loading edit makes the client reload the image. The URL it already
        # shows keeps it still until the final edit swaps it.
        if interaction.message and (url := _shown_image_url(interaction.message)):
            self._image.media.url = url
        if not await show_loading(self, interaction):
            return
        self.page = {
            "start": 1,
            "previous": self.pages if self.page <= 1 else self.page - 1,
            "next": 1 if self.page >= self.pages else self.page + 1,
            "end": self.pages,
        }[action]
        file = await self.render()
        # `attachments=[]` drops the old page's image, otherwise pycord keeps it next to the new one
        await interaction.edit(view=self, file=file, attachments=[])


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
        await ctx.defer()  # Fetching the avatar and rendering can outlast the 3 second reply window
        counts, board, (avatar, icon) = await asyncio.gather(
            fetch_counts(guild.id, target.id),
            fetch_leaderboard(guild.id),
            assets.fetch_many([target.display_avatar, guild.icon]),
        )
        rank = next((rank for rank, (user_id, _) in enumerate(board, start=1) if user_id == target.id), None)
        data = invite_card.InviteCard(
            name=target.display_name,
            username=target.name,
            avatar=avatar,
            guild_name=guild.name,
            guild_icon=icon,
            rank=rank,
            regular=counts.regular,
            left=counts.left,
            fake=counts.fake,
            bonus=counts.bonus,
            fake_days=cache.get(guild.id).invite_fake_days,
        )
        file = await imaging.render(invite_card.build, data, filename="invites.png")
        alt = (
            f"{target.display_name}: {data.total} invites ({counts.regular} regular, {counts.bonus} bonus, "
            f"{counts.left} left, {counts.fake} fake)"
        )
        view = DesignerView(
            ui.Container(ui.MediaGallery(discord.MediaGalleryItem("attachment://invites.png", description=alt)))
        )
        await ctx.respond(view=view, file=file)

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
        await ctx.defer()  # Fetching avatars and rendering can outlast the 3 second reply window
        view = LeaderboardView(self.client, ctx, guild, board, page)
        file = await view.render()
        await ctx.respond(view=view, file=file)

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
