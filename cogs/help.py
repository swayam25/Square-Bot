import discord
import discord.ui
from discord.commands import SlashCommandGroup, slash_command
from discord.ext import commands
from utils import check, config
from utils.emoji import emoji


# Cogs
async def get_cogs(ctx: discord.ApplicationContext) -> list[dict[str, str]]:
    """
    Get all cogs and their commands for the help menu.

    Parameters:
        ctx (Any): The context of the command.
    """

    cogs: list[dict[str, str]] = [
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


# Help embed
async def help_home_em(self, ctx: discord.ApplicationContext):
    help_em = discord.Embed(
        title=f"{self.client.user.name} Help Desk",
        description=f"Hello {ctx.author.mention}! I'm {self.client.user.name}, use the dropdown menu below to see the commands of each category. If you need help, feel free to ask in the [support server]({config.support_server_url}).",
        color=config.color.theme,
    )
    cogs = await get_cogs(ctx)
    help_em.add_field(name="Categories", value="\n".join(f"{cog['emoji']} `:` **{cog['name']}**" for cog in cogs))
    return help_em


class HelpView(discord.ui.View):
    def __init__(self, client: discord.Bot, ctx: discord.ApplicationContext, cogs: list[dict[str, str]], timeout: int):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client
        self.ctx = ctx
        self.cogs = cogs
        self.interaction_check = lambda i: check.author_interaction_check(ctx, i)

        self.add_item(
            discord.ui.Select(
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
                        emoji=emoji.start_white,
                    ),
                ],
            )
        )
        self.children[0].callback = lambda i: self.help_callback(self.children[0], i)

    # Help select menu
    async def help_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        cmds = ""
        if select.values[0] == "Home":
            await interaction.response.edit_message(embed=await help_home_em(self, self.ctx))
        else:
            cog = self.client.get_cog(select.values[0].replace(" ", ""))
            for command in cog.get_commands():
                if isinstance(command, SlashCommandGroup):
                    for subcommand in command.walk_commands():
                        cmds += f"</{command.name} {subcommand.name}:{command.id}>\n{emoji.bullet} {subcommand.description}\n\n"
                else:
                    cmds += f"</{command.name}:{command.id}>\n{emoji.bullet} {command.description}\n\n"
            help_em = discord.Embed(
                title=f"{select.values[0]} Commands", description=f"{cmds}", color=config.color.theme
            )
            await interaction.response.edit_message(embed=help_em)


class Help(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Help
    @slash_command(name="help")
    async def help(self, ctx: discord.ApplicationContext):
        """Need bot's help? Use this!"""
        cogs = await get_cogs(ctx)
        helpView = HelpView(self.client, ctx, cogs, timeout=60)
        helpView.msg = await ctx.respond(embed=await help_home_em(self, ctx), view=helpView)


def setup(client: discord.Bot):
    client.add_cog(Help(client))
