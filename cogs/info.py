import datetime
import discord
import lavalink
import platform
import psutil
import time
from babel.dates import format_timedelta
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from typing import Literal
from utils import check, config
from utils.emoji import emoji
from utils.helpers import fmt_memory
from utils.view import View

# Starting time of bot
start_time = time.time()


class Stats:
    class BotStats:
        def __init__(self, client: discord.Bot, ctx: discord.ApplicationContext):
            self.client = client
            self.ctx = ctx

        async def get(self) -> list[discord.ui.Item]:
            dur = datetime.timedelta(seconds=int(round(time.time() - start_time)))
            dur = format_timedelta(dur)
            is_dev: bool = await check.is_dev(self.ctx)
            if is_dev:
                mem = psutil.virtual_memory()
                cpu_cores = psutil.cpu_count()
                cpu_load = psutil.cpu_percent()
                disk = psutil.disk_usage("/")
            return [
                discord.ui.TextDisplay(f"## {self.client.user.name} Stats"),
                discord.ui.TextDisplay(
                    f"{emoji.ping} **Bot's Latency**: `{round(self.client.latency * 1000)} ms`\n"
                    f"{emoji.duration} **Bot's Uptime**: `{str(dur)}`\n"
                    f"{emoji.server} **Total Servers**: `{str(len(self.client.guilds))}`\n"
                    f"{emoji.members} **Total Members**: `{len(set(self.client.get_all_members()))}`\n"
                    f"{emoji.channel} **Total Channels**: `{len(set(self.client.get_all_channels()))}`"
                    + (
                        f"\n{emoji.python} **Python Version**: `v{platform.python_version()}`\n"
                        f"{emoji.pycord} **Pycord Version**: `v{discord.__version__}`\n"
                        f"{emoji.memory} **Memory**: `{fmt_memory(mem.total)}`"
                        f" `({fmt_memory(mem.used)} Used | {fmt_memory(mem.available)} Free)`\n"
                        f"{emoji.storage} **Storage**: `{fmt_memory(disk.total)}`"
                        f" `({fmt_memory(disk.used)} Used | {fmt_memory(disk.free)} Free)`\n"
                        f"{emoji.cpu} **Total CPU Cores**: `{cpu_cores}`\n"
                        f"{emoji.tasks} **CPU Load**: `{cpu_load}%`"
                        if is_dev
                        else ""
                    )
                ),
            ]

    class LavaNode(lavalink.Node):
        def __init__(self, client: discord.Bot, ctx: discord.ApplicationContext, manager: lavalink.NodeManager):
            super().__init__(
                host=config.lavalink["host"],
                port=config.lavalink["port"],
                password=config.lavalink["password"],
                region=config.lavalink["region"],
                ssl=config.lavalink["secure"],
                manager=manager,
            )
            self.client = client
            self.ctx = ctx

        async def get(self) -> list[discord.ui.Item]:
            dur = datetime.timedelta(milliseconds=self.stats.uptime)
            dur = format_timedelta(dur)
            is_dev: bool = await check.is_dev(self.ctx)
            return [
                discord.ui.TextDisplay(f"## {self.client.user.name} Lavalink Stats"),
                discord.ui.TextDisplay(
                    f"{emoji.ping} **Node Latency**: `{round(await self.get_rest_latency())} ms`\n"
                    f"{emoji.duration} **Node Uptime**: `{str(dur)}`\n"
                    f"{emoji.music} **Players Connected**: `{self.stats.players}`\n"
                    f"{emoji.play} **Currently Playing**: `{self.stats.playing_players}`"
                    + (
                        f"\n{emoji.lavalink} **Lavalink Version**: `v{await self.get_version()}`\n"
                        f"{emoji.memory} **Memory**: `{fmt_memory(self.stats.memory_allocated)}`"
                        f" `({fmt_memory(self.stats.memory_used)} Used | {fmt_memory(self.stats.memory_free)} Free)`\n"
                        f"{emoji.cpu} **Total CPU Cores**: `{self.stats.cpu_cores}`\n"
                        f"{emoji.tasks} **CPU Load**: `{round(self.stats.system_load * 100)}% System | {round(self.stats.lavalink_load * 100)}% Lavalink `"
                        if is_dev
                        else ""
                    )
                ),
            ]


