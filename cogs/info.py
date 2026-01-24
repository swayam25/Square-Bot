import datetime
import discord
import lavalink
import platform
import psutil
import time
from babel.dates import format_timedelta
from core import Client
from core.view import DesignerView
from discord import ui
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

    def _format_memory(self, total, used, free):
        return f"`{fmt_memory(total)}` `({fmt_memory(used)} Used | {fmt_memory(free)} Free)`"

    async def get_bot_stats(self) -> list[ui.Item]:
        dur = format_timedelta(datetime.timedelta(seconds=int(time.time() - start_time)))
        is_dev = await check.is_dev(self.ctx)

        stats_parts = [
            f"{emoji.ping} **Bot's Latency**: `{round(self.client.latency * 1000)} ms`",
            f"{emoji.duration} **Bot's Uptime**: `{dur}`",
            f"{emoji.server} **Total Servers**: `{len(self.client.guilds)}`",
            f"{emoji.members} **Total Members**: `{sum(1 for _ in self.client.get_all_members())}`",
            f"{emoji.channel} **Total Channels**: `{sum(1 for _ in self.client.get_all_channels())}`",
        ]

        if is_dev:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            stats_parts.extend(
                [
                    f"{emoji.python} **Python Version**: `v{platform.python_version()}`",
                    f"{emoji.pycord} **Pycord Version**: `v{discord.__version__}`",
                    f"{emoji.memory} **Memory**: {self._format_memory(mem.total, mem.used, mem.available)}",
                    f"{emoji.storage} **Storage**: {self._format_memory(disk.total, disk.used, disk.free)}",
                    f"{emoji.cpu} **Total CPU Cores**: `{psutil.cpu_count()}`",
                    f"{emoji.tasks} **CPU Load**: `{psutil.cpu_percent()}%`",
                ]
            )

        return [ui.TextDisplay(f"## {self.client.user.name} Stats"), ui.TextDisplay("\n".join(stats_parts))]

    async def get_lavalink_stats(self, node: lavalink.Node) -> list[ui.Item]:
        dur = format_timedelta(datetime.timedelta(milliseconds=node.stats.uptime))
        is_dev = await check.is_dev(self.ctx)
        latency = round(await node.get_rest_latency())

        stats_parts = [
            f"{emoji.ping} **Node Latency**: `{latency} ms`",
            f"{emoji.duration} **Node Uptime**: `{dur}`",
            f"{emoji.music} **Players Connected**: `{node.stats.players}`",
            f"{emoji.play} **Currently Playing**: `{node.stats.playing_players}`",
        ]

        if is_dev:
            version = await node.get_version()
            stats_parts.extend(
                [
                    f"{emoji.lavalink} **Lavalink Version**: `v{version}`",
                    f"{emoji.memory} **Memory**: {self._format_memory(node.stats.memory_allocated, node.stats.memory_used, node.stats.memory_free)}",
                    f"{emoji.cpu} **Total CPU Cores**: `{node.stats.cpu_cores}`",
                    f"{emoji.tasks} **CPU Load**: `{round(node.stats.system_load * 100)}% System | {round(node.stats.lavalink_load * 100)}% Lavalink`",
                ]
            )

        return [ui.TextDisplay(f"## {self.client.user.name} Lavalink Stats"), ui.TextDisplay("\n".join(stats_parts))]


