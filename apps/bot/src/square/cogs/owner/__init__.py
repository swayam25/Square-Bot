import discord
import importlib
import os
import sys
import time
from discord import ui
from discord.commands import option, slash_command
from discord.ext import commands
from importlib.metadata import version
from square.cogs import extensions
from square.cogs.info import start_time
from square.cogs.owner.emojis import Emojis
from square.cogs.owner.eval import Eval
from square.cogs.owner.guilds import Guilds
from square.cogs.owner.stats import StatsView
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, success_view
from square.utils import check, config, temp
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count

# Cogs import these without them being cogs, so `reload_extension` alone leaves them stale. Dependencies first.
# `assets` is skipped to keep its avatar cache.
_IMAGING = (
    "square.imaging.tokens",
    "square.imaging.theme",
    "square.imaging.fonts",
    "square.imaging.canvas",
    "square.imaging.layout",
    "square.imaging.components",
    "square.imaging",
)


def _reload_imaging() -> None:
    templates = sorted(name for name in sys.modules if name.startswith("square.imaging.templates."))
    for name in (*_IMAGING, *templates, "square.imaging.templates"):
        if module := sys.modules.get(name):
            importlib.reload(module)


class Owner(
    Guilds,
    Emojis,
    Cog,
    name="Owner",
    description="Tools only the bot owner can use.",
):
    def __init__(self, client: Client):
        self.client = client
        self.announced = False

    @commands.Cog.listener("on_ready")
    async def when_bot_gets_ready(self):
        # py-cord fires on_ready again after a reconnect that can't resume, which isn't a fresh start
        if self.announced:
            return
        self.announced = True
        channel = self.client.get_channel(config.system_channel_id) or await self.client.fetch_channel(
            config.system_channel_id
        )
        guilds = self.client.guilds
        members = sum(guild.member_count or 0 for guild in guilds)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"## {self.client.user.display_name} is online"),
                ui.TextDisplay(
                    f"{emoji.server} **Servers**: `{fmt_count(len(guilds))}`\n"
                    f"{emoji.members} **Members**: `{fmt_count(members)}`\n"
                    f"{emoji.console} **Commands**: `{fmt_count(len(self.client.application_commands))}`\n"
                    f"{emoji.duration} **Ready In**: `{time.time() - start_time:.1f}s`"
                ),
                ui.TextDisplay(f"-# v{version('square')}"),
                color=config.color.theme,
            )
        )
        await channel.send(view=view)

    @slash_command(guild_ids=config.owner_guild_ids, name="restart")
    @check.is_owner()
    async def restart(self, ctx: discord.ApplicationContext):
        """Restarts the bot."""
        await self.client.change_presence(
            status=discord.Status.idle,
            activity=discord.CustomActivity(name="Restarting..."),
        )
        view = DesignerView(ui.Container(ui.TextDisplay(f"{emoji.loading} Restarting...")))
        msg = await ctx.respond(view=view)
        temp.set("restart_msg", {"channel_id": msg.channel.id, "id": (await msg.original_message()).id})
        await self.client.wait_until_ready()
        await self.client.close()
        os.system("clear")
        os.execv(sys.executable, [sys.executable, "-m", "square"])

    @slash_command(guild_ids=config.owner_guild_ids, name="reload-cogs")
    @check.is_owner()
    async def reload_cogs(self, ctx: discord.ApplicationContext):
        """Reloads the bot cogs."""
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.reload} Reloaded Cogs"),
            )
        )
        await ctx.respond(view=view, ephemeral=True, delete_after=2)
        _reload_imaging()
        for name in extensions():
            self.client.reload_extension(name)

    @slash_command(guild_ids=config.owner_guild_ids, name="shutdown")
    @check.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext):
        """Shutdowns the bot."""
        await self.client.change_presence(
            status=discord.Status.dnd,
            activity=None,
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.shutdown} Bot is now shutdown."),
                color=config.color.red,
            )
        )
        await ctx.respond(view=view)
        await self.client.wait_until_ready()
        await self.client.close()

    @slash_command(guild_ids=config.owner_guild_ids, name="status")
    @check.is_owner()
    @option("status", description="Set the bot status", choices=["Online", "Idle", "DND", "Invisible"])
    @option("activity", description="Set the bot activity", max_length=128)
    async def set_status(self, ctx: discord.ApplicationContext, status: str, activity: str = None):
        """Sets the bot status."""
        await self.client.change_presence(
            status=discord.Status[status.lower()],
            activity=discord.CustomActivity(name=activity) if activity else self.client.activity,
        )
        await ctx.respond(
            view=success_view(f"Status updated to `{status}`" + (f"\n```\n{activity}\n```" if activity else ""))
        )

    @slash_command(guild_ids=config.owner_guild_ids, name="stats")
    @check.is_owner()
    async def stats(self, ctx: discord.ApplicationContext):
        """Shows bot, host & lavalink node stats."""
        await ctx.defer()
        view = StatsView(self.client, ctx)
        await view.build()
        await ctx.respond(view=view)


def setup(client: Client):
    client.add_cog(Owner(client))
    client.add_cog(Eval(client))
