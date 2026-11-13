import discord
from discord.ext import commands
from square.core import Client
from square.core.cog import Cog
from square.core.view import error_view
from square.db import cache


class AutoMod(Cog):
    def __init__(self, client: Client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot or msg.guild is None:
            return

        media_only_channel_id = cache.get(msg.guild.id).media_only_channel_id

        if msg.channel.id == media_only_channel_id:
            if (
                not msg.attachments
                and not msg.content.startswith("http")
                and msg.author.guild_permissions.manage_messages is False
            ):
                try:
                    await msg.delete()
                    view = error_view(
                        f"{msg.author.mention} This channel is for **media** only! Please do not send text messages here."
                    )
                    await msg.channel.send(
                        view=view, allowed_mentions=discord.AllowedMentions().users(), delete_after=10
                    )
                except discord.Forbidden, discord.NotFound:
                    pass

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
    client.add_cog(AutoMod(client))
