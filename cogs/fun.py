import aiohttp
import asyncio
import discord
import random
from discord import option, slash_command
from discord.ext import commands
from utils import config
from utils.check import check_subreddit
from utils.emoji import emoji
from utils.helpers import meme_view
from utils.view import View


class Fun(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @slash_command(name="coinflip")
    async def coinflip(self, ctx: discord.ApplicationContext):
        """Flips a coin."""
        result = random.choice(["heads", "tails"])
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.coin} Flipping coin..."),
            )
        )
        msg = await ctx.respond(view=view)
        await asyncio.sleep(2)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"The coin landed on {emoji.coin} **{result.title()}**."),
            )
        )
        await msg.edit(view=view)

    @slash_command(name="roll")
    @option("sides", description="Number of sides on the die.", default=6, min_value=1, max_value=1000, required=False)
    async def roll(self, ctx: discord.ApplicationContext, sides: int = 6):
        """Rolls a die with a specified number of sides."""
        if sides < 1 or sides > 1000:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.error} Invalid number of sides! Please choose a number between 1 and 1000."
                    ),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view)
            return
        result = random.randint(1, sides)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.dice} Rolling a {sides} sided die..."),
            )
        )
        msg = await ctx.respond(view=view)
        await asyncio.sleep(2)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"The die landed on {emoji.dice} **{result}**."),
            )
        )
        await msg.edit(view=view)

    @slash_command(name="random")
    @option("min", description="Minimum value (inclusive).", default=1, min_value=1, max_value=1000000, required=False)
    @option(
        "max", description="Maximum value (inclusive).", default=100, min_value=1, max_value=1000000, required=False
    )
    async def random_number(self, ctx: discord.ApplicationContext, min: int = 1, max: int = 100):
        """Generates a random number between min and max."""
        if min >= max:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} Invalid range! Minimum must be less than maximum."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view)
            return
        result = random.randint(min, max)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.numbers} Generating a random number between {min} and {max}..."),
            )
        )
        msg = await ctx.respond(view=view)
        await asyncio.sleep(2)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.numbers} The random number is **{result}**."),
            )
        )
        await msg.edit(view=view)

    @slash_command(name="choose")
    @option("options", description="Comma-separated list of options to choose from. Ex: apple, banana, cherry")
    async def choose(self, ctx: discord.ApplicationContext, options: str):
        """Chooses a random option from a comma-separated list."""
        options_list = [opt.strip() for opt in options.split(",") if opt.strip()]
        if not options_list:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.error} No valid options provided! Please provide at least one option."
                    ),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view)
            return
        result = random.choice(options_list)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.sparkles} Choosing from options: {', '.join(options_list)}..."),
            )
        )
        msg = await ctx.respond(view=view)
        await asyncio.sleep(2)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.sparkles} The chosen option is **{result}**."),
            )
        )
        await msg.edit(view=view)

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
                        breed = str(data["message"]).split("/")[4].replace("-", " ").title()
                        view = View(
                            discord.ui.Container(
                                discord.ui.TextDisplay("## Woof Woof"),
                                discord.ui.TextDisplay(f"{emoji.dog} **Breed**: {breed}"),
                                discord.ui.MediaGallery(discord.MediaGalleryItem(url=data["message"])),
                            )
                        )
                        await ctx.respond(view=view)
                    else:
                        view = View(
                            discord.ui.Container(
                                discord.ui.TextDisplay(
                                    f"{emoji.error} Could not fetch a dog image. Please try again later."
                                ),
                                color=config.color.red,
                            )
                        )
                        await ctx.respond(view=view)
                else:
                    view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay(f"{emoji.error} Failed to fetch dog image."),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view)

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
                        view = View(
                            discord.ui.Container(
                                discord.ui.TextDisplay("## Meowwww"),
                                discord.ui.MediaGallery(discord.MediaGalleryItem(url=data[0]["url"])),
                            )
                        )
                        await ctx.respond(view=view)
                    else:
                        view = View(
                            discord.ui.Container(
                                discord.ui.TextDisplay(
                                    f"{emoji.error} Could not fetch a cat image. Please try again later."
                                ),
                                color=config.color.red,
                            )
                        )
                        await ctx.respond(view=view)
                else:
                    view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay(f"{emoji.error} Failed to fetch cat image."),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view)

    @slash_command(name="meme")
    @option("subreddit", description="Subreddit to fetch memes from.", required=False)
    async def meme(self, ctx: discord.ApplicationContext, subreddit: str = ""):
        """Sends a random meme."""
        await ctx.defer()
        if subreddit:
            check_result = await check_subreddit(subreddit)
            if not check_result:
                await ctx.respond(
                    view=View(
                        discord.ui.Container(
                            discord.ui.TextDisplay(
                                f"{emoji.error} The subreddit `r/{subreddit}` does not exist or is invalid."
                            ),
                            color=config.color.red,
                        )
                    ),
                    ephemeral=True,
                )
                return
            subreddit = check_result.display_name
            if check_result.nsfw and not ctx.channel.nsfw:
                await ctx.respond(
                    view=View(
                        discord.ui.Container(
                            discord.ui.TextDisplay(
                                f"{emoji.error} The subreddit `r/{subreddit}` is **NSFW**. Please enable **NSFW** in {ctx.channel.mention} or choose a different subreddit."
                            ),
                            color=config.color.red,
                        )
                    ),
                    ephemeral=True,
                )
                return
        for _ in range(3):
            meme = await meme_view(subreddit)
            if meme and (not meme.nsfw or ctx.channel.is_nsfw()):
                await ctx.respond(view=meme.view)
                return
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.error} Failed to fetch meme."),
                color=config.color.red,
            )
        )
        await ctx.respond(view=view)


def setup(client: commands.Bot):
    client.add_cog(Fun(client))
