import datetime
import discord
import lavalink
import platform
import psutil
import time
from babel.dates import format_timedelta
from core import Client
from core.view import View
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from typing import Literal
from utils import check, config
from utils.emoji import emoji
from utils.helpers import fmt_memory

# Starting time of bot
start_time = time.time()


class Stats:
    def __init__(self, client: Client, ctx: discord.ApplicationContext):
        self.client = client
        self.ctx = ctx

    async def _format_memory(self, total, used, free):
        return f"`{fmt_memory(total)}` `({fmt_memory(used)} Used | {fmt_memory(free)} Free)`"

    async def get_bot_stats(self) -> list[discord.ui.Item]:
        dur = format_timedelta(datetime.timedelta(seconds=int(round(time.time() - start_time))))
        is_dev = await check.is_dev(self.ctx)

        stats = (
            f"{emoji.ping} **Bot's Latency**: `{round(self.client.latency * 1000)} ms`\n"
            f"{emoji.duration} **Bot's Uptime**: `{dur}`\n"
            f"{emoji.server} **Total Servers**: `{len(self.client.guilds)}`\n"
            f"{emoji.members} **Total Members**: `{len(set(self.client.get_all_members()))}`\n"
            f"{emoji.channel} **Total Channels**: `{len(set(self.client.get_all_channels()))}`"
        )

        if is_dev:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            stats += (
                f"\n{emoji.python} **Python Version**: `v{platform.python_version()}`\n"
                f"{emoji.pycord} **Pycord Version**: `v{discord.__version__}`\n"
                f"{emoji.memory} **Memory**: {await self._format_memory(mem.total, mem.used, mem.available)}\n"
                f"{emoji.storage} **Storage**: {await self._format_memory(disk.total, disk.used, disk.free)}\n"
                f"{emoji.cpu} **Total CPU Cores**: `{psutil.cpu_count()}`\n"
                f"{emoji.tasks} **CPU Load**: `{psutil.cpu_percent()}%`"
            )

        return [discord.ui.TextDisplay(f"## {self.client.user.name} Stats"), discord.ui.TextDisplay(stats)]

    async def get_lavalink_stats(self, node: lavalink.Node) -> list[discord.ui.Item]:
        dur = format_timedelta(datetime.timedelta(milliseconds=node.stats.uptime))
        is_dev = await check.is_dev(self.ctx)

        stats = (
            f"{emoji.ping} **Node Latency**: `{round(await node.get_rest_latency())} ms`\n"
            f"{emoji.duration} **Node Uptime**: `{dur}`\n"
            f"{emoji.music} **Players Connected**: `{node.stats.players}`\n"
            f"{emoji.play} **Currently Playing**: `{node.stats.playing_players}`"
        )

        if is_dev:
            stats += (
                f"\n{emoji.lavalink} **Lavalink Version**: `v{await node.get_version()}`\n"
                f"{emoji.memory} **Memory**: {await self._format_memory(node.stats.memory_allocated, node.stats.memory_used, node.stats.memory_free)}\n"
                f"{emoji.cpu} **Total CPU Cores**: `{node.stats.cpu_cores}`\n"
                f"{emoji.tasks} **CPU Load**: `{round(node.stats.system_load * 100)}% System | {round(node.stats.lavalink_load * 100)}% Lavalink`"
            )

        return [discord.ui.TextDisplay(f"## {self.client.user.name} Lavalink Stats"), discord.ui.TextDisplay(stats)]


class StatsView(View):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, manager: lavalink.NodeManager | None):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.ctx = ctx
        self.manager = manager
        self.stats = Stats(client, ctx)

    async def async_init(self):
        await self._build_bot_stats_view()

    async def _get_footer(self) -> discord.ui.Section:
        owner = await self.client.fetch_user(config.owner_id)
        return discord.ui.TextDisplay(f"-# Designed & Built by {owner.name}")

    def _get_button(self, button: Literal["Bot Stats", "Lavalink Stats"]):
        match button:
            case "Bot Stats":
                btn = discord.ui.Button(
                    emoji=emoji.lavalink_white, label="Lavalink Stats", style=discord.ButtonStyle.grey
                )
                btn.callback = self.lavalink_stats_callback
            case "Lavalink Stats":
                btn = discord.ui.Button(emoji=emoji.previous_white, label="Back", style=discord.ButtonStyle.gray)
                btn.callback = self.bot_stats_callback
        return btn

    async def _build_bot_stats_view(self):
        self.clear_items()
        items = await self.stats.get_bot_stats()
        container = discord.ui.Container(*items)
        container.add_item(await self._get_footer())
        self.add_item(container)
        self.add_item(self._get_button("Bot Stats"))

    async def _build_lavalink_stats_view(self):
        self.clear_items()
        node = lavalink.Node(
            host=config.lavalink["host"],
            port=config.lavalink["port"],
            password=config.lavalink["password"],
            region=config.lavalink["region"],
            ssl=config.lavalink["secure"],
            manager=self.manager,
        )
        items = await self.stats.get_lavalink_stats(node)
        container = discord.ui.Container(*items)
        container.add_item(await self._get_footer())
        self.add_item(container)
        self.add_item(self._get_button("Lavalink Stats"))

    async def lavalink_stats_callback(self, interaction: discord.Interaction):
        self.disable_all_items()
        await interaction.edit(view=self)
        await self._build_lavalink_stats_view()
        await interaction.edit(view=self)

    async def bot_stats_callback(self, interaction: discord.Interaction):
        self.disable_all_items()
        await interaction.edit(view=self)
        await self._build_bot_stats_view()
        await interaction.edit(view=self)


