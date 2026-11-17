import discord
from discord.ext import commands
from square.core import Client
from square.core.cog import Cog
from square.db import cache


class Members(Cog):
    def __init__(self, client: Client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = cache.get(member.guild.id)
        role_ids = [
            *(settings.autorole_bot_ids if member.bot and settings.autorole_split else settings.autorole_ids),
            *settings.autorole_users.get(member.id, ()),
        ]
        top = member.guild.me.top_role
        roles = [
            role
            for role_id in dict.fromkeys(role_ids)
            if (role := member.guild.get_role(role_id)) and not role.managed and role < top
        ]
        if not roles:
            return
        try:
            await member.add_roles(*roles, reason="Auto role")
        except discord.Forbidden, discord.NotFound:
            pass


def setup(client: Client):
    client.add_cog(Members(client))
