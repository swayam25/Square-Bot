import discord
import io
import traceback
from discord.ext import commands
from rich.console import Console
from rich.traceback import Traceback
from utils import check, config
from utils.emoji import emoji
from utils.helpers import fmt_perms
from utils.view import View

console = Console()


class ErrorHandler(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Slash cmd Error Handler
    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: discord.DiscordException):
        msg: str | None = None

        if isinstance(error, commands.CommandNotFound):
            pass

        elif await check.is_dev(ctx):
            tb = Traceback.from_exception(type(error), error, error.__traceback__, show_locals=True)
            console.print(tb)
            error = getattr(error, "original", None) or error
            err = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            msg = f"{emoji.error} An unexpected error occurred: **`{error.__class__.__name__}`**"
            if len(err) < 4096:
                msg += f"\n```py\n{err}\n```"
            else:
                file = discord.File(fp=io.BytesIO(tb.encode()), filename="error.txt")
                await ctx.respond(file=file, ephemeral=True)
                return

        elif isinstance(error, commands.CommandOnCooldown):
            msg = f"{emoji.error} You're on cooldown. Try again in {error.retry_after:.0f} seconds."

        elif isinstance(error, commands.BotMissingPermissions):
            msg = (f"{emoji.error} I don't have {fmt_perms(error.missing_permissions)} permission(s)",)

        elif isinstance(error, commands.MissingPermissions):
            msg = f"{emoji.error} You need {fmt_perms(error.missing_permissions)} permissions to use this command."

        elif isinstance(error, discord.errors.Forbidden):
            msg = f"{emoji.error} I don't have permission to do that."

        elif isinstance(error, ValueError):
            msg = f"{emoji.error} {error}. Please check your input and try again."

        else:
            msg = f"{emoji.error} An unexpected error occurred. Please try again later."
        view = View(discord.ui.Container(discord.ui.TextDisplay(msg), color=config.color.red))
        await ctx.respond(view=view, ephemeral=True)


def setup(client: discord.Bot):
    client.add_cog(ErrorHandler(client))
