import discord
from core import Client
from core.view import DesignerView
from discord import ui
from discord.commands import SlashCommand, SlashCommandGroup, slash_command
from discord.ext import commands
from typing import TypedDict
from utils import check, config
from utils.emoji import emoji


# Typed dictionary for cogs
class CogDict(TypedDict):
    name: str
    emoji: str
    description: str


# Cogs
async def get_cogs(ctx: discord.ApplicationContext) -> list[CogDict]:
    """
    Get all cogs and their commands for the help menu.

    Parameters:
        ctx (Any): The context of the command.
    """

    cogs: list[CogDict] = [
        {
            "name": "Moderation",  # This should match the class name of the cogs (spaces are removed).
            "emoji": emoji.mod,
            "description": "Moderate your server & keep it managed by using commands.",
        },
        {
            "name": "Mass Moderation",
            "emoji": emoji.mass_mod,
            "description": "Moderate your server in bulk.",
        },
        {
            "name": "Info",
            "emoji": emoji.info,
            "description": "See some info about bot and others.",
        },
        {
            "name": "Settings",
            "emoji": emoji.settings,
            "description": "Highly customisable server settings.",
        },
        {
            "name": "Music",
            "emoji": emoji.music,
            "description": "Wanna chill? Just play music & enjoy.",
        },
        {
            "name": "Tickets",
            "emoji": emoji.ticket,
            "description": "Need help? Create a ticket and ask.",
        },
        {
            "name": "Fun",
            "emoji": emoji.fun,
            "description": "Fun commands to enjoy with friends.",
        },
    ]
    if await check.is_dev(ctx):
        cogs.append(
            {
                "name": "Devs",
                "emoji": emoji.console,
                "description": "For developers to manage the bot.",
            }
        )
    return cogs


class HelpView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, cogs: list[CogDict]):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.ctx = ctx
        self.cogs = cogs
        self._build_home_view()  # Creates the initial home view

    # Home view builder
    def _build_home_view(self) -> None:
        """Clears the view and constructs the UI for the home page."""
        self.clear_items()
        category_list = "\n".join(f"{cog['emoji']} `:` **{cog['name']}**" for cog in self.cogs)
        container = ui.Container(
            ui.TextDisplay(f"## {self.client.user.name} Help Desk"),
            ui.TextDisplay(
                f"Hello {self.ctx.author.mention}! I'm {self.client.user.name}, use the dropdown menu below to see the commands of each category. If you need help, feel free to ask in the [support server]({config.support_server_url})."
            ),
            ui.TextDisplay(f"### Categories\n{category_list}"),
        )
        self.add_item(container)
        self.add_item(ui.ActionRow(self._build_select_menu()))

    # Builder util for select menu component
    def _build_select_menu(self) -> ui.Select:
        """Build the select menu for the help view."""
        select_menu = ui.Select(
            placeholder="Choose a category",
            min_values=1,
            max_values=1,
            custom_id="help",
            options=[
                *[
                    discord.SelectOption(
                        label=cog["name"],
                        description=cog["description"],
                        emoji=cog["emoji"],
                    )
                    for cog in self.cogs
                ],
                discord.SelectOption(
                    label="Home",
                    description="Go back to the home menu",
                    emoji=emoji.previous_white,
                ),
            ],
        )
        select_menu.callback = lambda i: self.help_callback(i)
        return select_menu

    # Cog view builder
    def _build_cog_view(self, cog_name: str) -> None:
        """Clears the view and constructs the UI for a specific cog's command list."""
        self.clear_items()
        cog = self.client.get_cog(cog_name.replace(" ", ""))
        if not cog:
            self._build_home_view()
            return
        cmds = ""

        # Util to build full command path including parent groups
        def build_full_command_path(cmd: SlashCommand | SlashCommandGroup) -> str:
            parts = [cmd.name]
            parent = getattr(cmd, "parent", None)
            # Walk up parent chain to root group
            while parent:
                parts.append(parent.name)
                parent = getattr(parent, "parent", None)
            return " ".join(reversed(parts))

        # Attempt to resolve a usable prefix (may be empty if unset)
        resolved_prefix = getattr(self.client, "command_prefix", "")
        if callable(resolved_prefix):
            try:
                # ApplicationContext isn't a Message, so fall back to empty on error
                resolved_prefix = resolved_prefix(self.client, getattr(self.ctx, "message", None)) or ""
            except Exception:
                resolved_prefix = ""

        for command in cog.get_commands():
            if isinstance(command, SlashCommandGroup):
                for subcommand in command.walk_commands():
                    if isinstance(subcommand, SlashCommandGroup):
                        continue  # Skip intermediate groups
                    full_path = build_full_command_path(subcommand)
                    cmds += (
                        f"</{full_path}:{command.id}>" if command.id else f"`/{full_path}`"
                    ) + f"\n{emoji.bottom_right} {subcommand.description}\n\n"
            elif isinstance(command, SlashCommand):
                full_path = command.name
                cmds += (
                    f"</{full_path}:{command.id}>" if command.id else f"`/{full_path}`"
                ) + f"\n{emoji.bottom_right} {command.description}\n\n"
            elif isinstance(command, commands.Command):
                if getattr(command, "hidden", False):
                    continue  # Skip hidden commands
                display = f"`{resolved_prefix}{command.name}`"
                cmds += (
                    display
                    + f"\n{emoji.bottom_right} {command.help or command.description or 'No description provided.'}\n\n"
                )
            else:  # Fallback: unknown command type
                cmds += f"`{getattr(command, 'name', 'unknown')}`\n{emoji.bottom_right} {getattr(command, 'description', 'No description provided.')}\n\n"
        if not cmds:
            cmds = "No command found."
        cog_emoji = next((cog["emoji"] for cog in self.cogs if cog["name"] == cog_name), "")
        container = ui.Container(
            ui.TextDisplay(f"## {cog_emoji} {cog_name} Commands"),
            ui.TextDisplay(cmds.strip()),
        )
        self.add_item(container)
        self.add_item(ui.ActionRow(self._build_select_menu()))

    # Help callback
    async def help_callback(self, interaction: discord.Interaction) -> None:
        """The callback for the select menu that rebuilds the view."""
        await interaction.response.defer()
        selected_value = interaction.data["values"][0]
        if selected_value == "Home":
            self._build_home_view()
        else:
            self._build_cog_view(selected_value)
        await interaction.edit(view=self)


class Help(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Help
    @slash_command(name="help")
    async def help(self, ctx: discord.ApplicationContext):
        """Need bot's help? Use this!"""
        cogs = await get_cogs(ctx)
        helpView = HelpView(self.client, ctx, cogs)
        helpView.msg = await ctx.respond(view=helpView)


def setup(client: Client):
    client.add_cog(Help(client))
