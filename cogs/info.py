import discord
import platform
import datetime, time
from utils import database as db
from utils.emoji import emoji
from discord.ext import commands
from discord.commands import slash_command, option, SlashCommandGroup

# Starting time of bot
start_time = time.time()

class Info(commands.Cog):
    def __init__(self, client):
        self.client = client

# Ping
    @slash_command(guild_ids=db.guild_ids(), name="ping")
    async def ping(self, ctx: discord.ApplicationContext):
        """Shows heartbeats of the bot."""
        ping_em = discord.Embed(description=f"{emoji.bullet} **Ping**: `{round(self.client.latency * 1000)} ms`", color=db.theme_color)
        await ctx.respond(embed=ping_em)

# Uptime
    @slash_command(guild_ids=db.guild_ids(), name="uptime")
    async def uptime(self, ctx: discord.ApplicationContext):
        """Shows bot's uptime."""
        uptime_em = discord.Embed(description=f"{emoji.bullet} **Bot's Uptime**: `{str(datetime.timedelta(seconds=int(round(time.time() - start_time))))}`", color=db.theme_color)
        await ctx.respond(embed=uptime_em)

# Stats
    @slash_command(guild_ids=db.guild_ids(), name="stats")
    async def stats(self, ctx: discord.ApplicationContext):
        """Shows bot stats."""
        owner = await self.client.fetch_user(db.owner_id())
        stats_em = discord.Embed(
            title=f"{self.client.user.name} Stats",
            description=f"{emoji.bullet} **Bot's Latency**: `{round(self.client.latency * 1000)} ms`\n" +
                        f"{emoji.bullet} **Bot's Uptime**: `{str(datetime.timedelta(seconds=int(round(time.time() - start_time))))}`\n" +
                        f"{emoji.bullet} **Total Servers**: `{str(len(self.client.guilds))}`\n" +
                        f"{emoji.bullet} **Total Members**: `{len(set(self.client.get_all_members()))}`\n" +
                        f"{emoji.bullet} **Total Channels**: `{len(set(self.client.get_all_channels()))}`\n" +
                        f"{emoji.bullet} **Python Version**: `v{platform.python_version()}`\n" +
                        f"{emoji.bullet} **Pycord Version**: `v{discord.__version__}`", color=db.theme_color)
        stats_em.set_footer(text=f"Designed & Built by {owner}", icon_url=f"{owner.avatar.url}")
        await ctx.respond(embed=stats_em)

# Avatar
    @slash_command(guild_ids=db.guild_ids(), name="avatar")
    @option("user", description="Mention the user whom you will see avatar")
    async def avatar(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Shows the avatar of the mentioned user."""
        avatar_em = discord.Embed(title=f"{user.name}'s Avatar", description=f"[Avatar URL]({user.avatar.url})", color=db.theme_color)
        avatar_em.set_image(url=f"{user.avatar.url}")
        await ctx.respond(embed=avatar_em)

# Info slash cmd group
    info = SlashCommandGroup(guild_ids=db.guild_ids(), name="info", description="Info related commands.")

# User info
    @info.command(name="user")
    @option("user", description="Mention the member whom you will see info")
    async def user_info(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Shows info of the mentioned user."""
        user_info_em = discord.Embed(
            title=f"{user.name}'s Info",
            description=f"{emoji.bullet} **Name**: `{user}`\n" +
                        f"{emoji.bullet} **ID**: `{user.id}`\n" +
                        f"{emoji.bullet} **Bot?**: {user.bot}\n" +
                        f"{emoji.bullet} **Avatar URL**: [Click Here]({user.avatar.url})\n" +
                        f"{emoji.bullet} **Status**: {user.status}\n" +
                        f"{emoji.bullet} **Nickname**: {user.nick}\n" +
                        f"{emoji.bullet} **Highest Role**: {user.top_role.mention}\n" +
                        f"{emoji.bullet} **Account Created**: {discord.utils.format_dt(user.created_at, "R")}\n" +
                        f"{emoji.bullet} **Server Joined**: {discord.utils.format_dt(user.joined_at, "R")}", color=db.theme_color)
        user_info_em.set_thumbnail(url=f"{user.avatar.url}")
        await ctx.respond(embed=user_info_em)

# Server info
    @info.command(name="server")
    async def server_info(self, ctx: discord.ApplicationContext):
        """Shows info of the current server."""
        server_info_em = discord.Embed(
            title=f"{ctx.guild.name}'s Info",
            description=f"{emoji.bullet} **Name**: {ctx.guild.name}\n" +
                        f"{emoji.bullet} **ID**: `{ctx.guild.id}`\n" +
                        f"{emoji.bullet} **Icon URL**: {f'[Click Here]({ctx.guild.icon})' if ctx.guild.icon else 'None'}\n" +
                        f"{emoji.bullet} **Owner**: {ctx.guild.owner.mention}\n" +
                        f"{emoji.bullet} **Verification Level**: `{ctx.guild.verification_level}`\n" +
                        f"{emoji.bullet} **Total Categorie(s)**: `{len(ctx.guild.categories)}`\n" +
                        f"{emoji.bullet} **Total Channel(s)**: `{len(ctx.guild.text_channels) + len(ctx.guild.voice_channels)}`\n" +
                        f"{emoji.bullet} **Text Channel(s)**: `{len(ctx.guild.text_channels)}`\n" +
                        f"{emoji.bullet} **Voice Channel(s)**: `{len(ctx.guild.voice_channels)}`\n" +
                        f"{emoji.bullet} **Stage Channel(s)**: `{len(ctx.guild.stage_channels)}`\n" +
                        f"{emoji.bullet} **Total Member(s)**: `{len([m for m in ctx.guild.members])}`\n" +
                        f"{emoji.bullet} **Human(s)**: `{len([m for m in ctx.guild.members if not m.bot])}`\n" +
                        f"{emoji.bullet} **Bot(s)**: `{len([m for m in ctx.guild.members if m.bot])}`\n" +
                        f"{emoji.bullet} **Role(s)**: `{len(ctx.guild.roles)}`\n" +
                        f"{emoji.bullet} **Server Created**: {discord.utils.format_dt(ctx.guild.created_at, "R")}", color=db.theme_color)
        server_info_em.set_thumbnail(url=ctx.guild.icon if ctx.guild.icon else "")
        await ctx.respond(embed=server_info_em)

# Emoji info
    @info.command(name="emoji")
    @option("icon", description="Enter the emoji")
    async def emoji_info(self, ctx: discord.ApplicationContext, icon: discord.Emoji):
        """Shows info of the given emoji."""
        emoji_info_em = discord.Embed(
            description=f"{emoji.bullet} **Name**: {icon.name}\n" +
                        f"{emoji.bullet} **ID**: `{icon.id}`\n" +
                        f"{emoji.bullet} **Emoji URL**: [Click Here]({icon.url})\n" +
                        f"{emoji.bullet} **Is Animated?**: {icon.animated}\n" +
                        f"{emoji.bullet} **Usage**: `{icon}`\n" +
                        f"{emoji.bullet} **Emoji Created**: {discord.utils.format_dt(icon.created_at, "R")}", color=db.theme_color)
        emoji_info_em.set_thumbnail(url=f"{icon.url}")
        await ctx.respond(embed=emoji_info_em)

def setup(client: discord.Client):
    client.add_cog(Info(client))
