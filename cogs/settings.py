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
    async def settings(self, ctx: discord.ApplicationContext):
        """Shows server settings."""

        mod_channel = (await self.client.fetch_channel(db.mod_log_ch(ctx.guild.id))).mention if db.mod_log_ch(ctx.guild.id) != None else emoji.off
        mod_cmd_channel = (await self.client.fetch_channel(db.mod_cmd_log_ch(ctx.guild.id))).mention if db.mod_cmd_log_ch(ctx.guild.id) != None else emoji.off
        msg_channel = (await self.client.fetch_channel(db.msg_log_ch(ctx.guild.id))).mention if db.msg_log_ch(ctx.guild.id) != None else emoji.off
        ticket_cmds = emoji.on if db.ticket_cmds(ctx.guild.id) else emoji.off
        ticket_channel = (await self.client.fetch_channel(db.ticket_log_ch(ctx.guild.id))).mention if db.ticket_log_ch(ctx.guild.id) != None else emoji.off

        set_em = discord.Embed(
            title=f"{emoji.settings} {ctx.guild.name}'s Settings",
            description=f"{emoji.bullet} **Mod Log Channel**: {mod_channel}\n" +
                        f"{emoji.bullet} **Mod Command Log Channel**: {mod_cmd_channel}\n" +
                        f"{emoji.bullet} **Message Log Channel**: {msg_channel}\n" +
                        f"{emoji.bullet} **Ticket Commands**: {ticket_cmds}\n" +
                        f"{emoji.bullet} **Ticket Log Channel**: {ticket_channel}",
            color=db.theme_color
        )
        await ctx.respond(embed=set_em)

# Settings slash cmd group
    setting = SlashCommandGroup(guild_ids=db.guild_ids(), name="setting", description="Server settings commands.")

# Reset
    @setting.command(name="reset")
    @discord.default_permissions(manage_channels=True)
    @option("setting", description="Setting to reset", choices=["All", "Mod Log", "Mod Command Log", "Message Log", "Ticket Commands", "Ticket Log"])
    async def reset_settings(self, ctx: discord.ApplicationContext, setting: str):
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
                case "ticket commands":
                    db.ticket_cmds(guild_id=ctx.guild.id, mode="set", status=True)
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
    async def set_mod_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
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
    async def set_mod_cmd_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
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
    async def set_msg_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets message log channel."""
        db.msg_log_ch(guild_id=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Message Log Settings",
            description=f"Successfully set message log channel to {channel.mention}",
            color=db.theme_color
        )
        await ctx.respond(embed=logging_em)

# Set ticket cmds
    @setting.command(name="ticket-commands")
    @discord.default_permissions(manage_channels=True)
    @option("status", description="Enable or disable ticket commands", choices=["Enable", "Disable"])
    async def set_ticket_cmds(self, ctx: discord.ApplicationContext, status: str):
        """Enables or disables ticket commands."""
        match status.lower():
            case "enable":
                db.ticket_cmds(guild_id=ctx.guild.id, mode="set", status=True)
            case "disable":
                db.ticket_cmds(guild_id=ctx.guild.id, mode="set", status=False)
        ticket_cmds_em = discord.Embed(
            title=f"{emoji.settings} Ticket Commands Settings",
            description=f"Successfully {status.lower()}d ticket commands.",
            color=db.theme_color
        )
        await ctx.respond(embed=ticket_cmds_em)

# Set ticket log
    @setting.command(name="ticket-log")
    @discord.default_permissions(manage_channels=True)
    @option("channel", description="Mention the ticket log channel")
    async def set_ticket_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets ticket log channel."""
        db.ticket_log_ch(guild_id=ctx.guild.id, channel_id=int(channel.id), mode="set")
        logging_em = discord.Embed(
            title=f"{emoji.settings} Ticket Log Settings",
            description=f"Successfully set ticket log channel to {channel.mention}",
            color=db.theme_color
        )
        await ctx.respond(embed=logging_em)

def setup(client: discord.Client):
    client.add_cog(Settings(client))
