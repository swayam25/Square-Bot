import discord
from db.funcs.guild import fetch_guild_settings, set_autorole
from discord.ext import commands
from utils import config
from utils.emoji import emoji


class AutoMod(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Media only channel
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return

        guild_settings = await fetch_guild_settings(msg.guild.id)
        media_only_channel_id = guild_settings.media_only_channel_id

        if msg.channel.id == media_only_channel_id:
            if not msg.attachments and not msg.content.startswith("http"):
                await msg.delete()
                try:
                    err_em = discord.Embed(
                        description=f"{emoji.error} This channel is for **media** only! Please do not send text messages here.",
                        color=config.color.red,
                    )
                    await msg.channel.send(msg.author.mention, embed=err_em, delete_after=10)
                except discord.Forbidden:
                    pass

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