class StatsView(View):
    def __init__(
        self,
        client: discord.Bot,
        ctx: discord.ApplicationContext,
        manager: lavalink.NodeManager | None,
    ):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.ctx = ctx
        self.manager = manager

    async def async_init(self):
        await self._build_bot_stats_view()

    async def _get_footer(self) -> discord.ui.Section:
        owner = await self.client.fetch_user(config.owner_id)
        return discord.ui.TextDisplay(f"-# Designed & Built by {owner.name}")

    def _get_buttons(self, button: Literal["Bot Stats", "Lavalink Stats"]):
        bot_btn = discord.ui.Button(
            emoji=emoji.bot_white,
            label="Bot Stats",
            style=discord.ButtonStyle.blurple if button == "Bot Stats" else discord.ButtonStyle.gray,
            disabled=bool(button == "Bot Stats"),
        )
        bot_btn.callback = self.bot_stats_callback
        lava_btn = discord.ui.Button(
            emoji=emoji.lavalink_white,
            label="Lavalink Stats",
            style=discord.ButtonStyle.blurple if button == "Lavalink Stats" else discord.ButtonStyle.grey,
            disabled=not self.manager or bool(button == "Lavalink Stats"),
        )
        lava_btn.callback = self.lavalink_stats_callback
        return [bot_btn, lava_btn]

    async def _build_bot_stats_view(self):
        self.clear_items()
        items = await Stats.BotStats(self.client, self.ctx).get()
        btns = self._get_buttons("Bot Stats")
        container = discord.ui.Container(*items)
        container.add_item(await self._get_footer())
        self.add_item(container)
        for btn in btns:
            self.add_item(btn)

    async def _build_lavalink_stats_view(self):
        self.clear_items()
        items = await Stats.LavaNode(self.client, self.ctx, self.manager).get()
        btns = self._get_buttons("Lavalink Stats")
        container = discord.ui.Container(*items)
        container.add_item(await self._get_footer())
        self.add_item(container)
        for btn in btns:
            self.add_item(btn)

    async def lavalink_stats_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._build_lavalink_stats_view()
        await interaction.edit(view=self)

    async def bot_stats_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._build_bot_stats_view()
        await interaction.edit(view=self)


