import datetime
import discord
import lavalink
import platform
import psutil
import time
from babel.dates import format_timedelta
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from utils import check, config
from utils.emoji import emoji
from utils.helpers import fmt_memory

# Starting time of bot
start_time = time.time()


class BotStats:
    def __init__(self, client: discord.Bot, ctx: discord.ApplicationContext):
        self.client = client
        self.ctx = ctx

    async def get_embed(self) -> discord.Embed:
        owner = await self.client.fetch_user(config.owner_id)
        dur = datetime.timedelta(seconds=int(round(time.time() - start_time)))
        dur = format_timedelta(dur)
        is_dev: bool = await check.is_dev(self.ctx)
        if is_dev:
            mem = psutil.virtual_memory()
            cpu_cores = psutil.cpu_count()
            cpu_load = psutil.cpu_percent()
            disk = psutil.disk_usage("/")
        em = discord.Embed(
            title=f"{self.client.user.name} Stats",
            description=(
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
            color=config.color.theme,
        )
        em.set_footer(text=f"Designed & Built by {owner}", icon_url=f"{owner.avatar.url}")
        return em


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

    async def get_stats_embed(self) -> discord.Embed:
        owner = await self.client.fetch_user(config.owner_id)
        dur = datetime.timedelta(milliseconds=self.stats.uptime)
        dur = format_timedelta(dur)
        em = discord.Embed(
            title=f"{self.client.user.name} Lavalink Stats",
            description=(
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
                    if (await check.is_dev(self.ctx))
                    else ""
                )
            ),
            color=config.color.theme,
        )
        em.set_footer(text=f"Designed & Built by {owner}", icon_url=f"{owner.avatar.url}")
        return em


class StatsView(discord.ui.View):
    def __init__(
        self, client: discord.Bot, ctx: discord.ApplicationContext, manager: lavalink.NodeManager | None, timeout: int
    ):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client
        self.ctx = ctx
        self.manager = manager
        self.interaction_check = lambda i: check.author_interaction_check(ctx, i)
        self.add_item(
            discord.ui.Button(
                emoji=emoji.lavalink_white,
                label="Show Lavalink Stats" if manager else "Lavalink Node Not Connected",
                style=discord.ButtonStyle.gray,
                disabled=not manager,
            )
        )
        self.children[0].callback = self.lavalink_stats_callback

    async def lavalink_stats_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        stats_em = await LavaNode(self.client, self.ctx, self.client.lavalink.node_manager).get_stats_embed()
        self.children[0].emoji = emoji.previous_white
        self.children[0].label = "Back"
        self.children[0].callback = self.back_callback
        await interaction.edit(embed=stats_em, view=self)

    async def back_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        stats_em = await BotStats(self.client, self.ctx).get_embed()
        self.children[0].emoji = emoji.lavalink_white
        self.children[0].label = "Show Lavalink Stats" if self.manager else "Lavalink Not Connected"
        self.children[0].callback = self.lavalink_stats_callback
        await interaction.edit(embed=stats_em, view=self)


