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

        mod_channel = (await self.client.fetch_channel(db.mod_log_ch(ctx.guild.id))).mention if db.mod_log_ch(ctx.guild.id) != None else "Not set"
        mod_cmd_channel = (await self.client.fetch_channel(db.mod_cmd_log_ch(ctx.guild.id))).mention if db.mod_cmd_log_ch(ctx.guild.id) != None else "Not set"
        msg_channel = (await self.client.fetch_channel(db.msg_log_ch(ctx.guild.id))).mention if db.msg_log_ch(ctx.guild.id) != None else "Not set"
        ticket_channel = (await self.client.fetch_channel(db.ticket_log_ch(ctx.guild.id))).mention if db.ticket_log_ch(ctx.guild.id) != None else "Not set"

        set_em = discord.Embed(
            title=f"{emoji.settings} {ctx.guild.name}'s Settings",
            description=f"{emoji.bullet} **Mod Log Channel**: {mod_channel}\n" +
                        f"{emoji.bullet} **Mod Command Log Channel**: {mod_cmd_channel}\n" +
                        f"{emoji.bullet} **Message Log Channel**: {msg_channel}\n" +
                        f"{emoji.bullet} **Ticket Log Channel**: {ticket_channel}",
            color=db.theme_color
        )
        await ctx.respond(embed=set_em)

# Settings slash cmd group
    setting = SlashCommandGroup(guild_ids=db.guild_ids(), name="setting", description="Server settings commands.")

# Reset
    @setting.command(name="reset")
    @discord.default_permissions(manage_channels=True)
    @option("setting", description="Setting to reset", choices=["All", "Mod Log", "Mod Command Log", "Message Log", "Ticket Log"])
    async def reset_settings(self, ctx, setting: str):
        """Resets server settings."""
        if setting.lower() == "all":
            db.delete(ctx.guild.id)
        else:
            match setting.lower():
                case "mod log":
                    db.mod_log_ch(guild_id=ctx.guild.id, mode="set", channel_id=None)
                case "mod command log":
                    db.mod_cmd_log_ch(guild_id=ctx.guild.id, mode="set", channel_id=None)
                case "message log":
                    db.msg_log_ch(guild_id=ctx.guild.id, mode="set", channel_id=None)
                case "ticket log":
                    db.ticket_log_ch(guild_id=ctx.guild.id, mode="set", channel_id=None)
        reset_em = discord.Embed(
            title=f"{emoji.settings} Reset Settings",
            description=f"Successfully reset the {setting.lower()} settings",
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

# Set message log
    @setting.command(name="message-log")
    @discord.default_permissions(manage_channels=True)
    @option("channel", description="Mention the message log channel")
    async def set_msg_log(self, ctx, channel: discord.TextChannel):
        """Sets message log channel."""
        db.msg_log_ch(guild_id=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Message Log Settings",
            description=f"Successfully set message log channel to {channel.mention}",
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

def setup(client):
    client.add_cog(Settings(client))
