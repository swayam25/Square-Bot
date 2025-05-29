import discord
from discord.ext import commands
from utils import database as db


class AutoMod(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Autorole
    @commands.Cog.listener()
    async def on_member_join(self, user: discord.Member):
        autorole = db.autorole(user.guild.id)
        if autorole is not None and not user.bot:
            role = user.guild.get_role(autorole)
            if role:
                await user.add_roles(role)
            else:
                db.autorole(user.guild.id, None, "set")


def setup(client: discord.Client):
    client.add_cog(AutoMod(client))
