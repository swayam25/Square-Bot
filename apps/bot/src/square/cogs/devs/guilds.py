import discord
import math
from discord import ui
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from discord.ui import ActionRow
from square.core import Client
from square.core.view import DesignerView, error_view, success_view
from square.db.funcs.guild import add_guild, remove_guild
from square.utils import check, config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count, member_counts
from square.utils.server_log import cleanup_guild


class GuildContainer(ui.Container):
    def __init__(self, guilds, page=1, items_per_page=10):
        super().__init__()
        total_pages = max(1, math.ceil(len(guilds) / items_per_page))
        start = (page - 1) * items_per_page
        end = start + items_per_page
        page_guilds = guilds[start:end]
        guilds_list = "\n".join(f"`{i + 1}.` **{g.name}**: `{g.id}`" for i, g in enumerate(page_guilds, start=start))
        self.add_item(ui.TextDisplay("## Guild List"))
        self.add_item(ui.TextDisplay(guilds_list or "No guilds found."))
        if len(guilds) > items_per_page:
            self.add_item(ui.Separator())
            self.add_item(ui.TextDisplay(f"-# Page {page} / {total_pages}"))


class GuildListView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, page: int = 1):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.page = page
        self.items_per_page = 10
        self.build()

    def build(self) -> None:
        self.clear_items()
        guilds = self.client.guilds
        self.add_item(GuildContainer(guilds, page=self.page, items_per_page=self.items_per_page))
        row = ActionRow()
        for btn_emoji, callback in [
            (emoji.start_white, "start"),
            (emoji.previous_white, "previous"),
            (emoji.next_white, "next"),
            (emoji.end_white, "end"),
        ]:
            btn = ui.Button(emoji=btn_emoji, style=discord.ButtonStyle.grey)
            btn.callback = lambda i, action=callback: self.interaction_callback(i, action)
            row.add_item(btn)
        self.add_item(row)

    async def interaction_callback(self, interaction: discord.Interaction, action: str):
        guilds = self.client.guilds
        total_pages = math.ceil(len(guilds) / self.items_per_page)
        if action == "start":
            self.page = 1
        elif action == "previous":
            self.page = total_pages if self.page <= 1 else self.page - 1
        elif action == "next":
            self.page = 1 if self.page >= total_pages else self.page + 1
        elif action == "end":
            self.page = total_pages
        self.build()
        await interaction.edit(view=self)


class Guilds:
    """Guild join and leave reports, and the `/guild` command group."""

    client: Client

    # On guild joined
    @commands.Cog.listener("on_guild_join")
    async def when_guild_joined(self, guild: discord.Guild):
        total, humans, bots = member_counts(guild)
        await add_guild(guild.id)
        join_log_ch = self.client.get_channel(config.system_channel_id) or await self.client.fetch_channel(
            config.system_channel_id
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Someone Added Me!"),
                ui.TextDisplay(
                    f"{emoji.server} **Name**: {guild.name}\n"
                    f"{emoji.id} **ID**: `{guild.id}`\n"
                    f"{emoji.members} **Total Members**: `{fmt_count(total)} ({fmt_count(humans)} Humans | {fmt_count(bots)} Bots)`"
                ),
            )
        )
        await join_log_ch.send(view=view)

    # On guild leave
    @commands.Cog.listener("on_guild_remove")
    async def when_removed_from_guild(self, guild: discord.Guild):
        total, humans, bots = member_counts(guild)
        await remove_guild(guild.id)
        await cleanup_guild(guild.id, {c.id for c in guild.channels})
        leave_log_ch = self.client.get_channel(config.system_channel_id) or await self.client.fetch_channel(
            config.system_channel_id
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Someone Removed Me!"),
                ui.TextDisplay(
                    f"{emoji.server_red} **Name**: {guild.name}\n"
                    f"{emoji.id_red} **ID**: `{guild.id}`\n"
                    f"{emoji.members_red} **Total Members**: `{fmt_count(total)} ({fmt_count(humans)} Humans | {fmt_count(bots)} Bots)`"
                ),
                color=config.color.red,
            )
        )
        await leave_log_ch.send(view=view)

    # Guild slash cmd group
    guild = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="guild", description="Guild related commands.")

    # List guild
    @guild.command(name="list")
    @check.is_owner()
    async def list_guilds(self, ctx: discord.ApplicationContext):
        """Shows all guilds."""
        guild_list_view = None
        if len(self.client.guilds) > 10:
            guild_list_view = GuildListView(self.client, ctx)
        else:
            guilds = self.client.guilds
            container = GuildContainer(guilds)
            guild_list_view = DesignerView(container)
        await ctx.respond(view=guild_list_view)

    # Leave guild
    @guild.command(name="leave")
    @check.is_owner()
    @option(
        "guild",
        description="Enter the guild name",
        autocomplete=lambda self, ctx: [
            guild.name for guild in self.client.guilds if not any(guild.id == g for g in config.owner_guild_ids)
        ],
    )
    async def leave_guild(self, ctx: discord.ApplicationContext, guild: discord.Guild):
        """Leaves a guild."""
        if any(guild.id == g for g in config.owner_guild_ids):
            view = error_view("I can't leave the owner guild.")
            await ctx.respond(view=view, ephemeral=True)
        else:
            await guild.leave()
            view = success_view(f"Left the guild **{guild.name}** with ID `{guild.id}`")
            await ctx.respond(view=view)

    # Guild invite
    @guild.command(name="invite")
    @check.is_owner()
    @option(
        "guild",
        description="Enter the guild name",
        autocomplete=lambda self, ctx: [
            guild.name for guild in self.client.guilds if not any(guild.id == g for g in config.owner_guild_ids)
        ],
    )
    async def guild_inv(self, ctx: discord.ApplicationContext, guild: discord.Guild):
        """Creates an invite link for the guild."""
        if any(guild.id == g for g in config.owner_guild_ids):
            view = error_view("I can't create an invite link for the owner guild")
            await ctx.respond(view=view, ephemeral=True)
        else:
            invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=0)
            await ctx.respond(invite.url)
