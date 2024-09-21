import discord
import discord.ui
from utils import database as db, emoji
from discord.ext import commands
from discord.commands import slash_command, SlashCommandGroup

# Help embed
def help_home_em(self, ctx):
    help_em = discord.Embed(
        title=f"{self.client.user.name} Help Desk",
        description=f"Hello {ctx.author.mention}! I'm {self.client.user.name}, use the dropdown menu below to see the commands of each category. If you need help, feel free to ask in the [support server]({db.support_server_url()}).",
        color=db.theme_color
    )
    help_em.add_field(
        name=f"Categories",
        value=f"{emoji.mod} `:` **Moderation**\n" +
            f"{emoji.info} `:` **Info**\n" +
            f"{emoji.settings}  `:` **Settings**\n" +
            f"{emoji.ai} `:` **AI**\n" +
            f"{emoji.music} `:` **Music**\n" +
            f"{emoji.ticket} `:` **Tickets**"
    )
    return help_em

class HelpView(discord.ui.View):
    def __init__(self, client, ctx, timeout):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client
        self.ctx = ctx

# Interaction check
    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            help_check_em = discord.Embed(description=f"{emoji.error} You are not the author of this message", color=db.error_color)
            await interaction.response.send_message(embed=help_check_em, ephemeral=True)
            return False
        else:
            return True

# Help select menu
    @discord.ui.select(
        placeholder="Choose A Category",
        min_values=1,
        max_values=1,
        custom_id="help",
        options=[
            discord.SelectOption(label="Moderation", description="Moderate your server & keep it managed by using commands", emoji=f"{emoji.mod}"),
            discord.SelectOption(label="Info", description="See some info about bot and others", emoji=f"{emoji.info}"),
            discord.SelectOption(label="Settings", description="Highly customisable server settings", emoji=f"{emoji.settings}"),
            discord.SelectOption(label="AI", description="Use the advance technology of AI", emoji=f"{emoji.ai}"),
            discord.SelectOption(label="Music", description="Wanna chill? Just play music & enjoy", emoji=f"{emoji.music}"),
            discord.SelectOption(label="Tickets", description="Need help? Create a ticket and ask", emoji=f"{emoji.ticket}"),
            discord.SelectOption(label="Home", description="Go back to home", emoji=f"{emoji.previous}")
        ]
    )
    async def help_callback(self, select, interaction):
        cmds = ""
        if select.values[0] == "Home":
            await interaction.response.edit_message(embed=help_home_em(self, self.ctx))
        else:
            cog = self.client.get_cog(select.values[0])
            for command in cog.get_commands():
                if isinstance(command, SlashCommandGroup):
                    for subcommand in command.walk_commands():
                        cmds += f"`/{command.name} {subcommand.name}`\n{emoji.bullet} {subcommand.description}\n\n"
                else:
                    cmds += f"`/{command.name}`\n{emoji.bullet} {command.description}\n\n"
            help_em = discord.Embed(title=f"{select.values[0]} Commands", description=f"{cmds}", color=db.theme_color)
            await interaction.response.edit_message(embed=help_em)

class Help(commands.Cog):
    def __init__(self, client):
        self.client = client

# Help
    @slash_command(guild_ids=db.guild_ids(), name="help")
    async def help(self, ctx):
        """Need bot's help? Use this!"""
        helpView = HelpView(self.client, ctx, timeout=60)
        helpView.msg = await ctx.respond(embed=help_home_em(self, ctx), view=helpView)

def setup(client):
    client.add_cog(Help(client))