class Info(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client = client

    # Ping
    @slash_command(name="ping")
    async def ping(self, ctx: discord.ApplicationContext):
        """Shows heartbeats of the bot."""
        ping_em = discord.Embed(
            description=f"{emoji.ping} **Ping**: `{round(self.client.latency * 1000)} ms`",
            color=config.color.theme,
        )
        await ctx.respond(embed=ping_em)

    # Uptime
    @slash_command(name="uptime")
    async def uptime(self, ctx: discord.ApplicationContext):
        """Shows bot's uptime."""
        dur = datetime.timedelta(seconds=int(round(time.time() - start_time)))
        dur = format_timedelta(dur)
        uptime_em = discord.Embed(
            description=f"{emoji.duration} **Bot's Uptime**: `{str(dur)}`",
            color=config.color.theme,
        )
        await ctx.respond(embed=uptime_em)

    # Stats
    @slash_command(name="stats")
    async def stats(self, ctx: discord.ApplicationContext):
        """Shows bot stats."""
        await ctx.defer()
        stats_em = await BotStats(self.client, ctx).get_embed()
        view = StatsView(
            client=self.client,
            ctx=ctx,
            manager=self.client.lavalink.node_manager if isinstance(self.client.lavalink, lavalink.Client) else None,
            timeout=60,
        )
        await ctx.respond(embed=stats_em, view=view)

    # Avatar
    @slash_command(name="avatar")
    @option("user", description="Mention the user whom you will see avatar")
    async def avatar(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Shows the avatar of the mentioned user."""
        avatar_em = discord.Embed(title=f"{user.name}'s Avatar", color=config.color.theme)
        avatar_em.set_image(url=f"{user.avatar.url}")
        await ctx.respond(
            embed=avatar_em,
            view=discord.ui.View(
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
            ),
        )

    # Info slash cmd group
    info = SlashCommandGroup(name="info", description="Info related commands.")

    # User info
    @info.command(name="user")
    @option("user", description="Mention the member whom you will see info")
    async def user_info(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Shows info of the mentioned user."""
        user_info_em = discord.Embed(
            title=f"{user.name}'s Info",
            description=(
                f"{emoji.mention} {user.mention}\n"
                f"{emoji.id} **ID**: `{user.id}`\n"
                f"{emoji.bot} **Bot?**: {user.bot}\n"
                f"{emoji.link} **Avatar URL**: [Click Here]({user.avatar.url})\n"
                f"{emoji.description} **Status**: {user.status}\n"
                f"{emoji.user} **Nickname**: {user.nick}\n"
                f"{emoji.role} **Highest Role**: {user.top_role.mention}\n"
                f"{emoji.date} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}\n"
                f"{emoji.join} **Server Joined**: {discord.utils.format_dt(user.joined_at, 'R')}"
            ),
            color=config.color.theme,
        )
        user_info_em.set_thumbnail(url=f"{user.avatar.url}")
        await ctx.respond(embed=user_info_em)

    # Server info
    @info.command(name="server")
    async def server_info(self, ctx: discord.ApplicationContext):
        """Shows info of the current server."""
        server_info_em = discord.Embed(
            title=f"{ctx.guild.name}'s Info",
            description=(
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
            color=config.color.theme,
        )
        server_info_em.set_thumbnail(url=ctx.guild.icon if ctx.guild.icon else "")
        await ctx.respond(embed=server_info_em)

    # Emoji info
    @info.command(name="emoji")
    @option("icon", description="Enter the emoji")
    async def emoji_info(self, ctx: discord.ApplicationContext, icon: discord.Emoji):
        """Shows info of the given emoji."""
        emoji_info_em = discord.Embed(
            title="Emoji Info",
            description=(
                f"{emoji.mention} **Name**: {icon.name}\n"
                f"{emoji.id} **ID**: `{icon.id}`\n"
                f"{emoji.emoji} **Is Animated?**: {icon.animated}\n"
                f"{emoji.description} **Usage**: `{icon}`\n"
                f"{emoji.owner} **Uploaded By**: {icon.user.mention if icon.user else 'Unknown'}\n"
                f"{emoji.date} **Emoji Created**: {discord.utils.format_dt(icon.created_at, 'R')}"
            ),
            color=config.color.theme,
        )
        emoji_info_em.set_thumbnail(url=f"{icon.url}")
        await ctx.respond(
            embed=emoji_info_em,
            view=discord.ui.View(discord.ui.Button(label="URL", style=discord.ButtonStyle.link, url=icon.url)),
        )

    @emoji_info.error
    async def on_error(self, ctx: discord.ApplicationContext, error: discord.DiscordException):
        if isinstance(error, commands.errors.EmojiNotFound):
            em = discord.Embed(
                description=f"{emoji.error} Invalid emoji provided. Please provide a valid emoji.",
                color=config.color.red,
            )
            await ctx.respond(embed=em, ephemeral=True)


def setup(client: discord.Bot):
    client.add_cog(Info(client))
