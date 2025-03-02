import discord
from utils import database as db
from discord.ext import commands

class AutoMod(commands.Cog):
    def __init__(self, client):
        self.client = client

# Autorole
    @commands.Cog.listener()
    async def on_member_join(self, user: discord.Member):
        autorole = db.autorole(user.guild.id)
        if autorole != None and user.bot == False:
            role = user.guild.get_role(autorole)
            if role != None:
                await user.add_roles(role)
            else:
                db.autorole(user.guild.id, None, "set")