import discord
from utils import database as db, emoji
from discord.ext import commands
from discord.commands import slash_command, option
from openai import OpenAI

# OpenAI API
openai = OpenAI(api_key=db.openai_api_token())

class ImageView(discord.ui.View):
    def __init__(self, client, ctx, prompt, timeout):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client
        self.ctx = ctx
        self.prompt = prompt

# Interaction check
    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            errorEm = discord.Embed(description=f"{emoji.error} You are not the author of this message", color=db.error_color)
            await interaction.response.send_message(embed=errorEm, ephemeral=True)
            return False
        else:
            return True

# Reload button
    @discord.ui.button(emoji=f"{emoji.restart}", custom_id="reload", style=discord.ButtonStyle.grey)
    async def reload_callback(self, button, interaction):
        await interaction.response.defer()
        response = openai.Image.create(
            prompt=self.prompt,
            n=1,
            size="1024x1024"
        )
        image_em= discord.Embed(
            title=f"{emoji.ai} Imagine",
            description=f"{emoji.bullet} **Prompt**: {self.prompt}",
            color=db.theme_color
        ).set_image(url=response['data'][0]['url'])
        await self.ctx.edit(embed=image_em)

class AI(commands.Cog):
    def __init__(self, client):
        self.client = client

# Image Generation
    @slash_command(guild_ids=db.guild_ids(), name="imagine")
    @option("prompt", description="Prompt to generate image")
    async def imagine(self, ctx, prompt: str):
        """Generate image from prompt"""
        await ctx.response.defer()
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            quality="standard",
            n=1
        )
        image_em= discord.Embed(
            title=f"{emoji.ai} Imagine",
            description=f"{emoji.bullet} **Prompt**: {prompt}",
            color=db.theme_color
        ).set_image(url=response.data[0].url)
        image_view = ImageView(self.client, ctx, prompt=prompt, timeout=60)
        await ctx.respond(embed=image_em, view=image_view)

def setup(client):
    client.add_cog(AI(client))
