import discord
from utils import database as db, emoji
from discord.ext import commands

class AutoModeration(commands.Cog):
    def __init__(self, client):
        self.client = client

# Antilink system
    @commands.Cog.listener("on_message")
    async def antilink_trigger(self, msg):
        links = [
	        "http" in msg.content.lower(),
	        "https" in msg.content.lower(),
		    ".gg" in msg.content.lower(),
		    ".com" in msg.content.lower()
	    ]
        if msg.author == self.client.user:
            pass
        elif db.antilink(msg.guild.id) == "ON":
            if any(links):
                await msg.delete()
                if db.warn_log_channel_id(msg.guild.id) != None:
                    logging_ch = await self.client.fetch_channel(db.warn_log_channel_id(msg.guild.id))
                    anti_link_log = discord.Embed(
                        title=f"{emoji.shield} Antilink",
                        description=f"{emoji.bullet} **Author**: {msg.author}\n" +
                                    f"{emoji.bullet} **Message**: {msg.content}", color=db.theme_color)
                    await logging_ch.send(embed=anti_link_log)

# Antiswear system
    @commands.Cog.listener("on_message")
    async def antiswear_trigger(self, msg):
        swear = [
		    "wtf" in msg.content.lower(),
            "fuck" in msg.content.lower(),
            "tf" in msg.content.lower(),
		    "poop" in msg.content.lower()
	    ]
        if msg.author == self.client.user:
            pass
        elif db.antiswear(msg.guild.id) == "ON":
            if any(swear):
                await msg.delete()
                if db.warn_log_channel_id(msg.guild.id) != None:
                    logging_ch = await self.client.fetch_channel(db.warn_log_channel_id(msg.guild.id))
                    anti_swear_log_em = discord.Embed(
                        title=f"{emoji.shield} Antiswear",
                        description=f"{emoji.bullet} **Author**: {msg.author}\n" +
                                    f"{emoji.bullet} **Message**: {msg.content}", color=db.theme_color)
                    await logging_ch.send(embed=anti_swear_log_em)

def setup(client):
    client.add_cog(AutoModeration(client))
