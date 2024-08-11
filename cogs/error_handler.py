import discord
import lavalink
from utils import database as db, emoji
from rich import print
from discord.ext import commands
from discord.commands import slash_command, Option

class ErrorHandler(commands.Cog):
    def __init__(self, client):
        self.client = client

# Slash cmd Error Handler
    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        print(f"[red][bold]✗[/] Error Raised: {error}[/]")
        error_em = discord.Embed()

        if isinstance(error, commands.CommandNotFound):
            pass

        elif isinstance(error, commands.BotMissingPermissions):
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_perms
            ]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            error_em = discord.Embed(description=f"{emoji.error} I don't have **{fmt}** permission(s)", color=db.error_color)

        elif isinstance(error, commands.MissingPermissions):
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_perms
            ]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            error_em = discord.Embed(description=f"{emoji.error} You don't have **{fmt}** permission(s)", color=db.error_color)

        elif isinstance(error, discord.errors.Forbidden):
            error_em = discord.Embed(description=f"{emoji.error} 404 Forbidden", color=db.error_color)

        else:
            error_em = discord.Embed(description=f"{emoji.error} An error occurred. Please try again later", color=db.error_color)
        await ctx.respond(embed=error_em, ephemeral=True)

def setup(client):
    client.add_cog(ErrorHandler(client))
