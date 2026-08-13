import asyncio
import discord
from core import Client
from core.view import DesignerView
from discord import SlashCommandGroup, option, ui
from discord.ext import commands
from utils import config
from utils.emoji import emoji


class Voice(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    vc = SlashCommandGroup(
        name="vc",
        description="Voice channel commands.",
        default_member_permissions=discord.Permissions(move_members=True),
    )

    # Move all members from one vc to another
    @vc.command(name="move")
    @option("from", parameter_name="_from", description="The voice channel to move members from.")
    @option("to", description="The voice channel to move members to.")
    async def move(self, ctx: discord.ApplicationContext, _from: discord.VoiceChannel, to: discord.VoiceChannel):
        """Moves all members from one voice channel to another."""
        await ctx.defer()
        if _from == to:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Source and destination voice channels cannot be the same."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        members = _from.members
        if not members:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} {_from.mention} has no members to move."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        results = await asyncio.gather(*(member.move_to(to) for member in members), return_exceptions=True)
        moved = [
            member.mention for member, result in zip(members, results, strict=True) if not isinstance(result, Exception)
        ]
        failed = [
            member.mention for member, result in zip(members, results, strict=True) if isinstance(result, Exception)
        ]
        if moved:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Moved VC Members"),
                    ui.TextDisplay(
                        f"Successfully moved {len(moved)} member(s) from {_from.mention} to {to.mention}.\n"
                        f"{emoji.members} **Members**: {', '.join(moved)}"
                    ),
                )
            )
            await ctx.respond(view=view)
        if failed:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Couldn't Move Some Members"),
                    ui.TextDisplay(f"{emoji.bullet_red} **Members**: {', '.join(failed)}"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Kick a member from vc
    @vc.command(name="kick")
    @option("user", description="Mention the user whom you want to kick from voice.")
    async def kick(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Kicks a member from their voice channel."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice is None:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is not in a voice channel."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            channel = user.voice.channel
            await user.move_to(None)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully kicked **{user}** from {channel.mention}."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Server mute a member in vc
    @vc.command(name="mute")
    @option("user", description="Mention the user whom you want to mute in voice.")
    async def mute(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Server mutes a member in their voice channel."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice is None:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is not in a voice channel."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice.mute:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is already muted."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await user.edit(mute=True)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully muted **{user}** in voice."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Server unmute a member in vc
    @vc.command(name="unmute")
    @option("user", description="Mention the user whom you want to unmute in voice.")
    async def unmute(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Server unmutes a member in their voice channel."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice is None:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is not in a voice channel."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif not user.voice.mute:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is not muted."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await user.edit(mute=False)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully unmuted **{user}** in voice."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Server deafen a member in vc
    @vc.command(name="deaf")
    @option("user", description="Mention the user whom you want to deafen in voice.")
    async def deaf(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Server deafens a member in their voice channel."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice is None:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is not in a voice channel."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice.deaf:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is already deafened."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await user.edit(deafen=True)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully deafened **{user}** in voice."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Server undeafen a member in vc
    @vc.command(name="undeaf")
    @option("user", description="Mention the user whom you want to undeafen in voice.")
    async def undeaf(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Server undeafens a member in their voice channel."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice is None:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is not in a voice channel."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif not user.voice.deaf:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is not deafened."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await user.edit(deafen=False)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully undeafened **{user}** in voice."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Pull a member into your vc
    @vc.command(name="pull")
    @option("user", description="Mention the user whom you want to pull into your voice channel.")
    async def pull(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Pulls a member into your voice channel."""
        if ctx.author.voice is None:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You need to be in a voice channel to use this."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice is None:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is not in a voice channel."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice.channel == ctx.author.voice.channel:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} **{user}** is already in your voice channel."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            channel = ctx.author.voice.channel
            await user.move_to(channel)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully pulled **{user}** into {channel.mention}."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Set/clear a vc's status
    @vc.command(name="status")
    @option("status", description="The status to set. Leave empty to clear it.", required=False)
    @option(
        "channel",
        description="The voice channel to set the status for. Defaults to your current voice channel.",
        required=False,
    )
    async def status(self, ctx: discord.ApplicationContext, status: str = None, channel: discord.VoiceChannel = None):
        """Sets or clears a voice channel's status."""
        target = channel or (ctx.author.voice.channel if ctx.author.voice else None)
        if target is None:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You need to be in a voice channel or specify one to set a status."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        try:
            await target.set_status(status)
        except discord.Forbidden:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I don't have permission to set the status of {target.mention}."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        if status:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully set {target.mention}'s status to **{status}**."),
                    color=config.color.green,
                )
            )
        else:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully cleared {target.mention}'s status."),
                    color=config.color.green,
                )
            )
        await ctx.respond(view=view)


def setup(client: Client):
    client.add_cog(Voice(client))
