import discord
from discord import ui
from discord.commands import slash_command
from square.core import Client
from square.core.cog import Cog
from square.core.settings import Callback, SettingsPage, button
from square.core.view import DesignerView, error_view, show_loading
from square.settings import reset_all
from square.utils.emoji import emoji

HOME = "home"  # Picker value for the Back option. Any value that isn't a page name opens the home page.


class SettingsPanel(DesignerView):
    """The private `/settings` panel: a home page summarising everything, then one page per feature."""

    def __init__(self, ctx: discord.ApplicationContext, client: Client, page_types: list[type[SettingsPage]]):
        super().__init__(ctx=ctx, check_author_interaction=True, timeout=600)
        assert ctx.guild is not None  # `/settings` is a server-only command
        self.guild: discord.Guild = ctx.guild
        self.bot = client  # `client` is taken by py-cord's view
        self.author = ctx.author
        self.pages = sorted((page_type(self) for page_type in page_types), key=lambda page: page.order)
        self.page: SettingsPage | None = None
        self.armed: str | None = None  # The destructive button waiting for its confirming click
        self.render()

    def render(self) -> None:
        self.clear_items()
        if self.page is None:
            items = [
                ui.TextDisplay("## Settings"),
                *(ui.TextDisplay(f"### {page.name}\n" + "\n".join(page.summary())) for page in self.pages),
                ui.ActionRow(self.confirm_button("reset-all", "Reset all", self._reset_all)),
            ]
        else:
            items = [
                *self.page.build(),
                ui.ActionRow(self.confirm_button(f"reset-{self.page.name}", "Reset page", self._reset_page)),
            ]
        self.add_item(ui.Container(*items))
        self.add_item(ui.ActionRow(self._picker()))

    def _picker(self) -> ui.Select:
        """The page switcher, shown on every page. Off the home page it leads with a Back option."""
        options = [
            discord.SelectOption(
                label=page.name,
                value=page.name,
                description=page.description,
                emoji=page.emoji,
                default=page is self.page,
            )
            for page in self.pages
        ]
        if self.page is not None:
            options.append(
                discord.SelectOption(
                    label="Home", value=HOME, description="All settings at a glance", emoji=emoji.previous_white
                ),
            )
        picker = ui.Select(placeholder="Choose a page", options=options)
        picker.callback = self._open
        return picker

    def confirm_button(self, key: str, label: str, action: Callback) -> ui.Button:
        """A red button that only acts on a second click, so a stray click never wipes settings."""

        async def callback(interaction: discord.Interaction) -> None:
            if self.armed == key:
                self.armed = None
                await action(interaction)
            else:
                self.armed = key
                await self.refresh(interaction, keep_armed=True)

        armed = self.armed == key
        return button(
            callback,
            label="Click again to confirm" if armed else label,
            emoji=emoji.bin_white,
            style=discord.ButtonStyle.red,
        )

    async def refresh(self, interaction: discord.Interaction, *, keep_armed: bool = False) -> None:
        """Redraws the panel in place, including after a modal submit or a deferred response."""
        if not keep_armed:
            self.armed = None
        self.render()
        if interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        else:
            await interaction.response.edit_message(view=self)

    async def error(self, interaction: discord.Interaction, text: str) -> None:
        """Replies with an error the panel can't show, e.g. a role the bot can't assign."""
        if interaction.response.is_done():
            await interaction.followup.send(view=error_view(text), ephemeral=True)
        else:
            await interaction.response.send_message(view=error_view(text), ephemeral=True)

    async def _open(self, interaction: discord.Interaction) -> None:
        name = (interaction.data or {}).get("values", [None])[0]
        self.page = next((page for page in self.pages if page.name == name), None)
        await self.refresh(interaction)

    async def _reset_page(self, interaction: discord.Interaction) -> None:
        if self.page is None:
            await self.refresh(interaction)
            return
        if not await show_loading(self, interaction, "Resetting..."):
            return
        try:
            await self.page.reset(interaction)
        finally:
            await self.refresh(interaction)

    async def _reset_all(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self, interaction, "Resetting..."):
            return
        try:
            if notes := await reset_all(self.bot, self.guild, self.author):
                await self.error(interaction, "\n".join(notes))
        finally:
            await self.refresh(interaction)


class Settings(Cog, name="Settings", description="Every server setting in one panel.", emoji=emoji.settings, order=5):
    def __init__(self, client: Client):
        self.client = client

    @slash_command(name="settings")
    @discord.default_permissions(manage_guild=True)
    async def settings(self, ctx: discord.ApplicationContext):
        """Opens the server settings panel."""
        pages = [page for cog in self.client.cogs.values() for page in getattr(cog, "settings_pages", ())]
        await ctx.respond(view=SettingsPanel(ctx, self.client, pages), ephemeral=True)


def setup(client: Client):
    client.add_cog(Settings(client))
