import discord
from discord.ext import commands
from utils import check, config
from utils.emoji import emoji
from utils.helpers import fmt_perms


class ErrorHandler(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Slash cmd Error Handler
    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: discord.DiscordException):
        error_em = discord.Embed(color=config.color.error)

        if isinstance(error, commands.CommandNotFound):
            pass

        elif isinstance(error, commands.CommandOnCooldown):
            error_em.description = f"{emoji.error} You're on cooldown. Try again in {error.retry_after:.0f} seconds."

        elif isinstance(error, commands.BotMissingPermissions):
            error_em.description = (f"{emoji.error} I don't have {fmt_perms(error.missing_permissions)} permission(s)",)

        elif isinstance(error, commands.MissingPermissions):
            error_em.description = (
                f"{emoji.error} You need {fmt_perms(error.missing_permissions)} permission(s) to use this command."
            )

        elif isinstance(error, discord.errors.Forbidden):
            error_em.description = f"{emoji.error} I don't have permission to do that."

        elif await check.is_dev().predicate(ctx):
            error_em.description = (
                f"{emoji.error} An unexpected error occurred: **`{error.__class__.__name__}`**\n```\n{error}```"
            )
        await ctx.respond(embed=error_em, ephemeral=True)


def setup(client: discord.Bot):
    client.add_cog(ErrorHandler(client))
