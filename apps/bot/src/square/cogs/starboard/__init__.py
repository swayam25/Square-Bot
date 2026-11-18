import asyncio
import discord
from datetime import UTC, datetime, timedelta
from discord import ui
from discord.commands import SlashCommandGroup, message_command, option
from discord.ext import commands, tasks
from square import imaging
from square.cogs.starboard import actions, cards
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, show_loading
from square.db import cache
from square.db.funcs import starboard as starboard_db
from square.db.funcs.starboard import emoji_key
from square.db.schema import StarboardTable
from square.imaging import assets
from square.imaging.templates import starboard_card
from square.modules import Module, ModuleOff
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count

TOP_SHOWN = 10
# Long enough to cover the votes on any message people are still starring
VOTE_KEEP = timedelta(days=7)


def _channel(guild: discord.Guild, channel_id: int) -> discord.abc.GuildChannel | discord.Thread | None:
    return guild.get_channel_or_thread(channel_id)


def _button(action: str, board: StarboardTable, message: discord.Message, label: str, **kwargs) -> ui.Button:
    custom_id = f"starboard:{action}:{board.id}:{message.channel.id}:{message.id}"
    return ui.Button(custom_id=custom_id, label=label, style=kwargs.pop("style", discord.ButtonStyle.grey), **kwargs)