class StatsView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, manager: lavalink.NodeManager | None):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.ctx = ctx
        self.manager = manager
        self.stats = Stats(client, ctx)
        self._footer = None

    async def _get_footer(self) -> ui.Section:
        if self._footer is None:
            owner = await self.client.fetch_user(config.owner_id)
            self._footer = ui.TextDisplay(f"-# Designed & Built by {owner.global_name or owner.name}")
        return self._footer

    def _get_button(self, button: Literal["Bot Stats", "Lavalink Stats"]):
        if button == "Bot Stats":
            btn = ui.Button(
                emoji=emoji.lavalink_white,
                label="Lavalink Stats",
                style=discord.ButtonStyle.grey,
                custom_id="lavalink_btn",
            )
            btn.callback = lambda interaction: self._handle_callback(interaction, btn.id, "lavalink")
        else:
            btn = ui.Button(
                emoji=emoji.previous_white,
                label="Back",
                style=discord.ButtonStyle.gray,
                custom_id="bot_stats_btn",
            )
            btn.callback = lambda interaction: self._handle_callback(interaction, btn.id, "bot")
        return btn

    async def _build_view(self, view_type: Literal["bot", "lavalink"]):
        self.clear_items()
        if view_type == "bot":
            items = await self.stats.get_bot_stats()
            button = self._get_button("Bot Stats")
        else:
            items = await self.stats.get_lavalink_stats(self.client.lavalink.nodes[0])
            button = self._get_button("Lavalink Stats")

        container = ui.Container(*items)
        container.add_item(await self._get_footer())
        self.add_item(container)
        self.add_item(ui.ActionRow(button))

    async def _handle_callback(
        self, interaction: discord.Interaction, button_id: str, view_type: Literal["bot", "lavalink"]
    ):
        self.disable_all_items()
        self.get_item(button_id).emoji = emoji.loading_white
        await interaction.edit(view=self)
        await self._build_view(view_type)
        await interaction.edit(view=self)

    async def build(self):
        await self._build_view("bot")


class UserInfo:
    def __init__(self, client: Client, ctx: discord.ApplicationContext, user: discord.Member | discord.User):
        self.client = client
        self.ctx = ctx
        self.user = user

    async def get_user_info(self, type: Literal["main", "server"] = "server") -> tuple[list[str], list[ui.Button]]:
        """Get user info lines and URL buttons for main/server profile."""
        if isinstance(self.user, discord.User):
            self.user = await self.client.fetch_user(self.user.id)
        else:
            self.user = await self.ctx.guild.fetch_member(self.user.id)

        info_lines = [
            f"{emoji.mention} {self.user.mention} {(emoji.crown if self.user.guild.owner_id == self.user.id else '') if isinstance(self.user, discord.Member) else ''}",
            f"{emoji.id} **ID**: `{self.user.id}`",
            f"{emoji.bot} **Bot?**: {self.user.bot}",
            f"{emoji.date} **Account Created**: {discord.utils.format_dt(self.user.created_at, 'R')}",
        ]

        url_buttons = []
        if isinstance(self.user, discord.Member):
            info_lines.extend(
                [
                    f"{emoji.description} **Status**: {self.user.status.name.title()}",
                    f"{emoji.user} **Nickname**: {self.user.nick}",
                    f"{emoji.role} **Highest Role**: {self.user.top_role.mention}",
                    f"{emoji.join} **Server Joined**: {discord.utils.format_dt(self.user.joined_at, 'R')}",
                    f"{emoji.boost} **Boosting Since**: {discord.utils.format_dt(self.user.premium_since, 'R') if self.user.premium_since else 'Not Boosting'}",
                ]
            )
            # Exclude @everyone
            other_roles = [
                role for role in self.user.roles if role != self.user.guild.default_role and role != self.user.top_role
            ]
            roles_str = ", ".join(role.mention for role in other_roles)
            if roles_str:
                info_lines.append(f"{emoji.role} **Other Roles (`{len(other_roles)}`)**: {roles_str}")

            # Key permissions
            key_perms: list[str] = [
                "administrator",
                "manage_guild",
                "manage_roles",
                "manage_channels",
                "manage_webhooks",
                "manage_emojis_and_stickers",
                "manage_messages",
                "manage_nicknames",
                "kick_members",
                "ban_members",
                "mention_everyone",
                "mute_members",
                "deafen_members",
                "move_members",
                "priority_speaker",
                "view_audit_log",
                "view_guild_insights",
                "manage_events",
                "manage_threads",
                "manage_expressions",
                "moderate_members",
            ]
            perms_list = []
            for perm in key_perms:
                if getattr(self.user.guild_permissions, perm, False):
                    perms_list.append(f"`{perm.replace('_', ' ').title()}`")
            if perms_list:
                info_lines.append(f"{emoji.perms} **Key Permissions**: {', '.join(perms_list)}")
        else:
            url_buttons.append(
                ui.Button(
                    label="View Profile",
                    style=discord.ButtonStyle.link,
                    url=f"https://discord.com/users/{self.user.id}",
                )
            )

        if self.user.avatar or (isinstance(self.user, discord.Member) and self.user.guild_avatar):
            url_buttons.append(
                ui.Button(
                    label="Avatar URL",
                    style=discord.ButtonStyle.link,
                    url=self.user.guild_avatar.url
                    if (isinstance(self.user, discord.Member) and self.user.guild_avatar) and type == "server"
                    else self.user.avatar.url,
                )
            )

        if self.user.banner or (isinstance(self.user, discord.Member) and self.user.guild_banner):
            url_buttons.append(
                ui.Button(
                    label="Banner URL",
                    style=discord.ButtonStyle.link,
                    url=self.user.guild_banner.url
                    if (isinstance(self.user, discord.Member) and self.user.guild_banner) and type == "server"
                    else self.user.banner.url,
                )
            )

        return info_lines, url_buttons

    def get_thumbnail_url(self, type: Literal["main", "server"] = "server") -> str:
        """Get the thumbnail URL based on type."""
        if type == "server" and isinstance(self.user, discord.Member) and self.user.guild_avatar:
            return self.user.guild_avatar.url
        elif self.user.avatar:
            return self.user.avatar.url
        else:
            return self.user.default_avatar.url

    def get_banner_url(self, type: Literal["main", "server"] = "server") -> str | None:
        """Get the banner URL based on type."""
        if type == "server" and isinstance(self.user, discord.Member) and self.user.guild_banner:
            return self.user.guild_banner.url
        elif self.user.banner:
            return self.user.banner.url
        return None


