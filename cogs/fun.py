import aiohttp
import asyncio
import discord
import random
from discord import option, slash_command
from discord.ext import commands
from utils import config
from utils.emoji import emoji
from utils.helpers import meme_embed


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

    @slash_command(name="roll")
    @option("sides", description="Number of sides on the die.", default=6, min_value=1, max_value=1000)
    async def roll(self, ctx: discord.ApplicationContext, sides: int = 6):
        """Rolls a die with a specified number of sides."""
        if sides < 1 or sides > 1000:
            err_em = discord.Embed(
                description=f"{emoji.error} Invalid number of sides! Please choose a number between 1 and 1000.",
                color=config.color.error,
            )
            await ctx.respond(embed=err_em)
            return
        result = random.randint(1, sides)
        em = discord.Embed(description=f"{emoji.dice} Rolling a {sides} sided die...", color=config.color.theme)
        msg = await ctx.respond(embed=em)
        await asyncio.sleep(2)
        em = discord.Embed(description=f"The die landed on {emoji.dice} **{result}**.", color=config.color.theme)
        await msg.edit(embed=em)

    @slash_command(name="random")
    @option("min", description="Minimum value (inclusive).", default=1, min_value=1, max_value=1000000)
    @option("max", description="Maximum value (inclusive).", default=100, min_value=1, max_value=1000000)
    async def random_number(self, ctx: discord.ApplicationContext, min: int = 1, max: int = 100):
        """Generates a random number between min and max."""
        if min >= max:
            err_em = discord.Embed(
                description=f"{emoji.error} Invalid range! Minimum must be less than maximum.",
                color=config.color.error,
            )
            await ctx.respond(embed=err_em)
            return
        result = random.randint(min, max)
        em = discord.Embed(
            description=f"{emoji.numbers} Generating a random number between {min} and {max}...",
            color=config.color.theme,
        )
        msg = await ctx.respond(embed=em)
        await asyncio.sleep(2)
        em = discord.Embed(description=f"{emoji.numbers} The random number is **{result}**.", color=config.color.theme)
        await msg.edit(embed=em)

    @slash_command(name="choose")
    @option("options", description="Comma-separated list of options to choose from. Ex: apple, banana, cherry")
    async def choose(self, ctx: discord.ApplicationContext, options: str):
        """Chooses a random option from a comma-separated list."""
        options_list = [opt.strip() for opt in options.split(",") if opt.strip()]
        if not options_list:
            err_em = discord.Embed(
                description=f"{emoji.error} No valid options provided! Please provide at least one option.",
                color=config.color.error,
            )
            await ctx.respond(embed=err_em)
            return
        result = random.choice(options_list)
        em = discord.Embed(
            description=f"{emoji.sparkles} Choosing from options: {', '.join(options_list)}...",
            color=config.color.theme,
        )
        msg = await ctx.respond(embed=em)
        await asyncio.sleep(2)
        em = discord.Embed(description=f"{emoji.sparkles} The chosen option is **{result}**.", color=config.color.theme)
        await msg.edit(embed=em)

    @slash_command(name="dog")
    async def dog(self, ctx: discord.ApplicationContext):
        """Sends a cute dog image."""
        url = "https://dog.ceo/api/breeds/image/random"
        await ctx.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if "message" in data:
                        em = discord.Embed(
                            title="Woof Woof",
                            description=f"{emoji.dog} **Breed**: {str(data['message']).split('/')[4].replace('-', ' ').title()}",
                            color=config.color.theme,
                        )
                        em.set_image(url=data["message"])
                        await ctx.respond(embed=em)
                    else:
                        err_em = discord.Embed(
                            description=f"{emoji.error} Could not fetch a dog image. Please try again later.",
                            color=config.color.error,
                        )
                        await ctx.respond(embed=err_em)
                else:
                    err_em = discord.Embed(
                        description=f"{emoji.error} Failed to fetch dog image.",
                        color=config.color.error,
                    )
                    await ctx.respond(embed=err_em)

    @slash_command(name="cat")
    async def cat(self, ctx: discord.ApplicationContext):
        """Sends a cute cat image."""
        url = "https://api.thecatapi.com/v1/images/search"
        await ctx.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        em = discord.Embed(
                            title="Meowwww",
                            color=config.color.theme,
                        )
                        em.set_image(url=data[0]["url"])
                        await ctx.respond(embed=em)
                    else:
                        err_em = discord.Embed(
                            description=f"{emoji.error} Could not fetch a cat image. Please try again later.",
                            color=config.color.error,
                        )
                        await ctx.respond(embed=err_em)
                else:
                    err_em = discord.Embed(
                        description=f"{emoji.error} Failed to fetch cat image.",
                        color=config.color.error,
                    )
                    await ctx.respond(embed=err_em)

    @slash_command(name="meme")
    async def meme(self, ctx: discord.ApplicationContext):
        """Sends a random meme."""
        await ctx.defer()
        meme = await meme_embed()
        if meme:
            await ctx.respond(embed=meme)
        else:
            err_em = discord.Embed(
                description=f"{emoji.error} Failed to fetch meme.",
                color=config.color.error,
            )
            await ctx.respond(embed=err_em)


def setup(client: commands.Bot):
    client.add_cog(Fun(client))