class Info(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client = client

    # Ping
    @slash_command(name="ping")
    async def ping(self, ctx: discord.ApplicationContext):
        """Shows heartbeats of the bot."""
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.ping} **Ping**: `{round(self.client.latency * 1000)} ms`"),
            )
        )
        await ctx.respond(view=view)

    # Uptime
    @slash_command(name="uptime")
    async def uptime(self, ctx: discord.ApplicationContext):
        """Shows bot's uptime."""
        dur = datetime.timedelta(seconds=int(round(time.time() - start_time)))
        dur = format_timedelta(dur)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.duration} **Bot's Uptime**: `{str(dur)}`"),
            )
        )
        await ctx.respond(view=view)

    # Stats
    @slash_command(name="stats")
    async def stats(self, ctx: discord.ApplicationContext):
        """Shows bot stats."""
        await ctx.defer()
        view = StatsView(
            client=self.client,
            ctx=ctx,
            manager=self.client.lavalink.node_manager if isinstance(self.client.lavalink, lavalink.Client) else None,
        )
        await view.async_init()
        await ctx.respond(view=view)

    # Avatar
    @slash_command(name="avatar")
    @option("user", description="Mention the user whom you will see avatar", required=False)
    async def avatar(self, ctx: discord.ApplicationContext, user: discord.Member = None):
        """Shows the avatar of the mentioned user."""
        if not user:
            user = ctx.author
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"## {user.display_name}'s Avatar"),
                discord.ui.MediaGallery(discord.MediaGalleryItem(url=user.avatar.url)),
            ),
            discord.ui.Button(
                label="PNG",
                style=discord.ButtonStyle.link,
                url=user.avatar.url
                if user.avatar.with_format("png").url
                else "https://cdn.discordapp.com/embed/avatars/0.png",
            ),
            discord.ui.Button(
                label="JPG",
                style=discord.ButtonStyle.link,
                url=user.avatar.with_format("jpg").url
                if user.avatar
                else "https://cdn.discordapp.com/embed/avatars/0.png",
            ),
            discord.ui.Button(
                label="WEBP",
                style=discord.ButtonStyle.link,
                url=user.avatar.with_format("webp").url
                if user.avatar
                else "https://cdn.discordapp.com/embed/avatars/0.png",
            ),
        )
        await ctx.respond(view=view)

    # Info slash cmd group
    info = SlashCommandGroup(name="info", description="Info related commands.")

    # User info
    @info.command(name="user")
    @option("user", description="Mention the member whom you will see info")
    async def user_info(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Shows info of the mentioned user."""
        view = View(
            discord.ui.Container(
                discord.ui.Section(
                    discord.ui.TextDisplay(f"## {user.display_name}'s Info"),
                    discord.ui.TextDisplay(
                        f"{emoji.mention} {user.mention}\n"
                        f"{emoji.id} **ID**: `{user.id}`\n"
                        f"{emoji.bot} **Bot?**: {user.bot}\n"
                        f"{emoji.link} **Avatar URL**: [Click Here]({user.avatar.url})\n"
                        + (
                            f"{emoji.description} **Status**: {user.status}\n"
                            f"{emoji.user} **Nickname**: {user.nick}\n"
                            f"{emoji.role} **Highest Role**: {user.top_role.mention}\n"
                            if isinstance(user, discord.Member) and user.nick and user.top_role
                            else ""
                        )
                        + (f"{emoji.date} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}\n")
                        + (
                            f"{emoji.join} **Server Joined**: {discord.utils.format_dt(user.joined_at, 'R')}"
                            if isinstance(user, discord.Member) and user.joined_at
                            else ""
                        )
                    ),
                    accessory=discord.ui.Thumbnail(user.avatar.url),
                ),
            )
        )
        await ctx.respond(view=view, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))

    # Server info
    @info.command(name="server")
    async def server_info(self, ctx: discord.ApplicationContext):
        """Shows info of the current server."""
        view = View(
            discord.ui.Container(
                discord.ui.Section(
                    discord.ui.TextDisplay(f"## {ctx.guild.name}'s Info"),
                    discord.ui.TextDisplay(
                        f"{emoji.mention} **Name**: {ctx.guild.name}\n"
                        f"{emoji.id} **ID**: `{ctx.guild.id}`\n"
                        f"{emoji.link} **Icon URL**: {f'[Click Here]({ctx.guild.icon})' if ctx.guild.icon else 'None'}\n"
                        f"{emoji.owner} **Owner**: {ctx.guild.owner.mention}\n"
                        f"{emoji.verification} **Verification Level**: `{ctx.guild.verification_level}`\n"
                        f"{emoji.channel} **Total Channels**: `{len(ctx.guild.text_channels) + len(ctx.guild.voice_channels)}`"
                        f" `({len(ctx.guild.categories)} Categories | {len(ctx.guild.text_channels)} Text | {len(ctx.guild.voice_channels)} Voice | {len(ctx.guild.stage_channels)} Stage)`\n"
                        f"{emoji.members} **Total Members**: `{len(list(ctx.guild.members))}`"
                        f" `({len([m for m in ctx.guild.members if not m.bot])} Humans | {len([m for m in ctx.guild.members if m.bot])} Bots)`\n"
                        f"{emoji.role} **Roles**: `{len(ctx.guild.roles)}`\n"
                        f"{emoji.date} **Server Created**: {discord.utils.format_dt(ctx.guild.created_at, 'R')}"
                    ),
                    accessory=discord.ui.Thumbnail(ctx.guild.icon.url if ctx.guild.icon else ""),
                ),
            )
        )
        await ctx.respond(view=view, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))

    # Emoji info
    @info.command(name="emoji")
    @option("icon", description="Enter the emoji")
    async def emoji_info(self, ctx: discord.ApplicationContext, icon: discord.Emoji):
        """Shows info of the given emoji."""
        try:
            _emoji = await ctx.guild.fetch_emoji(icon.id)
            view = View(
                discord.ui.Container(
                    discord.ui.Section(
                        discord.ui.TextDisplay("## Emoji Info"),
                        discord.ui.TextDisplay(
                            f"{emoji.mention} **Name**: `{_emoji.name}`\n"
                            f"{emoji.id} **ID**: `{_emoji.id}`\n"
                            f"{emoji.emoji} **Is Animated?**: {_emoji.animated}\n"
                            f"{emoji.bot} **Is Managed?**: {_emoji.managed}\n"
                            f"{emoji.keyboard} **Is Usuable?**: {_emoji.is_usable()}\n"
                            f"{emoji.description} **Usage**: `{icon}`\n"
                            f"{emoji.owner} **Uploaded By**: {_emoji.user.mention if _emoji.user else 'Unknown'}\n"
                            f"{emoji.date} **Emoji Created**: {discord.utils.format_dt(_emoji.created_at, 'R')}"
                        ),
                        accessory=discord.ui.Thumbnail(_emoji.url),
                    ),
                ),
                discord.ui.Button(label="URL", style=discord.ButtonStyle.link, url=_emoji.url),
            )
            await ctx.respond(
                view=view, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
            )
        except discord.errors.HTTPException:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} Invalid emoji provided. Please provide a valid emoji."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)


def setup(client: discord.Bot):
    client.add_cog(Info(client))
