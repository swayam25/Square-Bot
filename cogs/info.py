import datetime
import discord
import platform
import time
from babel.dates import format_timedelta
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from utils import config
from utils.emoji import emoji

# Starting time of bot
start_time = time.time()


class Info(commands.Cog):
    def __init__(self, client):
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
        owner = await self.client.fetch_user(config.owner_id)
        dur = datetime.timedelta(seconds=int(round(time.time() - start_time)))
        dur = format_timedelta(dur)
        stats_em = discord.Embed(
            title=f"{self.client.user.name} Stats",
            description=(
                f"{emoji.ping} **Bot's Latency**: `{round(self.client.latency * 1000)} ms`\n"
                f"{emoji.duration} **Bot's Uptime**: `{str(dur)}`\n"
                f"{emoji.server} **Total Servers**: `{str(len(self.client.guilds))}`\n"
                f"{emoji.members} **Total Members**: `{len(set(self.client.get_all_members()))}`\n"
                f"{emoji.channel} **Total Channels**: `{len(set(self.client.get_all_channels()))}`\n"
                f"{emoji.python} **Python Version**: `v{platform.python_version()}`\n"
                f"{emoji.pycord} **Pycord Version**: `v{discord.__version__}`"
            ),
            color=config.color.theme,
        )
        stats_em.set_footer(text=f"Designed & Built by {owner}", icon_url=f"{owner.avatar.url}")
        await ctx.respond(embed=stats_em)

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
                f"{emoji.channel} **Total Channels**: `{len(ctx.guild.text_channels) + len(ctx.guild.voice_channels)}"
                f" ({len(ctx.guild.categories)} Categories | {len(ctx.guild.text_channels)} Text | {len(ctx.guild.voice_channels)} Voice | {len(ctx.guild.stage_channels)} Stage)`\n"
                f"{emoji.members} **Total Members**: `{len(list(ctx.guild.members))}"
                f" ({len([m for m in ctx.guild.members if not m.bot])} Humans | {len([m for m in ctx.guild.members if m.bot])} Bots)`\n"
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


def setup(client: discord.Bot):
    client.add_cog(Info(client))
