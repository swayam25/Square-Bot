import discord
from core import Client
from core.view import DesignerView
from db.funcs.guild import (
    fetch_guild_settings,
    remove_guild,
    set_autorole,
    set_media_only,
    set_ticket_cmds,
)
from db.funcs.logs import fetch_log_channels, remove_log_channel, set_all_log_channels, set_log_channel
from discord import ui
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from utils import config
from utils.emoji import emoji
from utils.logger import LogType


class SettingsCommand:
    def __init__(self, ctx: discord.ApplicationCommand):
        self.ctx = ctx

    async def show(self):
        # Fetch channel mention util func
        def mention_ch(channel_id: int | None) -> str:
            return f"<#{channel_id}>" if channel_id else emoji.off

        guild_settings = await fetch_guild_settings(self.ctx.guild.id)
        log_channels = await fetch_log_channels(self.ctx.guild.id)

        ticket = emoji.on if guild_settings.ticket_cmds else emoji.off
        media_only_channel = mention_ch(guild_settings.media_only_channel_id)
        role_id = guild_settings.autorole
        autorole = (
            self.ctx.guild.get_role(role_id).mention if (role_id and self.ctx.guild.get_role(role_id)) else emoji.off
        )
        if role_id and not self.ctx.guild.get_role(role_id):
            await set_autorole(self.ctx.guild.id, None)  # Reset autorole if role doesn't exist

        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"## {self.ctx.guild.name}'s Settings"),
                ui.TextDisplay(
                    f"### General\n"
                    f"{emoji.ticket} **Ticket Commands**: {ticket}\n"
                    f"{emoji.img} **Media Only Channel**: {media_only_channel}\n"
                    f"{emoji.role} **Autorole**: {autorole}"
                ),
                ui.TextDisplay("### Logs"),
                ui.TextDisplay(
                    "\n".join(
                        f"{emoji.bullet} **{log_type.label}**: {mention_ch(log_channels.get(log_type.key))}"
                        for log_type in LogType
                    )
                ),
            )
        )
        await self.ctx.respond(view=view)

    async def reset(self, setting: str):
        """Resets server settings."""
        match setting.lower():
            case "all":
                await remove_guild(self.ctx.guild.id)
            case "all logs":
                await remove_log_channel(self.ctx.guild.id)
            case "ticket commands":
                await set_ticket_cmds(self.ctx.guild.id, False)
            case "media only":
                await set_media_only(self.ctx.guild.id, None)
            case "auto role":
                await set_autorole(self.ctx.guild.id, None)
            case _:
                await remove_log_channel(self.ctx.guild.id, LogType.from_label(setting).key)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Successfully reset {setting.lower()} settings."),
                color=config.color.green,
            )
        )
        await self.ctx.respond(view=view)


class Settings(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # Settings
    @slash_command(name="settings")
    @discord.default_permissions(manage_channels=True)
    @option(
        "reset",
        description="Setting to reset",
        choices=["All", "All Logs", "Ticket Commands", "Media Only", "Auto Role"]
        + [log_type.label for log_type in LogType],
        required=False,
    )
    async def settings(self, ctx: discord.ApplicationContext, reset: str):
        """Shows server settings."""
        settings = SettingsCommand(ctx)
        if reset:
            await settings.reset(reset)
        else:
            await settings.show()

    # Settings slash cmd group
    setting = SlashCommandGroup(
        name="set",
        description="Server settings commands.",
        default_member_permissions=discord.Permissions(manage_channels=True, moderate_members=True),
    )

    # Set log channel
    @setting.command(name="log")
    @option(
        "type",
        description="Log type to set",
        choices=["All Logs"] + [log_type.label for log_type in LogType],
    )
    @option("channel", description="Mention the log channel")
    async def set_log(self, ctx: discord.ApplicationContext, type: str, channel: discord.TextChannel):
        """Sets a log channel for the given log type."""
        if type == "All Logs":
            await set_all_log_channels(ctx.guild.id, [log_type.key for log_type in LogType], channel.id)
        else:
            await set_log_channel(ctx.guild.id, LogType.from_label(type).key, channel.id)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Successfully set {type.lower()} channel to {channel.mention}."),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Set ticket cmds
    @setting.command(name="ticket-commands")
    @option("status", description="Enable or disable ticket commands", choices=["Enable", "Disable"])
    async def set_ticket_cmds(self, ctx: discord.ApplicationContext, status: str):
        """Enables or disables ticket commands."""
        match status.lower():
            case "enable":
                await set_ticket_cmds(ctx.guild.id, True)
            case "disable":
                await set_ticket_cmds(ctx.guild.id, False)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Successfully {status.lower()}d ticket commands."),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Set media only channel
    @setting.command(name="media-only")
    @option("channel", description="Mention the media only channel")
    async def set_image_only(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets media only channel."""
        if not channel.permissions_for(ctx.guild.me).send_messages:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I don't have permission to send messages in {channel.mention}."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await set_media_only(ctx.guild.id, channel.id)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully set media only channel to {channel.mention}."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Set autorole
    @setting.command(name="auto-role")
    @option("role", description="Mention the autorole")
    async def set_auto_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Sets autorole. The bot will assign this role to new members."""
        if role >= ctx.guild.me.top_role:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I can't assign roles higher than my top role."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif role.name == "@everyone":
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I can't assign the @everyone role."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await set_autorole(ctx.guild.id, role.id)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(
                        f"{emoji.success} Successfully set autorole to {role.mention}.\n-# This role will be assigned to members when they join the server."
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)


def setup(client: Client):
    client.add_cog(Settings(client))
