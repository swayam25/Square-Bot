import discord
from utils import database as db, emoji
from discord.ext import commands
from discord.commands import slash_command, option, SlashCommandGroup

class Settings(commands.Cog):
    def __init__(self, client):
        self.client = client

# Settings
    @slash_command(guild_ids=db.guild_ids(), name="settings")
    @discord.default_permissions(manage_channels=True)
    async def settings(self, ctx):
        """Shows server settings."""

        mod_channel = await self.client.fetch_channel(db.mod_log_ch(ctx.guild.id)) if db.mod_log_ch(ctx.guild.id) != None else "Not set"
        mod_cmd_channel = await self.client.fetch_channel(db.mod_cmd_log_ch(ctx.guild.id)) if db.mod_cmd_log_ch(ctx.guild.id) != None else "Not set"
        ticket_channel = await self.client.fetch_channel(db.ticket_log_ch(ctx.guild.id)) if db.ticket_log_ch(ctx.guild.id) != None else "Not set"
        antilink = db.antilink(ctx.guild.id) if db.antilink(ctx.guild.id) != None else "OFF"
        antiswear = db.antiswear(ctx.guild.id) if db.antiswear(ctx.guild.id) != None else "OFF"

        set_em = discord.Embed(
            title=f"{emoji.settings} {ctx.guild.name}'s Settings",
            description=f"{emoji.bullet} **Mod Log Channel**: {mod_channel}\n" +
                        f"{emoji.bullet} **Mod Command Log Channel**: {mod_cmd_channel}\n" +
                        f"{emoji.bullet} **Ticket Log Channel**: {ticket_channel}\n" +
                        f"{emoji.bullet} **Antilink**: {antilink}\n" +
                        f"{emoji.bullet} **Antiswear**: {antiswear}",
            color=db.theme_color
        )
        await ctx.respond(embed=set_em)

# Settings slash cmd group
    setting = SlashCommandGroup(guild_ids=db.guild_ids(), name="setting", description="Server settings commands")

# Reset
    @setting.command(name="reset")
    @discord.default_permissions(manage_channels=True)
    async def reset_settings(self, ctx):
        """Resets server settings."""
        db.delete(ctx.guild.id)
        reset_em = discord.Embed(
            title=f"{emoji.settings} Reset Settings",
            description=f"Successfully reset the server settings",
            color=db.theme_color
        )
        await ctx.respond(embed=reset_em)

# Set mod log
    @setting.command(name="mod-log")
    @discord.default_permissions(manage_channels=True)
    @option("channel", description="Mention the mod log channel")
    async def set_mod_log(self, ctx, channel: discord.TextChannel):
        """Sets mod log channel."""
        db.mod_log_ch(guild_id=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Mod Log Settings",
            description=f"Successfully set mod log channel to {channel.mention}",
            color=db.theme_color
        )
        await ctx.respond(embed=logging_em)

# Set mod cmd log
    @setting.command(name="mod-command-log")
    @discord.default_permissions(manage_channels=True)
    @option("channel", description="Mention the mod command log channel")
    async def set_mod_cmd_log(self, ctx, channel: discord.TextChannel):
        """Sets mod command log channel."""
        db.mod_cmd_log_ch(guild_id=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Mod Command Log Settings",
            description=f"Successfully set mod command log channel to {channel.mention}",
            color=db.theme_color
        )
        await ctx.respond(embed=logging_em)

# Set ticket log
    @setting.command(name="ticket-log")
    @discord.default_permissions(manage_channels=True)
    @option("channel", description="Mention the ticket log channel")
    async def set_ticket_log(self, ctx, channel: discord.TextChannel):
        """Sets ticket log channel."""
        db.ticket_log_ch(guild_id=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Ticket Log Settings",
            description=f"Successfully set ticket log channel to {channel.mention}",
            color=db.theme_color
        )
        await ctx.respond(embed=logging_em)

# Set antilink
    @setting.command(name="antilink")
    @discord.default_permissions(manage_channels=True)
    @option("status", description="Choose the antilink status", choices=["ON", "OFF"])
    async def set_antilink(self, ctx, status: str):
        """Sets antilink."""
        db.antilink(guild_id=ctx.guild.id, status=status, mode="set")
        anitlink_em = discord.Embed(
            title=f"{emoji.settings} Antilink Settings",
            description=f"Successfully set antilink status to **{status}**",
            color=db.theme_color
        )
        await ctx.respond(embed=anitlink_em)

# Set antiswear
    @setting.command(name="antiswear")
    @discord.default_permissions(manage_channels=True)
    @option("status", description="Choose the antiswear status", choices=["ON", "OFF"])
    async def setAntiswear(self, ctx, status: str):
        """Sets antiswear."""
        db.antiswear(guild_id=ctx.guild.id, status=status, mode="set")
        antiswear_em = discord.Embed(
            title=f"{emoji.settings} Antiswear Settings",
            description=f"Successfully set antiswear status to **{status}**",
            color=db.theme_color
        )
        await ctx.respond(embed=antiswear_em)

def setup(client):
    client.add_cog(Settings(client))