class Info(commands.Cog):
    def __init__(self, client: Client):
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
            manager=self.client.lavalink.node_manager if self.client.lavalink else None,
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
        # Prepare info fields
        info_lines = [
            f"{emoji.mention} {user.mention} {emoji.crown if user.guild.owner_id == user.id else ''}",
            f"{emoji.id} **ID**: `{user.id}`",
            f"{emoji.bot} **Bot?**: {user.bot}",
            f"{emoji.link} **Avatar URL**: [Click Here]({user.avatar.url})",
            f"{emoji.date} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}",
        ]

        if isinstance(user, discord.Member):
            info_lines.extend(
                [
                    f"{emoji.description} **Status**: {user.status}",
                    f"{emoji.user} **Nickname**: {user.nick}",
                    f"{emoji.role} **Highest Role**: {user.top_role.mention}",
                    f"{emoji.join} **Server Joined**: {discord.utils.format_dt(user.joined_at, 'R')}",
                ]
            )
            # Exclude @everyone
            other_roles = [role for role in user.roles if role != user.guild.default_role and role != user.top_role]
            roles_str = " ".join(role.mention for role in other_roles)
            if roles_str:
                info_lines.append(f"{emoji.role} **Other Roles (`{len(other_roles)}`)**: {roles_str}")
            perms = [f"`{perm.replace('_', ' ').title()}`" for perm, value in user.guild_permissions if value]
            if perms:
                info_lines.append(f"{emoji.perms} **Permissions**: {', '.join(perms)}")

        view = View(
            discord.ui.Container(
                discord.ui.Section(
                    discord.ui.TextDisplay(f"## {user.display_name}'s Info"),
                    discord.ui.TextDisplay("\n".join(info_lines)),
                    accessory=discord.ui.Thumbnail(user.avatar.url),
                ),
            )
        )
        await ctx.respond(view=view, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))

    # Server info
    @info.command(name="server")
    async def server_info(self, ctx: discord.ApplicationContext):
        """Shows info of the current server."""
        animated_emojis = len([e for e in ctx.guild.emojis if e.animated])
        static_emojis = len(ctx.guild.emojis) - animated_emojis

        bot_roles = len([role for role in ctx.guild.roles if role.is_bot_managed()])
        user_roles = len(ctx.guild.roles) - bot_roles

        view = View(
            discord.ui.Container(
                discord.ui.Section(
                    discord.ui.TextDisplay(f"## {ctx.guild.name}'s Info"),
                    discord.ui.TextDisplay(
                        f"{emoji.mention} **Name**: {ctx.guild.name}\n"
                        f"{emoji.id} **ID**: `{ctx.guild.id}`\n"
                        f"{emoji.owner} **Owner**: {ctx.guild.owner.mention}\n"
                        f"{emoji.verification} **Verification Level**: `{ctx.guild.verification_level}`\n"
                        f"{emoji.channel} **Total Channels**: `{len(ctx.guild.text_channels) + len(ctx.guild.voice_channels)}`"
                        f" `({len(ctx.guild.categories)} Categories | {len(ctx.guild.text_channels)} Text | {len(ctx.guild.voice_channels)} Voice | {len(ctx.guild.stage_channels)} Stage)`\n"
                        f"{emoji.members} **Total Members**: `{len(list(ctx.guild.members))}`"
                        f" `({len([m for m in ctx.guild.members if not m.bot])} Humans | {len([m for m in ctx.guild.members if m.bot])} Bots)`\n"
                        f"{emoji.role} **Roles**: `{len(ctx.guild.roles)}`"
                        f" `({user_roles} User | {bot_roles} Bot)`\n"
                        f"{emoji.emoji} **Emojis**: `{len(ctx.guild.emojis)}`"
                        f" `({animated_emojis} Animated | {static_emojis} Static)`\n"
                        f"{emoji.date} **Server Created**: {discord.utils.format_dt(ctx.guild.created_at, 'R')}"
                    ),
                    accessory=discord.ui.Thumbnail(ctx.guild.icon.url if ctx.guild.icon else ""),
                ),
            ),
        )
        if ctx.guild.icon:
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Icon URL", url=ctx.guild.icon.url))
        if ctx.guild.banner:
            view.add_item(
                discord.ui.Button(style=discord.ButtonStyle.link, label="Banner URL", url=ctx.guild.banner.url)
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


def setup(client: Client):
    client.add_cog(Info(client))
