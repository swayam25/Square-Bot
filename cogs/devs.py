import discord
import discord.ui
import os, sys
from utils import database as db, emoji
from utils import check
from discord.ext import commands
from discord.commands import slash_command, Option

class Devs(commands.Cog):
    def __init__(self, client):
        self.client = client

# On start
    @commands.Cog.listener("on_ready")
    async def when_bot_gets_ready(self):
        start_log_ch = await self.client.fetch_channel(db.system_channel_id())
        start_log_em = discord.Embed(title=f"{emoji.restart} Restarted", description=f"Logged in as **{self.client.user}** with ID `{self.client.user.id}`", color=db.theme_color)
        await start_log_ch.send(embed=start_log_em)

# On guild joined
    @commands.Cog.listener("on_guild_join")
    async def when_guild_joined(self, guild):
        db.set_on_guild_join(guild.id)
        join_log_ch = await self.client.fetch_channel(db.system_channel_id())
        join_log_em = discord.Embed(
            title=f"{emoji.plus} Someone Added Me!",
            description=f"{emoji.bullet} Name: {guild.name}/n"
                        f"{emoji.bullet} ID: `{guild.id}`/n"
                        f"{emoji.bullet} Total Members: `{guild.member_count}`/n"
                        f"{emoji.bullet} Total Humans: `{len([m for m in guild.members if not m.bot])}`/n"
                        f"{emoji.bullet} Total Bots: `{len([m for m in guild.members if m.bot])}`",
            color=db.theme_color)
        await join_log_ch.send(embed=join_log_em)
 
# On guild leave
    @commands.Cog.listener("on_guild_remove")
    async def when_removed_from_guild(self, guild):
        db.set_on_guild_remove(guild.id)
        leave_log_ch = await self.client.fetch_channel(db.system_channel_id())
        leave_log_em = discord.Embed(
            title=f"{emoji.minus} Someone Removed Me!",
            description=f"{emoji.bullet} Name: {guild.name}/n"
                        f"{emoji.bullet} ID: `{guild.id}`/n"
                        f"{emoji.bullet} Total Members: `{guild.member_count}`/n"
                        f"{emoji.bullet} Total Humans: `{len([m for m in guild.members if not m.bot])}`/n"
                        f"{emoji.bullet} Total Bots: `{len([m for m in guild.members if m.bot])}`",
            color=db.error_color)
        await leave_log_ch.send(embed=leave_log_em)

# Add dev
    @slash_command(guild_ids=db.owner_guild_ids(), name="add-dev")
    async def add_dev(
        self, ctx,
        user: Option(discord.Member, "Mention the user whom you want to add to dev")
    ):
        """Adds a bot dev"""
        if check.is_owner(ctx.author.id):
            db.add_dev_ids(user.id)
            done_em = discord.Embed(title=f"{emoji.plus} Added", description=f"Added {user.mention} to dev", color=db.theme_color)
            await ctx.respond(embed=done_em)
        else:
            error_em = discord.Embed(description=f"{emoji.error} You are not authorized to use the command", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

# Remove dev
    @slash_command(guild_ids=db.owner_guild_ids(), name="remove-dev")
    async def remove_dev(
        self, ctx,
        user: Option(discord.Member, "Mention the user whom you want to remove from dev")
    ):
        """Removes a bot dev"""
        if check.is_owner(ctx.author.id):
            db.remove_dev_ids(user.id)
            done_em = discord.Embed(title=f"{emoji.bin} Removed", description=f"Removed {user.mention} from dev", color=db.theme_color)
            await ctx.respond(embed=done_em)
        else:
            error_em = discord.Embed(description=f"{emoji.error} You are not authorized to use the command", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

# List devs
    @slash_command(guild_ids=db.owner_guild_ids(), name="list-devs")
    async def list_devs(self, ctx):
        """Shows bot devs"""
        if check.is_owner(ctx.author.id):
            num = 0
            devs_list = ""
            for ids in list(db.dev_ids()):
                num += 1
                dev_mention = f"<@{ids}>"
                devs_list += f"`{num}.` {dev_mention}\n"
            dev_em = discord.Embed(title=f"{emoji.embed} Devs List", description=devs_list, color=db.theme_color)
            await ctx.respond(embed=dev_em)
        else:
            error_em = discord.Embed(description=f"{emoji.error} You are not authorized to use the command", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

# Restart
    @slash_command(guild_ids=db.owner_guild_ids(), name="restart")
    async def restart(self, ctx):
        """Restarts the bot"""
        if check.is_dev(ctx.author.id): 
            restartEm = discord.Embed(title=f"{emoji.restart} Restarting", color=db.theme_color)
            await ctx.respond(embed=restartEm)
            os.system("clear")
            os.execv(sys.executable, ['python'] + sys.argv)
        else: 
            error_em = discord.Embed(description=f"{emoji.error} You are not authorized to use the command", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

# Reload cogs
    @slash_command(guild_ids=db.owner_guild_ids(), name="reload-cogs")
    async def reload_cogs(self, ctx):
        """Reloads bot's all files"""
        if check.is_dev(ctx.author.id): 
            reloadEm = discord.Embed(title=f"{emoji.restart} Reloaded Cogs",color=db.theme_color)
            await ctx.respond(embed=reloadEm)
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    self.client.reload_extension(f"cogs.{filename[:-3]}")
        else: 
            error_em = discord.Embed(description=f"{emoji.error} You are not authorized to use the command", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

# Shutdown
    @slash_command(guild_ids=db.owner_guild_ids(), name="shutdown")
    async def shutdown(self, ctx):
        """Shutdowns the bot"""
        if check.is_owner(ctx.author.id):
            shutdown_em = discord.Embed(title=f"{emoji.shutdown} Shutdowned", color=db.theme_color)
            await ctx.respond(embed=shutdown_em)
        else: 
            error_em = discord.Embed(description=f"{emoji.error} You are not authorized to use the command", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

# Set status
    @slash_command(guild_ids=db.owner_guild_ids(), name="set-status")
    async def set_status(
        self, ctx,
        type: Option(str, "Choose bot status type", choices=["Game", "Streaming", "Listening", "Watching"]),
        status: Option(str, "Enter new status of bot")
        ):
            """Sets custom bot status"""
            if check.is_dev(ctx.author.id): 
                if type == "Game":
                    await self.client.change_presence(activity=discord.Game(name=status))
                elif type == "Streaming":
                    await self.client.change_presence(activity=discord.Streaming(name=status, url=db.website_url))
                elif type == "Listening":
                    await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
                elif type == "Watching":
                    await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))
                status_em = discord.Embed(title=f"{emoji.console} Status Changed", description=f"Status changed to **{type}** as `{status}`", color=db.theme_color)
                await ctx.respond(embed=status_em)
            else: 
                error_em = discord.Embed(description=f"{emoji.error} You are not authorized to use the command", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)

def setup(client):
    client.add_cog(Devs(client))
