import discord
from discord import ui
from discord.commands import SlashCommand, SlashCommandGroup, slash_command
from discord.ext import commands
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView
from square.utils import check, config
from square.utils.emoji import Icon, emoji
from typing import TypedDict


class CogDict(TypedDict):
    name: str
    emoji: Icon
    description: str


async def get_cogs(ctx: discord.ApplicationContext) -> list[CogDict]:
    cogs = sorted(
        (cog for cog in ctx.bot.cogs.values() if isinstance(cog, Cog) and cog.help_emoji),
        key=lambda cog: cog.help_order,
    )
    if any(cog.help_dev_only for cog in cogs) and not await check.is_dev(ctx):
        cogs = [cog for cog in cogs if not cog.help_dev_only]
    return [
        {"name": cog.qualified_name, "emoji": icon, "description": cog.description}
        for cog in cogs
        if (icon := cog.help_emoji)
    ]


class HelpView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, cogs: list[CogDict]):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.ctx = ctx
        self.cogs = cogs
        self._build_home_view()

    def _build_home_view(self) -> None:
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

    def _build_select_menu(self, current: str | None = None) -> ui.Select:
        options = [
            discord.SelectOption(
                label=cog["name"],
                description=cog["description"],
                emoji=cog["emoji"],
                default=cog["name"] == current,
            )
            for cog in self.cogs
        ]
        if current is not None:
            options.append(
                discord.SelectOption(
                    label="Home",
                    description="Go back to the home menu",
                    emoji=emoji.previous_white,
                )
            )
        select_menu = ui.Select(
            placeholder="Choose a category",
            min_values=1,
            max_values=1,
            custom_id="help",
            options=options,
        )
        select_menu.callback = lambda i: self.help_callback(i)
        return select_menu

    def _build_cog_view(self, cog_name: str) -> None:
        self.clear_items()
        cog = self.client.get_cog(cog_name)
        if not cog:
            self._build_home_view()
            return
        cmds = ""

        def build_full_command_path(cmd: SlashCommand | SlashCommandGroup) -> str:
            parts = [cmd.name]
            parent = getattr(cmd, "parent", None)
            while parent:
                parts.append(parent.name)
                parent = getattr(parent, "parent", None)
            return " ".join(reversed(parts))

        resolved_prefix = getattr(self.client, "command_prefix", "")
        if callable(resolved_prefix):
            try:
                resolved_prefix = resolved_prefix(self.client, getattr(self.ctx, "message", None)) or ""
            except Exception:
                resolved_prefix = ""

        for command in cog.get_commands():
            if isinstance(command, SlashCommandGroup):
                for subcommand in command.walk_commands():
                    if isinstance(subcommand, SlashCommandGroup):
                        continue
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
                    continue
                display = f"`{resolved_prefix}{command.name}`"
                cmds += (
                    display
                    + f"\n{emoji.bottom_right} {command.help or command.description or 'No description provided.'}\n\n"
                )
            else:
                cmds += f"`{getattr(command, 'name', 'unknown')}`\n{emoji.bottom_right} {getattr(command, 'description', 'No description provided.')}\n\n"
        if not cmds:
            cmds = "No command found."
        cog_emoji = next((cog["emoji"] for cog in self.cogs if cog["name"] == cog_name), "")
        container = ui.Container(
            ui.TextDisplay(f"## {cog_emoji} {cog_name} Commands"),
            ui.TextDisplay(cmds.strip()),
        )
        self.add_item(container)
        self.add_item(ui.ActionRow(self._build_select_menu(cog_name)))

    async def help_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        selected_value = interaction.data["values"][0]
        if selected_value == "Home":
            self._build_home_view()
        else:
            self._build_cog_view(selected_value)
        await interaction.edit(view=self)


class Help(Cog):
    def __init__(self, client):
        self.client = client

    @slash_command(name="help")
    async def help(self, ctx: discord.ApplicationContext):
        """Need bot's help? Use this!"""
        cogs = await get_cogs(ctx)
        helpView = HelpView(self.client, ctx, cogs)
        helpView.msg = await ctx.respond(view=helpView, ephemeral=True)


def setup(client: Client):
    client.add_cog(Help(client))
