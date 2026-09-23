import discord
from core import Client
from core.view import DesignerView
from db.funcs.dj import fetch_dj, remove_dj
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
from music import request
from music.player import release_guild, render_player
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
        dj_mode, dj_role_ids = await fetch_dj(self.ctx.guild.id)
        dj_roles = [role.mention for role_id in dj_role_ids if (role := self.ctx.guild.get_role(role_id))]

        ticket = emoji.on if guild_settings.ticket_cmds else emoji.off
        media_only_channel = mention_ch(guild_settings.media_only_channel_id)
        music_channel_id = guild_settings.music_channel_id
        if music_channel_id and not self.ctx.guild.get_channel(music_channel_id):
            await request.unbind(self.ctx.guild.id)
            music_channel_id = None
        music_channel = mention_ch(music_channel_id)
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
                    f"{emoji.music} **Music Channel**: {music_channel}\n"
                    f"{emoji.role} **Autorole**: {autorole}\n"
                    f"{emoji.dj} **DJ Mode**: {emoji.on if dj_mode else emoji.off}\n"
                    f"{emoji.dj} **DJ Roles**: {', '.join(dj_roles) or emoji.off}"
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

    async def _clear_music_channel(self) -> str:
        """
        Unbinds the music channel and deletes it, card and all.

        `/set music` creates the channel, so the bot is throwing away its own: everything in there
        is either the card or a request the bot already cleared.

        Returns:
            str: A note to append to the reply when the channel had to be left behind.
        """
        guild_id = self.ctx.guild.id
        channel_id = request.channel_id(guild_id)
        if channel_id is None:
            return ""
        # Unbind first, so deleting the channel doesn't race the listener that watches for it.
        await request.unbind(guild_id)
        channel = self.ctx.guild.get_channel(channel_id)
        note = ""
        if channel is not None:
            try:
                await channel.delete(reason=f"Music channel reset by {self.ctx.author}")
            except discord.HTTPException:
                note = f"\n-# I couldn't delete {channel.mention}, so it's yours to remove."
        await release_guild(self.ctx.bot, guild_id)
        return note

    async def reset(self, setting: str):
        """Resets server settings."""
        note = ""
        match setting.lower():
            case "all":
                note = await self._clear_music_channel()
                await remove_guild(self.ctx.guild.id)
                request.forget(self.ctx.guild.id)
            case "all logs":
                await remove_log_channel(self.ctx.guild.id)
            case "ticket commands":
                await set_ticket_cmds(self.ctx.guild.id, False)
            case "media only":
                await set_media_only(self.ctx.guild.id, None)
            case "auto role":
                await set_autorole(self.ctx.guild.id, None)
            case "dj":
                await remove_dj(self.ctx.guild.id)
            case "music":
                note = await self._clear_music_channel()
            case _:
                await remove_log_channel(self.ctx.guild.id, LogType.from_label(setting).key)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Successfully reset {setting.lower()} settings.{note}"),
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
        choices=["All", "All Logs", "Ticket Commands", "Media Only", "Auto Role", "DJ", "Music"]
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

    # Set music request channel
    @setting.command(name="music")
    async def set_music(self, ctx: discord.ApplicationContext):
        """Creates a channel where anything you type is queued, with the player pinned."""
        await ctx.defer()
        bound = request.channel_id(ctx.guild.id)
        if bound is not None and (existing := ctx.guild.get_channel(bound)) is not None:
            await request.adopt(ctx.bot, ctx.guild.id)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(
                        f"{emoji.success} Music channel is already set to {existing.mention}.\n"
                        "-# The player card has been refreshed."
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)
            return
        if not ctx.guild.me.guild_permissions.manage_channels:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I need the `Manage Channels` permission to create the channel."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                add_reactions=False,
                attach_files=False,
                embed_links=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False,
            ),
            ctx.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True,
                embed_links=True,
                attach_files=True,
                add_reactions=True,
            ),
        }
        try:
            channel = await ctx.guild.create_text_channel(
                "music-requests",
                overwrites=overwrites,
                topic="Send a track name or a link here to queue it.",
            )
        except discord.HTTPException as exc:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I couldn't create the music channel: {exc.text or exc}"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        await request.bind(ctx.guild.id, channel.id)
        request.prime(ctx.bot, ctx.guild.id)
        await render_player(ctx.bot, ctx.guild.id, wait=True)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"{emoji.success} Successfully set the music channel to {channel.mention}.\n"
                    "-# Send a track name or a link there to queue it. `/play` only works inside it from now on."
                ),
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
