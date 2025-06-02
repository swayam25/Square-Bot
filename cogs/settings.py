import discord
from db.funcs.guild import (
    fetch_guild_settings,
    remove_guild,
    set_autorole,
    set_mod_cmd_log_channel,
    set_mod_log_channel,
    set_msg_log_channel,
    set_ticket_cmds,
    set_ticket_log_channel,
)
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from utils import config
from utils.emoji import emoji


class Settings(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client = client

    # Settings
    @slash_command(name="settings")
    @discord.default_permissions(manage_channels=True)
    async def settings(self, ctx: discord.ApplicationContext):
        """Shows server settings."""

        # Fetch channel mention util func
        async def mention_ch(channel_id):
            return f"<#{channel_id}>" if channel_id else emoji.off

        guild_settings = await fetch_guild_settings(ctx.guild.id)

        mod_log_channel = await mention_ch(guild_settings.mod_log_channel_id)
        mod_log_cmd_channel = await mention_ch(guild_settings.mod_cmd_log_channel_id)
        msg_log_channel = await mention_ch(guild_settings.msg_log_channel_id)
        ticket = emoji.on if guild_settings.ticket_cmds else emoji.off
        ticket_log_channel = await mention_ch(guild_settings.ticket_log_channel_id)

        role_id = guild_settings.autorole
        autorole = ctx.guild.get_role(role_id).mention if (role_id and ctx.guild.get_role(role_id)) else emoji.off
        if role_id and not ctx.guild.get_role(role_id):
            await set_autorole(ctx.guild.id, None)  # Reset autorole if role doesn't exist

        set_em = discord.Embed(
            title=f"{emoji.settings} {ctx.guild.name}'s Settings",
            description=f"{emoji.bullet} **Mod Log Channel**: {mod_log_channel}\n"
            + f"{emoji.bullet} **Mod Command Log Channel**: {mod_log_cmd_channel}\n"
            + f"{emoji.bullet} **Message Log Channel**: {msg_log_channel}\n"
            + f"{emoji.bullet} **Ticket Commands**: {ticket}\n"
            + f"{emoji.bullet} **Ticket Log Channel**: {ticket_log_channel}\n"
            + f"{emoji.bullet} **Autorole**: {autorole}",
            color=config.color.theme,
        )
        await ctx.respond(embed=set_em)

    # Settings slash cmd group
    setting = SlashCommandGroup(
        name="setting",
        description="Server settings commands.",
        default_member_permissions=discord.Permissions(manage_channels=True, moderate_members=True),
    )

    # Reset
    @setting.command(name="reset")
    @option(
        "setting",
        description="Setting to reset",
        choices=["All", "Mod Log", "Mod Command Log", "Message Log", "Ticket Commands", "Ticket Log", "Auto Role"],
    )
    async def reset_settings(self, ctx: discord.ApplicationContext, setting: str):
        """Resets server settings."""
        if setting.lower() == "all":
            await remove_guild(ctx.guild.id)
        else:
            match setting.lower():
                case "mod log":
                    await set_mod_cmd_log_channel(ctx.guild.id, None)
                case "mod command log":
                    await set_mod_cmd_log_channel(ctx.guild.id, None)
                case "message log":
                    await set_msg_log_channel(ctx.guild.id, None)
                case "ticket commands":
                    await set_ticket_cmds(ctx.guild.id, False)
                case "ticket log":
                    await set_ticket_log_channel(ctx.guild.id, None)
                case "auto role":
                    await set_autorole(ctx.guild.id, None)
        reset_em = discord.Embed(
            title=f"{emoji.settings} Reset Settings",
            description=f"Successfully reset the {setting.lower()} settings.",
            color=config.color.theme,
        )
        await ctx.respond(embed=reset_em)

    # Set mod log
    @setting.command(name="mod-log")
    @option("channel", description="Mention the mod log channel")
    async def set_mod_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets mod log channel."""
        await set_mod_log_channel(ctx.guild.id, channel.id)
        logging_em = discord.Embed(
            title=f"{emoji.settings} Mod Log Settings",
            description=f"Successfully set mod log channel to {channel.mention}.",
            color=config.color.theme,
        )
        await ctx.respond(embed=logging_em)

    # Set mod cmd log
    @setting.command(name="mod-command-log")
    @option("channel", description="Mention the mod command log channel")
    async def set_mod_cmd_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets mod command log channel."""
        await set_mod_cmd_log_channel(ctx.guild.id, channel.id)
        logging_em = discord.Embed(
            title=f"{emoji.settings} Mod Command Log Settings",
            description=f"Successfully set mod command log channel to {channel.mention}.",
            color=config.color.theme,
        )
        await ctx.respond(embed=logging_em)

    # Set message log
    @setting.command(name="message-log")
    @option("channel", description="Mention the message log channel")
    async def set_msg_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets message log channel."""
        await set_msg_log_channel(ctx.guild.id, channel.id)
        logging_em = discord.Embed(
            title=f"{emoji.settings} Message Log Settings",
            description=f"Successfully set message log channel to {channel.mention}.",
            color=config.color.theme,
        )
        await ctx.respond(embed=logging_em)

    # Set ticket cmds
    @setting.command(name="ticket-commands")
    @option("status", description="Enable or disable ticket commands", choices=["Enable", "Disable"])
    async def set_ticket_cmds(self, ctx: discord.ApplicationContext, status: str):
        """Enables or disables ticket commands."""
        match status.lower():
            case "enable":
                await set_ticket_cmds(ctx.guild.id, True)
            case "disable":
                await set_ticket_cmds(ctx.guild.id, False)
        ticket_cmds_em = discord.Embed(
            title=f"{emoji.settings} Ticket Commands Settings",
            description=f"Successfully {status.lower()}d ticket commands.",
            color=config.color.theme,
        )
        await ctx.respond(embed=ticket_cmds_em)

    # Set ticket log
    @setting.command(name="ticket-log")
    @option("channel", description="Mention the ticket log channel")
    async def set_ticket_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets ticket log channel."""
        await set_ticket_log_channel(ctx.guild.id, channel.id)
        logging_em = discord.Embed(
            title=f"{emoji.settings} Ticket Log Settings",
            description=f"Successfully set ticket log channel to {channel.mention}.",
            color=config.color.theme,
        )
        await ctx.respond(embed=logging_em)

    # Set autorole
    @setting.command(name="auto-role")
    @option("role", description="Mention the autorole")
    async def set_auto_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Sets autorole. The bot will assign this role to new members."""
        if role >= ctx.guild.me.top_role:
            error_em = discord.Embed(
                description=f"{emoji.error} I can't assign roles higher than my top role.", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        elif role.name == "@everyone":
            error_em = discord.Embed(
                description=f"{emoji.error} I can't assign the @everyone role.", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            await set_autorole(ctx.guild.id, role.id)
            autorole_em = discord.Embed(
                title=f"{emoji.settings} Auto Role Settings",
                description=f"Successfully set autorole to {role.mention}.",
                color=config.color.theme,
            )
            await ctx.respond(embed=autorole_em)


def setup(client: discord.Bot):
    client.add_cog(Settings(client))
