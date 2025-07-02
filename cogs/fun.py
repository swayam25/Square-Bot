import asyncio
import discord
import random
from discord import slash_command
from discord.ext import commands
from utils import config
from utils.emoji import emoji


class Fun(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @slash_command(name="coinflip")
    async def coinflip(self, ctx: discord.ApplicationContext):
        """Flips a coin."""
        result = random.choice(["heads", "tails"])
        em = discord.Embed(description=f"{emoji.coin} Flipping coin...", color=config.color.theme)
        msg = await ctx.respond(embed=em)
        await asyncio.sleep(2)
        em = discord.Embed(
            description=f"The coin landed on {emoji.coin} **{result.title()}**.", color=config.color.theme
        )
        await msg.edit(embed=em)


def setup(client: commands.Bot):
    client.add_cog(Fun(client))
