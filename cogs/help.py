import discord
from core import Client
from core.view import View
from discord.commands import SlashCommandGroup, slash_command
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
        {"name": "Fun", "emoji": emoji.fun, "description": "Fun commands to enjoy with friends."},
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


class HelpView(View):
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
        container = discord.ui.Container(
            discord.ui.TextDisplay(f"## {self.client.user.name} Help Desk"),
            discord.ui.TextDisplay(
                f"Hello {self.ctx.author.mention}! I'm {self.client.user.name}, use the dropdown menu below to see the commands of each category. If you need help, feel free to ask in the [support server]({config.support_server_url})."
            ),
            discord.ui.TextDisplay(f"### Categories\n{category_list}"),
        )
        self.add_item(container)
        self.add_item(self._build_select_menu())

    # Builder util for select menu component
    def _build_select_menu(self) -> discord.ui.Select:
        """Build the select menu for the help view."""
        select_menu = discord.ui.Select(
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
        for command in cog.get_commands():
            if isinstance(command, SlashCommandGroup):
                for subcommand in command.walk_commands():
                    cmds += (
                        f"</{command.name} {subcommand.name}:{command.id}>"
                        if command.id
                        else f"`/{command.name} {subcommand.name}`"
                    ) + f"\n{emoji.bullet} {subcommand.description}\n\n"
            else:
                cmds += (
                    f"</{command.name}:{command.id}>" if command.id else f"`/{command.name}`"
                ) + f"\n{emoji.bullet} {command.description}\n\n"
        cog_emoji = next((cog["emoji"] for cog in self.cogs if cog["name"] == cog_name), "")
        container = discord.ui.Container(
            discord.ui.TextDisplay(f"## {cog_emoji} {cog_name} Commands"),
            discord.ui.TextDisplay(cmds.strip()),
        )
        self.add_item(container)
        self.add_item(self._build_select_menu())

    # Help callback
    async def help_callback(self, interaction: discord.Interaction) -> None:
        """The callback for the select menu that rebuilds the view."""
        selected_value = interaction.data["values"][0]
        if selected_value == "Home":
            self._build_home_view()
        else:
            self._build_cog_view(selected_value)
        await interaction.edit(
            view=self, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
        )


class Help(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Help
    @slash_command(name="help")
    async def help(self, ctx: discord.ApplicationContext):
        """Need bot's help? Use this!"""
        cogs = await get_cogs(ctx)
        helpView = HelpView(self.client, ctx, cogs)
        helpView.msg = await ctx.respond(
            view=helpView, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
        )


def setup(client: Client):
    client.add_cog(Help(client))
