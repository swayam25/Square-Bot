import discord
import json
from discord.commands import message_command
from io import BytesIO
from square.cogs.utility.grab import GrabView, collect_expressions
from square.core import Client
from square.core.cog import Cog
from square.core.view import error_view
from square.utils import check


class Utility(Cog, name="Utility", description="See the raw data behind Discord objects.", order=14):
    def __init__(self, client: Client):
        self.client = client

    @message_command(name="View JSON", **check.USER_INSTALL)
    async def view_json(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Sends the raw API data of a message as a JSON file."""
        # Discord sends the message's raw API object with the interaction, so no extra request is needed
        raw = ctx.interaction.data["resolved"]["messages"][str(message.id)]
        payload = json.dumps(raw, indent=2, ensure_ascii=False).encode()
        await ctx.respond(file=discord.File(BytesIO(payload), filename="message.json"))

    @message_command(name="Grab Expression", **check.USER_INSTALL)
    async def grab(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Shows the custom emojis and stickers in a message, ready to save or add to the server."""
        items = collect_expressions(message)
        if not items:
            await ctx.respond(view=error_view("That message has no custom emojis or stickers to grab."), ephemeral=True)
            return
        guild = self.client.get_guild(ctx.guild_id) if ctx.guild_id else None
        manager = bool(guild and ctx.interaction.permissions.manage_emojis)
        await ctx.respond(view=GrabView(self.client, items, guild, manager), ephemeral=True)


def setup(client: Client):
    client.add_cog(Utility(client))
