import discord
from utils import database as db, emoji
from discord.ext import commands
from discord.commands import slash_command, Option

class Settings(commands.Cog):
    def __init__(self, client):
        self.client = client

# Settings
    @slash_command(guild_ids=db.guild_ids(), name="settings")
    @discord.default_permissions(manage_channels=True)
    async def settings(self, ctx):
        """Shows server settings"""
        if db.mod_log_channel_id(ctx.guild.id) != None:
            mod_log_channel = await self.client.fetch_channel(db.mod_log_channel_id(ctx.guild.id))
            mod_log_channel_mention = mod_log_channel.mention
        else:
            mod_log_channel_mention = None
        if db.warn_log_channel_id(ctx.guild.id) != None:
            warn_log_channel = await self.client.fetch_channel(db.warn_log_channel_id(ctx.guild.id))
            warn_log_channel_mention = warn_log_channel.mention
        else:
            warn_log_channel_mention = None

        if db.ticket_log_channel_id(ctx.guild.id) != None:
            ticket_log_channel = await self.client.fetch_channel(db.ticket_log_channel_id(ctx.guild.id))
            ticket_log_channel_mention = ticket_log_channel.mention
        else:
            ticket_log_channel_mention = None

        set_em = discord.Embed(
            title=f"{emoji.settings} {ctx.guild.name}'s Settings",
            description=f"{emoji.bullet} **Mod Log Channel**: {mod_log_channel_mention}\n" +
                        f"{emoji.bullet} **Warn Log Channel**: {warn_log_channel_mention}\n" +
                        f"{emoji.bullet} **Ticket Log Channel**: {ticket_log_channel_mention}\n" +
                        f"{emoji.bullet} **Antilink**: {db.antilink(ctx.guild.id)}\n" +
                        f"{emoji.bullet} **Antiswear**: {db.antiswear(ctx.guild.id)}",
            color=db.theme_color
        )
        await ctx.respond(embed=set_em)

# Set mod log
    @slash_command(guild_ids=db.guild_ids(), name="set-mod-log-channel")
    @discord.default_permissions(manage_channels=True)
    async def set_mod_log(
        self, ctx,
        channel: Option(discord.TextChannel, "Mention the mod log channel")
    ):
        """Sets mod log channel"""
        db.mod_log_channel_id(guild_ids=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Mod Log Settings",
            description=f"Successfully set mod log channel to {channel.mention}",
            color=db.theme_color
        )
        await ctx.respond(embed=logging_em)

# Set warn log
    @slash_command(guild_ids=db.guild_ids(), name="set-warn-log-channel")
    @discord.default_permissions(manage_channels=True)
    async def set_warn_log(
        self, ctx,
        channel: Option(discord.TextChannel, "Mention the warn log channel")
    ):
        """Sets warn log channel"""
        db.warn_log_channel_id(guild_ids=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Warn Log Settings",
            description=f"Successfully set warn log channel to {channel.mention}",
            color=db.theme_color
        )
        await ctx.respond(embed=logging_em)

# Set ticket log
    @slash_command(guild_ids=db.guild_ids(), name="set-ticket-log-channel")
    @discord.default_permissions(manage_channels=True)
    async def set_ticket_log(
        self, ctx,
        channel: Option(discord.TextChannel, "Mention the ticket log channel")
    ):
        """Sets ticket log channel"""
        db.ticket_log_channel_id(guild_ids=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Ticket Log Settings",
            description=f"Successfully set ticket log channel to {channel.mention}",
            color=db.theme_color
        )
        await ctx.respond(embed=logging_em)

# Set antilink
    @slash_command(guild_ids=db.guild_ids(), name="set-antilink")
    @discord.default_permissions(manage_channels=True)
    async def set_antilink(
        self, ctx,
        status: Option(str, "Choose the antilink status", choices=["ON", "OFF"])
    ):
        """Sets antilink"""
        db.antilink(guild_ids=ctx.guild.id, status=status, mode="set")
        anitlink_em = discord.Embed(
            title=f"{emoji.settings} Antilink Settings",
            description=f"Successfully set antilink status to **{status}**",
            color=db.theme_color
        )
        await ctx.respond(embed=anitlink_em)

# Set antiswear
    @slash_command(guild_ids=db.guild_ids(), name="set-antiswear")
    @discord.default_permissions(manage_channels=True)
    async def setAntiswear(
        self, ctx,
        status: Option(str, "Choose the antiswear status", choices=["ON", "OFF"])
    ):
        """Sets antiswear"""
        db.antiswear(guild_ids=ctx.guild.id, status=status, mode="set")
        antiswear_em = discord.Embed(
            title=f"{emoji.settings} Antiswear Settings",
            description=f"Successfully set antiswear status to **{status}**",
            color=db.theme_color
        )
        await ctx.respond(embed=antiswear_em)

def setup(client):
    client.add_cog(Settings(client))
