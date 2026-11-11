import discord
from discord.ext import commands
from square.core import Client
from square.core.cog import Cog
from square.core.view import error_view
from square.db import cache
from square.db.funcs.guild import set_autorole


class AutoMod(Cog):
    def __init__(self, client: Client):
        self.client = client

    # Media only channel
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
                await msg.delete()
                try:
                    view = error_view(
                        f"{msg.author.mention} This channel is for **media** only! Please do not send text messages here."
                    )
                    await msg.channel.send(
                        view=view, allowed_mentions=discord.AllowedMentions().users(), delete_after=10
                    )
                except discord.Forbidden:
                    pass

    # Autorole
    @commands.Cog.listener()
    async def on_member_join(self, user: discord.Member):
        if user.bot:
            return
        autorole = cache.get(user.guild.id).autorole
        if autorole is None:
            return
        if role := user.guild.get_role(autorole):
            await user.add_roles(role)
        else:
            await set_autorole(user.guild.id, None)  # The role was deleted


def setup(client: Client):
    client.add_cog(AutoMod(client))
