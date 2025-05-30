import discord
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from utils import database as db
from utils.emoji import emoji


class Settings(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client = client

    # Settings
    @slash_command(guild_ids=db.guild_ids(), name="settings")
    @discord.default_permissions(manage_channels=True)
    async def settings(self, ctx: discord.ApplicationContext):
        """Shows server settings."""

        # Fetch channel mention util func
        async def fetch_channel_mention(channel_id):
            return (await self.client.fetch_channel(channel_id)).mention if channel_id else emoji.off

        mod_channel = await fetch_channel_mention(db.mod_log_ch(ctx.guild.id))
        mod_cmd_channel = await fetch_channel_mention(db.mod_cmd_log_ch(ctx.guild.id))
        msg_channel = await fetch_channel_mention(db.msg_log_ch(ctx.guild.id))
        ticket_cmds = emoji.on if db.ticket_cmds(ctx.guild.id) else emoji.off
        ticket_channel = await fetch_channel_mention(db.ticket_log_ch(ctx.guild.id))

        role_id = db.autorole(ctx.guild.id)
        autorole = ctx.guild.get_role(role_id).mention if (role_id and ctx.guild.get_role(role_id)) else emoji.off
        if role_id and not ctx.guild.get_role(role_id):
            db.autorole(ctx.guild.id, None, "set")

        set_em = discord.Embed(
            title=f"{emoji.settings} {ctx.guild.name}'s Settings",
            description=f"{emoji.bullet} **Mod Log Channel**: {mod_channel}\n"
            + f"{emoji.bullet} **Mod Command Log Channel**: {mod_cmd_channel}\n"
            + f"{emoji.bullet} **Message Log Channel**: {msg_channel}\n"
            + f"{emoji.bullet} **Ticket Commands**: {ticket_cmds}\n"
            + f"{emoji.bullet} **Ticket Log Channel**: {ticket_channel}\n"
            + f"{emoji.bullet} **Autorole**: {autorole}",
            color=db.theme_color,
        )
        await ctx.respond(embed=set_em)

    # Settings slash cmd group
    setting = SlashCommandGroup(guild_ids=db.guild_ids(), name="setting", description="Server settings commands.")

    # Reset
    @setting.command(name="reset")
    @discord.default_permissions(manage_channels=True)
    @option(
        "setting",
        description="Setting to reset",
        choices=["All", "Mod Log", "Mod Command Log", "Message Log", "Ticket Commands", "Ticket Log", "Auto Role"],
    )
    async def reset_settings(self, ctx: discord.ApplicationContext, setting: str):
        """Resets server settings."""
        if setting.lower() == "all":
            db.delete(ctx.guild.id)
        else:
            match setting.lower():
                case "mod log":
                    db.mod_log_ch(guild_id=ctx.guild.id, channel_id=None, mode="set")
                case "mod command log":
                    db.mod_cmd_log_ch(guild_id=ctx.guild.id, channel_id=None, mode="set")
                case "message log":
                    db.msg_log_ch(guild_id=ctx.guild.id, channel_id=None, mode="set")
                case "ticket commands":
                    db.ticket_cmds(guild_id=ctx.guild.id, status=True, mode="set")
                case "ticket log":
                    db.ticket_log_ch(guild_id=ctx.guild.id, channel_id=None, mode="set")
                case "auto role":
                    db.autorole(guild_id=ctx.guild.id, role_id=None, mode="set")
        reset_em = discord.Embed(
            title=f"{emoji.settings} Reset Settings",
            description=f"Successfully reset the {setting.lower()} settings.",
            color=db.theme_color,
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
            description=f"Successfully set mod log channel to {channel.mention}.",
            color=db.theme_color,
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
            description=f"Successfully set mod command log channel to {channel.mention}.",
            color=db.theme_color,
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
            description=f"Successfully set message log channel to {channel.mention}.",
            color=db.theme_color,
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
                db.ticket_cmds(guild_id=ctx.guild.id, status=True, mode="set")
            case "disable":
                db.ticket_cmds(guild_id=ctx.guild.id, status=False, mode="set")
        ticket_cmds_em = discord.Embed(
            title=f"{emoji.settings} Ticket Commands Settings",
            description=f"Successfully {status.lower()}d ticket commands.",
            color=db.theme_color,
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
            description=f"Successfully set ticket log channel to {channel.mention}.",
            color=db.theme_color,
        )
        await ctx.respond(embed=logging_em)

    # Set autorole
    @setting.command(name="auto-role")
    @discord.default_permissions(moderate_members=True, manage_roles=True)
    @option("role", description="Mention the autorole")
    async def set_auto_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Sets autorole. The bot will assign this role to new members."""
        if role >= ctx.guild.me.top_role:
            error_em = discord.Embed(
                description=f"{emoji.error} I can't assign roles higher than my top role.", color=db.error_color
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        elif role.name == "@everyone":
            error_em = discord.Embed(
                description=f"{emoji.error} I can't assign the @everyone role.", color=db.error_color
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            db.autorole(guild_id=ctx.guild.id, role_id=int(role.id), mode="set")
            autorole_em = discord.Embed(
                title=f"{emoji.settings} Auto Role Settings",
                description=f"Successfully set autorole to {role.mention}.",
                color=db.theme_color,
            )
            await ctx.respond(embed=autorole_em)


def setup(client: discord.Bot):
    client.add_cog(Settings(client))
