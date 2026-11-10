import asyncio
import discord
from discord import SlashCommandGroup, option, ui
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, success_view
from square.utils import config
from square.utils.emoji import emoji
from typing import Literal


class Voice(Cog, name="Voice", description="Move, mute and manage voice members.", emoji=emoji.voice, order=3):
    def __init__(self, client: Client):
        self.client = client

    vc = SlashCommandGroup(
        name="vc",
        description="Voice channel commands.",
        default_member_permissions=discord.Permissions(move_members=True),
    )

    # Move all members from one vc to another
    @vc.command(name="move")
    @option("to", description="The voice channel to move members to.")
    @option(
        "from",
        parameter_name="_from",
        description="The voice channel to move members from. Defaults to your current voice channel.",
        required=False,
    )
    async def move(self, ctx: discord.ApplicationContext, to: discord.VoiceChannel, _from: discord.VoiceChannel = None):
        """Moves all members from one voice channel to another."""
        await ctx.defer()
        source = _from or (ctx.author.voice.channel if ctx.author.voice else None)
        if source is None:
            view = error_view("You need to be in a voice channel or specify one to move from.")
            await ctx.respond(view=view, ephemeral=True)
            return
        if source == to:
            view = error_view("Source and destination voice channels cannot be the same.")
            await ctx.respond(view=view, ephemeral=True)
            return
        members = source.members
        if not members:
            view = error_view(f"{source.mention} has no members to move.")
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
                        f"Successfully moved {len(moved)} member(s) from {source.mention} to {to.mention}.\n"
                        f"{emoji.members_green} **Members**: {', '.join(moved)}"
                    ),
                    color=config.color.green,
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

    @staticmethod
    async def _check_target(ctx: discord.ApplicationContext, user: discord.Member) -> bool:
        """The shared rules for acting on someone in voice. Replies and returns False when one fails."""
        if user == ctx.author:
            error = "You cannot use it on yourself."
        elif user.voice is None:
            error = f"**{user}** is not in a voice channel."
        elif user.top_role.position >= ctx.author.top_role.position:
            error = "Given user has same role or higher role than you."
        else:
            return True
        await ctx.respond(view=error_view(error), ephemeral=True)
        return False

    async def _set_voice_flag(
        self, ctx: discord.ApplicationContext, user: discord.Member, flag: Literal["mute", "deafen"], value: bool
    ) -> None:
        """Server mutes or deafens someone (or undoes it), refusing when they're already in that state."""
        if not await self._check_target(ctx, user) or user.voice is None:
            return
        word = "muted" if flag == "mute" else "deafened"
        if (user.voice.mute if flag == "mute" else user.voice.deaf) == value:
            await ctx.respond(view=error_view(f"**{user}** is {'already' if value else 'not'} {word}."), ephemeral=True)
            return
        await (user.edit(mute=value) if flag == "mute" else user.edit(deafen=value))
        await ctx.respond(view=success_view(f"Successfully {'' if value else 'un'}{word} **{user}** in voice."))

    # Kick a member from vc
    @vc.command(name="kick")
    @option("user", description="Mention the user whom you want to kick from voice.")
    async def kick(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Kicks a member from their voice channel."""
        if not await self._check_target(ctx, user) or user.voice is None:
            return
        channel = user.voice.channel
        await user.move_to(None)
        await ctx.respond(view=success_view(f"Successfully kicked **{user}** from {channel.mention}."))

    # Server mute a member in vc
    @vc.command(name="mute")
    @option("user", description="Mention the user whom you want to mute in voice.")
    async def mute(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Server mutes a member in their voice channel."""
        await self._set_voice_flag(ctx, user, "mute", True)

    # Server unmute a member in vc
    @vc.command(name="unmute")
    @option("user", description="Mention the user whom you want to unmute in voice.")
    async def unmute(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Server unmutes a member in their voice channel."""
        await self._set_voice_flag(ctx, user, "mute", False)

    # Server deafen a member in vc
    @vc.command(name="deaf")
    @option("user", description="Mention the user whom you want to deafen in voice.")
    async def deaf(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Server deafens a member in their voice channel."""
        await self._set_voice_flag(ctx, user, "deafen", True)

    # Server undeafen a member in vc
    @vc.command(name="undeaf")
    @option("user", description="Mention the user whom you want to undeafen in voice.")
    async def undeaf(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Server undeafens a member in their voice channel."""
        await self._set_voice_flag(ctx, user, "deafen", False)

    # Pull a member into your vc
    @vc.command(name="pull")
    @option("user", description="Mention the user whom you want to pull into your voice channel.")
    async def pull(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Pulls a member into your voice channel."""
        if ctx.author.voice is None:
            view = error_view("You need to be in a voice channel to use this.")
            await ctx.respond(view=view, ephemeral=True)
        elif user == ctx.author:
            view = error_view("You cannot use it on yourself.")
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice is None:
            view = error_view(f"**{user}** is not in a voice channel.")
            await ctx.respond(view=view, ephemeral=True)
        elif user.voice.channel == ctx.author.voice.channel:
            view = error_view(f"**{user}** is already in your voice channel.")
            await ctx.respond(view=view, ephemeral=True)
        else:
            channel = ctx.author.voice.channel
            await user.move_to(channel)
            view = success_view(f"Successfully pulled **{user}** into {channel.mention}.")
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
            view = error_view("You need to be in a voice channel or specify one to set a status.")
            await ctx.respond(view=view, ephemeral=True)
            return
        try:
            await target.set_status(status)
        except discord.Forbidden:
            view = error_view(f"I don't have permission to set the status of {target.mention}.")
            await ctx.respond(view=view, ephemeral=True)
            return
        if status:
            view = success_view(f"Successfully set {target.mention}'s status to **{status}**.")
        else:
            view = success_view(f"Successfully cleared {target.mention}'s status.")
        await ctx.respond(view=view)


def setup(client: Client):
    client.add_cog(Voice(client))
