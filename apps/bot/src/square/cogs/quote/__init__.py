import discord
import msgspec
from discord import ui
from discord.commands import message_command, option, slash_command
from square import imaging
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, show_loading
from square.imaging import assets
from square.imaging.templates import quote_card
from square.utils import check
from square.utils.emoji import emoji
from square.utils.markdown import plain

MAX_TEXT = 500


class QuoteView(DesignerView):
    def __init__(self, ctx: discord.ApplicationContext, data: quote_card.QuoteCard):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.data = data
        self.build()

    def build(self) -> None:
        self.clear_items()
        alt = f"{self.data.name}: {self.data.text}"
        self.add_item(
            ui.Container(ui.MediaGallery(discord.MediaGalleryItem("attachment://quote.png", description=alt[:1024])))
        )
        color = ui.Button(
            label="Mono" if self.data.color else "Color",
            emoji=emoji.palette_white,
            style=discord.ButtonStyle.grey,
            custom_id="quote_color",
        )
        color.callback = lambda interaction: self.restyle(interaction, color=not self.data.color)
        flip = ui.Button(label="Flip", emoji=emoji.flip_white, style=discord.ButtonStyle.grey, custom_id="quote_flip")
        flip.callback = lambda interaction: self.restyle(interaction, flip=not self.data.flip)
        self.add_item(ui.ActionRow(color, flip))

    async def restyle(self, interaction: discord.Interaction, **changes: bool) -> None:
        if not await show_loading(self, interaction):
            return
        self.data = msgspec.structs.replace(self.data, **changes)
        file = await render(self.data)
        self.build()
        await interaction.edit_original_response(view=self, file=file, attachments=[])


async def render(data: quote_card.QuoteCard) -> discord.File:
    return await imaging.render(quote_card.build, data, filename="quote.png", bare=True)


class Quote(Cog, name="Quote", description="Turn messages into quote images.", order=11):
    def __init__(self, client: Client):
        self.client = client

    async def _send(self, ctx: discord.ApplicationContext, text: str, user: discord.abc.User) -> None:
        await ctx.defer()
        data = quote_card.QuoteCard(
            text=text,
            name=user.display_name,
            username=user.name,
            avatar=await assets.fetch(user.display_avatar, 1024),
        )
        await ctx.respond(view=QuoteView(ctx, data), file=await render(data))

    @message_command(name="Quote", **check.ANYWHERE)
    async def quote_message(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Turns a message into a quote image."""
        if not (text := plain(message.clean_content)):
            await ctx.respond(view=error_view("That message has no text to quote."), ephemeral=True)
            return
        await self._send(ctx, text, message.author)

    @slash_command(name="quote", **check.ANYWHERE)
    @option("text", description="What they said", max_length=MAX_TEXT)
    @option("user", description="Who said it. Defaults to you.", required=False)
    async def quote(self, ctx: discord.ApplicationContext, text: str, user: discord.User = None):
        """Turns your text into a quote image."""
        if not (text := plain(text)):
            await ctx.respond(view=error_view("Give me some text to quote."), ephemeral=True)
            return
        await self._send(ctx, text, user or ctx.author)


def setup(client: Client):
    client.add_cog(Quote(client))
