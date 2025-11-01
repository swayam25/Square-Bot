import discord
import io
import traceback
from core import Client
from core.view import DesignerView
from discord import ui
from discord.ext import commands
from rich.console import Console
from rich.traceback import Traceback
from utils import check, config
from utils.emoji import emoji
from utils.helpers import fmt_perms

console = Console()


class ErrorHandler(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # Slash cmd Error Handler
    @commands.Cog.listener(name="on_application_command_error")
    @commands.Cog.listener(name="on_command_error")
    async def on_error(self, ctx: discord.ApplicationContext | commands.Context, error: discord.DiscordException):
        msg: str | None = None
        is_app: bool = isinstance(ctx, discord.ApplicationContext)

        if isinstance(error, commands.CommandNotFound):
            return

        elif await check.is_dev(ctx):
            tb = Traceback.from_exception(type(error), error, error.__traceback__)
            console.print(tb)
            error = getattr(error, "original", None) or error
            err = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            msg = f"{emoji.error} An unexpected error occurred: **`{error.__class__.__name__}`**"
            if len(err) < 4096:
                msg += f"\n```py\n{err}\n```"
            else:
                file = discord.File(fp=io.BytesIO(tb.encode()), filename="error.txt")
                if is_app:
                    await ctx.respond(file=file, ephemeral=True)
                else:
                    await ctx.reply(file=file)
                return

        elif isinstance(error, check.NotAuthorized):
            if is_app:
                msg = f"{emoji.error} You are not authorized to use this command."
            else:  # Because we don't want to send errors for normal commands
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
        view = DesignerView(ui.Container(ui.TextDisplay(msg), color=config.color.red))

        if is_app:
            await ctx.respond(view=view, ephemeral=True)
        else:
            await ctx.reply(view=view, delete_after=5)


def setup(client: Client):
    client.add_cog(ErrorHandler(client))
