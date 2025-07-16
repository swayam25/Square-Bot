import discord
import io
from discord.ext import commands
from rich.console import Console
from rich.traceback import Traceback
from utils import check, config
from utils.emoji import emoji
from utils.helpers import fmt_perms

console = Console()


class ErrorHandler(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Slash cmd Error Handler
    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: discord.DiscordException):
        error_em = discord.Embed(color=config.color.red)

        if isinstance(error, commands.CommandNotFound):
            pass

        elif isinstance(error, commands.CommandOnCooldown):
            error_em.description = f"{emoji.error} You're on cooldown. Try again in {error.retry_after:.0f} seconds."

        elif isinstance(error, commands.BotMissingPermissions):
            error_em.description = (f"{emoji.error} I don't have {fmt_perms(error.missing_permissions)} permission(s)",)

        elif isinstance(error, commands.MissingPermissions):
            error_em.description = (
                f"{emoji.error} You need {fmt_perms(error.missing_permissions)} permissions to use this command."
            )

        elif isinstance(error, discord.errors.Forbidden):
            error_em.description = f"{emoji.error} I don't have permission to do that."

        elif isinstance(error, ValueError):
            error_em.description = f"{emoji.error} {error}. Please check your input and try again."

        else:
            error_em.description = f"{emoji.error} An unexpected error occurred. Please try again later."

        if await check.is_dev(ctx):
            tb = Traceback.from_exception(type(error), error, error.__traceback__, show_locals=True)
            console.print(tb)
            error_em.description = f"{emoji.error} An unexpected error occurred: **`{error.__class__.__name__}`**"
            if len(tb) < 4096:
                error_em.description += f"\n```py\n{tb}\n```"
            else:
                file = discord.File(fp=io.BytesIO(tb.encode()), filename="error.txt")
                await ctx.respond(embed=error_em, file=file, ephemeral=True)
                return
        await ctx.respond(embed=error_em, ephemeral=True)


def setup(client: discord.Bot):
    client.add_cog(ErrorHandler(client))
