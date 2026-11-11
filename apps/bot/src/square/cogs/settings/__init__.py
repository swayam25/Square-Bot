import discord
from discord import ui
from discord.commands import slash_command
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView
from square.utils import config
from square.utils.emoji import emoji


class Settings(
    Cog, name="Settings", description="Server settings live on the dashboard.", emoji=emoji.settings, order=5
):
    def __init__(self, client: Client):
        self.client = client

    @slash_command(name="settings")
    @discord.default_permissions(manage_guild=True)
    async def settings(self, ctx: discord.ApplicationContext):
        """Links to this server's settings on the dashboard."""
        assert ctx.guild is not None
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"## Settings Dashboard\n"
                    f"Change how {self.client.user.name} works in **{ctx.guild.name}** from the dashboard."
                ),
            ),
            ui.ActionRow(
                ui.Button(
                    label="Open dashboard",
                    style=discord.ButtonStyle.link,
                    url=f"{config.dashboard_url}/guild/{ctx.guild.id}",
                )
            ),
        )
        await ctx.respond(view=view, ephemeral=True)


def setup(client: Client):
    client.add_cog(Settings(client))