class Starboard(
    Cog,
    name="Starboard",
    description="Keep the best messages on a board people vote for with reactions.",
    emoji=emoji.star,
    order=10,
    module=Module.STARBOARD,
):
    def __init__(self, client: Client):
        self.client = client
        self.sweep.start()

    def cog_unload(self):
        self.sweep.cancel()

    @tasks.loop(hours=24)
    async def sweep(self):
        await starboard_db.sweep(datetime.now(UTC) - VOTE_KEEP)

    @sweep.before_loop
    async def _before_sweep(self):
        await self.client.wait_until_ready()

    starboard = SlashCommandGroup(name="starboard", description="Starboard commands.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._vote(payload, added=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._vote(payload, added=False)

    async def _vote(self, payload: discord.RawReactionActionEvent, *, added: bool) -> None:
        if not payload.guild_id or not (guild := self.client.get_guild(payload.guild_id)):
            return
        key = emoji_key(payload.emoji)
        channel = _channel(guild, payload.channel_id)
        if channel is None or not actions.boards_for(guild.id, channel, key):
            return
        if added:
            await starboard_db.add_vote(guild.id, payload.message_id, payload.channel_id, payload.user_id, key)
        else:
            await starboard_db.remove_vote(payload.message_id, payload.user_id, key)
        actions.schedule(self.client, guild.id, payload.channel_id, payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        if payload.guild_id and actions.active_boards(payload.guild_id):
            actions.schedule(self.client, payload.guild_id, payload.channel_id, payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionClearEmojiEvent):
        if payload.guild_id and actions.active_boards(payload.guild_id):
            actions.schedule(self.client, payload.guild_id, payload.channel_id, payload.message_id)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if not payload.guild_id or not actions.active_boards(payload.guild_id):
            return
        if await starboard_db.posts_for([payload.message_id]):
            actions.schedule(self.client, payload.guild_id, payload.channel_id, payload.message_id)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        await self._deleted(payload.guild_id, [payload.message_id])

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        await self._deleted(payload.guild_id, list(payload.message_ids))

    async def _deleted(self, guild_id: int | None, message_ids: list[int]) -> None:
        if not guild_id or not starboard_db.boards(guild_id):
            return
        await actions.post_gone(self.client, message_ids)
        await actions.source_gone(self.client, message_ids)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await starboard_db.forget_channel(channel.id)
        if board := starboard_db.board_in(channel.guild.id, channel.id):
            await starboard_db.save_board(channel.guild.id, board, enabled=False)
            await starboard_db.clear_post_ids([board.id])

    @staticmethod
    async def _panel(guild: discord.Guild, message: discord.Message) -> DesignerView:
        votes = await starboard_db.message_votes(message.id)
        posts = {post.board_id: post for post in await starboard_db.posts_for([message.id])}
        container = ui.Container(ui.TextDisplay("## Starboard"))
        for board in starboard_db.boards(guild.id):
            post = posts.get(board.id)
            on_board = bool(post and post.post_id)
            status = cards.board_status(board, actions.score(board, message, votes), on_board)
            if not board.enabled:
                container.add_item(ui.TextDisplay(f"{status}\n-# This board is turned off."))
                continue
            if on_board:
                button = _button(
                    "remove", board, message, "Remove", emoji=emoji.bin_white, style=discord.ButtonStyle.red
                )
            else:
                button = _button("post", board, message, "Post", emoji=emoji.star_white)
            container.add_item(ui.Section(ui.TextDisplay(status), accessory=button))
        return DesignerView(container, timeout=None, store=False)

    @message_command(
        name="Starboard",
        default_member_permissions=discord.Permissions(manage_messages=True),
        contexts={discord.InteractionContextType.guild},
    )
    async def manage(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Posts or removes a message on the starboards."""
        assert ctx.guild is not None
        if not starboard_db.boards(ctx.guild.id):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} This server has no starboard yet."), color=config.color.red
                ),
                ui.ActionRow(
                    ui.Button(
                        label="Open dashboard",
                        emoji=emoji.settings_white,
                        style=discord.ButtonStyle.link,
                        url=cards.dashboard_url(ctx.guild.id),
                    )
                ),
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        if board := starboard_db.board_in(ctx.guild.id, message.channel.id):
            # Picked on a post, so it acts on the message the post shows
            post = await starboard_db.fetch_by_post(message.id)
            if post is None:
                view = error_view(
                    f"Messages in <#{board.channel_id}> can't go on a starboard, since it is one. "
                    "Pick a message from another channel."
                )
                await ctx.respond(view=view, ephemeral=True)
                return
            try:
                source = await actions.fetch(self.client, ctx.guild.id, post.channel_id, post.message_id)
            except discord.HTTPException:
                source = None
            if source is None:
                await ctx.respond(
                    view=error_view("The message this post shows is gone. It or its channel was deleted."),
                    ephemeral=True,
                )
                return
            message = source
        await ctx.respond(view=await self._panel(ctx.guild, message), ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type is not discord.InteractionType.component:
            return
        custom_id = str((interaction.data or {}).get("custom_id", ""))
        if not custom_id.startswith("starboard:"):
            return
        guild, member = interaction.guild, interaction.user
        if not guild or not isinstance(member, discord.Member):
            return
        if not cache.enabled(guild.id, Module.STARBOARD):
            await interaction.response.send_message(view=error_view(str(ModuleOff(Module.STARBOARD))), ephemeral=True)
            return
        parts = custom_id.split(":")
        if len(parts) != 5 or not all(part.isdigit() for part in parts[2:]):
            return
        action, board_id, channel_id, message_id = parts[1], int(parts[2]), int(parts[3]), int(parts[4])
        channel = _channel(guild, channel_id)
        if channel is None or not channel.permissions_for(member).manage_messages:
            await interaction.response.send_message(
                view=error_view("You need `Manage Messages` in that channel."), ephemeral=True
            )
            return
        board = starboard_db.fetch_board(guild.id, board_id)
        try:
            message = await actions.fetch(self.client, guild.id, channel_id, message_id)
        except discord.HTTPException:
            message = None
        if board is None or message is None:
            await interaction.response.edit_message(view=error_view("That message or starboard is gone."))
            return
        if not await show_loading(await self._panel(guild, message), interaction):
            return
        await self._act(action, board, message)
        await interaction.edit_original_response(view=await self._panel(guild, message))

    async def _act(self, action: str, board: StarboardTable, message: discord.Message) -> None:
        post = await starboard_db.fetch_post(board.id, message.id)
        if action == "post":
            await starboard_db.save_post(board, message, forced=True)
        elif action == "remove" and post:
            await actions.remove(self.client, board, post)
            return
        assert message.guild is not None
        await actions.refresh(self.client, message.guild.id, message.channel.id, message.id)

    async def _boards(
        self, ctx: discord.ApplicationContext, channel: discord.TextChannel | None
    ) -> list[StarboardTable]:
        """The board in `channel`, or every board when none was picked. Empty after replying why."""
        assert ctx.guild is not None
        boards = starboard_db.boards(ctx.guild.id)
        if channel:
            boards = [board for board in boards if board.channel_id == channel.id]
        if not boards:
            text = f"{channel.mention} isn't a starboard." if channel else "This server has no starboard yet."
            await ctx.respond(view=error_view(text), ephemeral=True)
        return boards

    @starboard.command(name="top")
    @option("channel", description="Only this starboard.", default=None)
    @option("user", description="Only this user's messages.", default=None)
    async def top(
        self, ctx: discord.ApplicationContext, channel: discord.TextChannel | None, user: discord.Member | None
    ):
        """Shows the most starred messages."""
        assert ctx.guild is not None
        if not (boards := await self._boards(ctx, channel)):
            return
        posts = await starboard_db.top_posts([board.id for board in boards], user.id if user else None, TOP_SHOWN)
        title = f"## Top of <#{boards[0].channel_id}>" if len(boards) == 1 else "## Top starred"
        container = ui.Container(ui.TextDisplay(title))
        if not posts:
            container.add_item(ui.TextDisplay("Nothing has made it onto the board yet."))
        for rank, post in enumerate(posts, 1):
            shown = cards.stored_tally(post).emoji
            sent = discord.utils.format_dt(discord.utils.snowflake_time(post.message_id), "R")
            text = (
                f"`#{rank}` {shown} **{fmt_count(post.score)}** · <@{post.author_id}>\n"
                f"-# {emoji.bottom_right} <#{post.channel_id}> · {sent}"
            )
            jump = ui.Button(
                label="Jump",
                style=discord.ButtonStyle.link,
                url=cards.jump_url(ctx.guild.id, post.board.channel_id, post.post_id or 0),
            )
            container.add_item(ui.Section(ui.TextDisplay(text), accessory=jump))
        await ctx.respond(view=DesignerView(container), ephemeral=True)

    @starboard.command(name="random")
    @option("channel", description="Only this starboard.", default=None)
    async def random(self, ctx: discord.ApplicationContext, channel: discord.TextChannel | None):
        """Shows a random message from the starboard."""
        assert ctx.guild is not None
        if not (boards := await self._boards(ctx, channel)):
            return
        # Age-restricted boards only show up where everyone in the channel could already see them
        here_nsfw = getattr(getattr(ctx.channel, "parent", None) or ctx.channel, "nsfw", False)
        allowed = [
            board
            for board in boards
            if here_nsfw or not getattr(ctx.guild.get_channel(board.channel_id), "nsfw", False)
        ]
        post = await starboard_db.random_post([board.id for board in allowed]) if allowed else None
        if post is None:
            await ctx.respond(view=error_view("Nothing has made it onto the board yet."), ephemeral=True)
            return
        await ctx.defer()
        try:
            message = await actions.fetch(self.client, ctx.guild.id, post.channel_id, post.message_id)
        except discord.HTTPException:
            message = None
        if message is None:
            shown = cards.stored_tally(post).emoji
            link = cards.jump_url(ctx.guild.id, post.board.channel_id, post.post_id or 0)
            await ctx.respond(view=DesignerView(ui.Container(ui.TextDisplay(f"{shown} [See the post]({link})"))))
            return
        await ctx.respond(
            view=cards.post_card(
                post.board,
                message,
                cards.stored_tally(post),
                usable=cards.usable_emojis(self.client, ctx.channel, webhook=True),
                name=message.author.display_name,
            )
        )

    @starboard.command(name="stats")
    @option("user", description="Whose stats to show. Defaults to you.", default=None)
    async def stats(self, ctx: discord.ApplicationContext, user: discord.Member | None):
        """Shows how many stars someone got."""
        assert ctx.guild is not None
        if not (boards := await self._boards(ctx, None)):
            return
        guild, who = ctx.guild, user or ctx.author
        await ctx.defer()
        found, (avatar, icon) = await asyncio.gather(
            starboard_db.user_stats([board.id for board in boards], who.id),
            assets.fetch_many([who.display_avatar, guild.icon]),
        )
        data = starboard_card.StarboardCard(
            name=who.display_name,
            username=who.name,
            avatar=avatar,
            guild_name=guild.name,
            guild_icon=icon,
            rank=found["rank"] or None,
            received=found["received"],
            posts=found["posts"],
            best=found["best"],
        )
        file = await imaging.render(starboard_card.build, data, filename="starboard.png")
        alt = (
            f"{who.display_name}: {found['received']} stars received over {found['posts']} posts, "
            f"best post {found['best']}"
        )
        view = DesignerView(
            ui.Container(ui.MediaGallery(discord.MediaGalleryItem("attachment://starboard.png", description=alt)))
        )
        await ctx.respond(view=view, file=file)


def setup(client: Client):
    client.add_cog(Starboard(client))