class InfoView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, user: discord.Member | discord.User):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.ctx = ctx
        self.user = user
        self.user_info = UserInfo(client, ctx, user)
        self.permissions_page = 1
        self.items_per_page = 10

    async def build(self, type: Literal["main", "server", "permissions"] = "server"):
        """Build the info view for main, server profile, or permissions."""
        self.clear_items()

        if type == "permissions":
            await self._build_permissions_view()
            return

        info_lines, url_buttons = await self.user_info.get_user_info(type)
        row = ui.ActionRow()
        if isinstance(self.user_info.user, discord.Member) and (
            self.user_info.user.guild_avatar or self.user_info.user.guild_banner
        ):
            if type == "server":
                btn = ui.Button(
                    emoji=emoji.profile_white,
                    label="View Main Profile",
                    style=discord.ButtonStyle.grey,
                    custom_id="main_profile_btn",
                )
                btn.callback = lambda interaction: self._handle_callback(interaction, "main")
            else:
                btn = ui.Button(
                    emoji=emoji.profile_white,
                    label="View Server Profile",
                    style=discord.ButtonStyle.grey,
                    custom_id="back_btn",
                )
                btn.callback = lambda interaction: self._handle_callback(interaction, "server")
            row.add_item(btn)

        if isinstance(self.user_info.user, discord.Member) and (
            (self.user_info.user.id != self.ctx.guild.owner_id)
            and not self.user_info.user.guild_permissions.administrator
        ):
            perm_btn = ui.Button(
                emoji=emoji.perms_white,
                label="Show Permissions",
                style=discord.ButtonStyle.grey,
                custom_id="permissions_btn",
            )
            perm_btn.callback = lambda interaction: self._handle_callback(interaction, "permissions")
            row.add_item(perm_btn)

        cont = ui.Container(
            ui.Section(
                ui.TextDisplay(f"## {self.user_info.user.display_name}'s Info"),
                ui.TextDisplay("\n".join(info_lines)),
                accessory=ui.Thumbnail(self.user_info.get_thumbnail_url(type)),
            ),
        )

        banner_url = self.user_info.get_banner_url(type)
        if banner_url:
            cont.add_item(ui.MediaGallery(discord.MediaGalleryItem(url=banner_url)))

        if url_buttons:
            cont.add_item(ui.ActionRow(*list(url_buttons)))

        self.add_item(cont)
        if row.children:
            self.add_item(row)

    async def _build_permissions_view(self):
        """Build the permissions view with pagination."""
        if not isinstance(self.user_info.user, discord.Member):
            return

        member = self.user_info.user
        permissions = member.guild_permissions

        all_perms = []
        for perm_name, has_perm in permissions:
            if has_perm:
                perm_display = perm_name.replace("_", " ").title()
                roles_granting = []

                if getattr(member.guild.default_role.permissions, perm_name, False):
                    roles_granting.append(member.guild.default_role.mention)

                for role in member.roles:
                    if role == member.guild.default_role:
                        continue
                    if getattr(role.permissions, perm_name, False):
                        roles_granting.append(role.mention)

                all_perms.append((perm_display, roles_granting))

        total_pages = max(1, (len(all_perms) + self.items_per_page - 1) // self.items_per_page)
        start = (self.permissions_page - 1) * self.items_per_page
        end = start + self.items_per_page
        page_perms = all_perms[start:end]

        perm_text = "\n".join(
            f"`{i + start + 1}.` **{perm}**\n{emoji.bottom_right} {', '.join(roles)}"
            for i, (perm, roles) in enumerate(page_perms)
        )

        avatar_url = (
            member.guild_avatar.url
            if member.guild_avatar
            else (member.avatar.url if member.avatar else member.default_avatar.url)
        )

        cont = ui.Container(
            ui.Section(
                ui.TextDisplay(f"## {member.display_name}'s Permissions"),
                ui.TextDisplay(perm_text or "No permissions found."),
                accessory=ui.Thumbnail(avatar_url),
            ),
        )

        if len(all_perms) > self.items_per_page:
            cont.add_item(ui.Separator())
            cont.add_item(ui.TextDisplay(f"-# Viewing Page {self.permissions_page}/{total_pages}"))

        self.add_item(cont)

        row = ui.ActionRow()

        if len(all_perms) > self.items_per_page:
            left_buttons = []
            for btn_emoji, action in [
                (emoji.start_white, "start"),
                (emoji.previous_white, "previous"),
            ]:
                btn = ui.Button(emoji=btn_emoji, style=discord.ButtonStyle.grey)
                btn.callback = lambda i, a=action: self._handle_pagination(i, a, total_pages)
                left_buttons.append(btn)
            for btn in left_buttons:
                row.add_item(btn)

        profile_btn = ui.Button(
            emoji=emoji.profile_white,
            label="View Profile" if len(all_perms) < self.items_per_page else "",
            style=discord.ButtonStyle.grey,
            custom_id="profile_from_perms_btn",
        )
        profile_btn.callback = lambda interaction: self._handle_callback(interaction, "server")
        row.add_item(profile_btn)

        if len(all_perms) > self.items_per_page:
            right_buttons = []
            for btn_emoji, action in [
                (emoji.next_white, "next"),
                (emoji.end_white, "end"),
            ]:
                btn = ui.Button(emoji=btn_emoji, style=discord.ButtonStyle.grey)
                btn.callback = lambda i, a=action: self._handle_pagination(i, a, total_pages)
                right_buttons.append(btn)
            for btn in right_buttons:
                row.add_item(btn)

        self.add_item(row)

    async def _handle_pagination(self, interaction: discord.Interaction, action: str, total_pages: int):
        """Handle pagination for permissions view."""
        if action == "start":
            self.permissions_page = 1
        elif action == "previous":
            self.permissions_page = total_pages if self.permissions_page <= 1 else self.permissions_page - 1
        elif action == "next":
            self.permissions_page = 1 if self.permissions_page >= total_pages else self.permissions_page + 1
        elif action == "end":
            self.permissions_page = total_pages

        await self.build("permissions")
        await interaction.edit(view=self)

    async def _handle_callback(
        self, interaction: discord.Interaction, view_type: Literal["main", "server", "permissions"]
    ):
        """Handle navigation between main, server profile, and permissions."""
        if view_type != "permissions":
            self.permissions_page = 1
        await self.build(view_type)
        await interaction.edit(view=self)


class Info(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # Ping
    @slash_command(name="ping")
    async def ping(self, ctx: discord.ApplicationContext):
        """Shows heartbeats of the bot."""
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.ping} **Ping**: `{round(self.client.latency * 1000)} ms`"),
            )
        )
        await ctx.respond(view=view)

    # Uptime
    @slash_command(name="uptime")
    async def uptime(self, ctx: discord.ApplicationContext):
        """Shows bot's uptime."""
        dur = datetime.timedelta(seconds=int(round(time.time() - start_time)))
        dur = format_timedelta(dur)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.duration} **Bot's Uptime**: `{str(dur)}`"),
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
        await view.build()
        await ctx.respond(view=view)

    # Avatar
    @slash_command(name="avatar")
    @option("user", description="Mention the user whom you will see avatar", required=False)
    async def avatar(self, ctx: discord.ApplicationContext, user: discord.Member = None):
        """Shows the avatar of the mentioned user."""
        if not user:
            user = ctx.author

        async def profile_btn_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                view=await get_view("main" if interaction.data["custom_id"] == "server_profile_btn" else "server")
            )

        async def get_view(type: Literal["main", "server"] = "server"):
            avatar = (
                user.guild_avatar if user.guild_avatar and type == "server" else (user.avatar or user.default_avatar)
            )
            profile_btn = ui.Button(
                emoji=emoji.profile_white,
                label=f"View {'Main' if type == 'server' else 'Server'} Avatar",
                style=discord.ButtonStyle.grey,
                custom_id=f"{type}_profile_btn",
            )
            profile_btn.callback = profile_btn_callback
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"## {user.display_name}'s Avatar"),
                    ui.MediaGallery(discord.MediaGalleryItem(url=avatar.url)),
                    ui.ActionRow(
                        *[
                            ui.Button(
                                label=fmt.upper(),
                                style=discord.ButtonStyle.link,
                                url=avatar.with_format(fmt).url,
                            )
                            for fmt in ["png", "jpg", "webp"]
                        ]
                    ),
                ),
                ctx=ctx,
                check_author_interaction=True,
            )
            if user.guild_avatar:
                view.add_item(ui.ActionRow(profile_btn))
            return view

        view = await get_view()
        await ctx.respond(view=view)

    # Info slash cmd group
    info = SlashCommandGroup(name="info", description="Info related commands.")

    # User info
    @info.command(name="user")
    @option("user", description="Mention the member whom you will see info")
    async def user_info(self, ctx: discord.ApplicationContext, user: discord.Member | discord.User):
        """Shows info of the mentioned user."""
        await ctx.defer()
        view = InfoView(self.client, ctx, user)
        await view.build()
        await ctx.respond(view=view)

    # Server info
    @info.command(name="server")
    async def server_info(self, ctx: discord.ApplicationContext):
        """Shows info of the current server."""
        animated_emojis = len([e for e in ctx.guild.emojis if e.animated])
        static_emojis = len(ctx.guild.emojis) - animated_emojis

        bot_roles = len([role for role in ctx.guild.roles if role.is_bot_managed()])
        user_roles = len(ctx.guild.roles) - bot_roles

        row = ui.ActionRow()
        container = ui.Container(
            ui.Section(
                ui.TextDisplay(f"## {ctx.guild.name}'s Info"),
                ui.TextDisplay(
                    f"{emoji.mention} **Name**: {ctx.guild.name}\n"
                    f"{emoji.id} **ID**: `{ctx.guild.id}`\n"
                    f"{emoji.owner} **Owner**: {ctx.guild.owner.mention}\n"
                    f"{emoji.verification} **Verification Level**: {ctx.guild.verification_level.name.title()}\n"
                    f"{emoji.channel} **Total Channels**: `{len(ctx.guild.text_channels) + len(ctx.guild.voice_channels)}`"
                    f" `({len(ctx.guild.categories)} Categories | {len(ctx.guild.text_channels)} Text | {len(ctx.guild.voice_channels)} Voice | {len(ctx.guild.stage_channels)} Stage)`\n"
                    f"{emoji.members} **Total Members**: `{len(list(ctx.guild.members))}`"
                    f" `({len([m for m in ctx.guild.members if not m.bot])} Humans | {len([m for m in ctx.guild.members if m.bot])} Bots)`\n"
                    f"{emoji.role} **Roles**: `{len(ctx.guild.roles)}`"
                    f" `({user_roles} User | {bot_roles} Bot)`\n"
                    f"{emoji.boost} **Boosts**: `{ctx.guild.premium_subscription_count}`"
                    f" `(Level {ctx.guild.premium_tier})`\n"
                    f"{emoji.emoji} **Emojis**: `{len(ctx.guild.emojis)}`"
                    f" `({animated_emojis} Animated | {static_emojis} Static)`\n"
                    f"{emoji.date} **Server Created**: {discord.utils.format_dt(ctx.guild.created_at, 'R')}"
                ),
                accessory=ui.Thumbnail(ctx.guild.icon.url + "?" if ctx.guild.icon else ""),
            ),
        )

        if ctx.guild.banner:
            container.add_item(
                ui.MediaGallery(discord.MediaGalleryItem(url=ctx.guild.banner.url)),
            )
        view = DesignerView(container, row)

        if ctx.guild.icon:
            row.add_item(ui.Button(style=discord.ButtonStyle.link, label="Icon URL", url=ctx.guild.icon.url))
        if ctx.guild.banner:
            row.add_item(ui.Button(style=discord.ButtonStyle.link, label="Banner URL", url=ctx.guild.banner.url))
        await ctx.respond(view=view)

    # Emoji info
    @info.command(name="emoji")
    @option("icon", description="Enter the emoji")
    async def emoji_info(self, ctx: discord.ApplicationContext, icon: discord.Emoji):
        """Shows info of the given emoji."""
        try:
            _emoji = await ctx.guild.fetch_emoji(icon.id)
            view = DesignerView(
                ui.Container(
                    ui.Section(
                        ui.TextDisplay("## Emoji Info"),
                        ui.TextDisplay(
                            f"{emoji.mention} **Name**: `{_emoji.name}`\n"
                            f"{emoji.id} **ID**: `{_emoji.id}`\n"
                            f"{emoji.emoji} **Is Animated?**: {_emoji.animated}\n"
                            f"{emoji.bot} **Is Managed?**: {_emoji.managed}\n"
                            f"{emoji.keyboard} **Is Usuable?**: {_emoji.is_usable()}\n"
                            f"{emoji.description} **Usage**: `{icon}`\n"
                            f"{emoji.owner} **Uploaded By**: {_emoji.user.mention if _emoji.user else 'Unknown'}\n"
                            f"{emoji.date} **Emoji Created**: {discord.utils.format_dt(_emoji.created_at, 'R')}"
                        ),
                        accessory=ui.Thumbnail(_emoji.url),
                    ),
                ),
                ui.ActionRow(
                    ui.Button(label="URL", style=discord.ButtonStyle.link, url=_emoji.url),
                ),
            )
            await ctx.respond(view=view)
        except discord.errors.HTTPException:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Invalid emoji provided. Please provide a valid emoji."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)


def setup(client: Client):
    client.add_cog(Info(client))
