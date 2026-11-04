import discord
import os
import sys
from discord import ui
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from square.cogs import extensions
from square.cogs.devs.emojis import Emojis
from square.cogs.devs.eval import Eval
from square.cogs.devs.guilds import Guilds
from square.cogs.devs.stats import StatsView
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, success_view
from square.db.funcs.dev import add_dev, fetch_dev_ids, remove_dev
from square.utils import check, config, temp
from square.utils.emoji import emoji


class Devs(
    Guilds,
    Emojis,
    Cog,
    name="Devs",
    description="For developers to manage the bot.",
    emoji=emoji.console,
    order=99,
    dev_only=True,
):
    def __init__(self, client: Client):
        self.client = client

    # On start
    @commands.Cog.listener("on_ready")
    async def when_bot_gets_ready(self):
        start_log_ch = self.client.get_channel(config.system_channel_id) or await self.client.fetch_channel(
            config.system_channel_id
        )
        view = success_view(f"Logged in as **{self.client.user}** with ID `{self.client.user.id}`")
        await start_log_ch.send(view=view)

    # Dev slash cmd group
    dev = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="dev", description="Developer related commands.")

    # Add dev
    @dev.command(name="add")
    @check.is_owner()
    @option("user", description="Mention the user whom you want to add to dev")
    async def add_dev(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Adds a bot dev."""
        await add_dev(user.id)
        view = success_view(f"Added {user.mention} to dev.")
        await ctx.respond(view=view)

    # Remove dev
    @dev.command(name="remove")
    @check.is_owner()
    @option("user", description="Mention the user whom you want to remove from dev")
    async def remove_dev(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Removes a bot dev."""
        await remove_dev(user.id)
        view = success_view(f"Removed {user.mention} from dev")
        await ctx.respond(view=view)

    # List devs
    @dev.command(name="list")
    @check.is_owner()
    async def list_devs(self, ctx: discord.ApplicationContext):
        """Shows bot devs."""
        num = 0
        devs_list = ""
        dev_ids = await fetch_dev_ids()
        for ids in dev_ids:
            num += 1
            dev_mention = f"<@{ids}>"
            devs_list += f"`{num}.` {dev_mention}\n"
        if devs_list:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Dev List"),
                    ui.TextDisplay(devs_list),
                )
            )
        else:
            view = error_view("No devs found.")
        await ctx.respond(view=view)

    # Restart
    @slash_command(guild_ids=config.owner_guild_ids, name="restart")
    @check.is_dev()
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

    # Reload cogs
    @slash_command(guild_ids=config.owner_guild_ids, name="reload-cogs")
    @check.is_dev()
    async def reload_cogs(self, ctx: discord.ApplicationContext):
        """Reloads the bot cogs."""
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.reload} Reloaded Cogs"),
            )
        )
        await ctx.respond(view=view, ephemeral=True, delete_after=2)
        for name in extensions():
            self.client.reload_extension(name)

    # Shutdown
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

    # Set status
    @slash_command(guild_ids=config.owner_guild_ids, name="status")
    @check.is_dev()
    @option("status", description="Set the bot status", choices=["Online", "Idle", "DND", "Invisible"])
    @option("activity", description="Set the bot activity", max_length=128)
    async def set_status(self, ctx: discord.ApplicationContext, status: str, activity: str = None):
        """Sets the bot status."""
        await self.client.change_presence(
            status=discord.Status[status.lower()],
            activity=discord.CustomActivity(name=activity) if activity else self.client.activity,
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"{emoji.success} Status updated to `{status}`\n" + (f"```\n{activity}\n```" if activity else "")
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Stats
    @slash_command(guild_ids=config.owner_guild_ids, name="stats")
    @check.is_dev()
    async def stats(self, ctx: discord.ApplicationContext):
        """Shows bot, host & lavalink node stats."""
        await ctx.defer()
        view = StatsView(self.client, ctx)
        await view.build()
        await ctx.respond(view=view)


def setup(client: Client):
    client.add_cog(Devs(client))
    client.add_cog(Eval(client))
