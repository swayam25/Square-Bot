import discord
from db.funcs.guild import fetch_guild_settings, set_autorole
from discord.ext import commands


class AutoMod(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Autorole
    @commands.Cog.listener()
    async def on_member_join(self, user: discord.Member):
        autorole = (await fetch_guild_settings(user.guild.id)).autorole
        if not user.bot:
            role = user.guild.get_role(autorole)
            if role:
                await user.add_roles(role)
            else:
                await set_autorole(user.guild.id, None)


def setup(client: discord.Bot):
    client.add_cog(AutoMod(client))
