import discord
from db.funcs.guild import (
    fetch_guild_settings,
    remove_guild,
    set_auto_meme,
    set_autorole,
    set_media_only,
    set_mod_cmd_log,
    set_mod_log,
    set_msg_log,
    set_ticket_cmds,
    set_ticket_log,
)
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from utils import config
from utils.check import check_subreddit
from utils.emoji import emoji
from utils.view import View


class Settings(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client = client

    # Settings
    @slash_command(name="settings")
    @discord.default_permissions(manage_channels=True)
    async def settings(self, ctx: discord.ApplicationContext):
        """Shows server settings."""

        # Fetch channel mention util func
        async def mention_ch(channel_id: int | None) -> str:
            return f"<#{channel_id}>" if channel_id else emoji.off

        guild_settings = await fetch_guild_settings(ctx.guild.id)

        mod_log_channel = await mention_ch(guild_settings.mod_log_channel_id)
        mod_log_cmd_channel = await mention_ch(guild_settings.mod_cmd_log_channel_id)
        msg_log_channel = await mention_ch(guild_settings.msg_log_channel_id)
        ticket = emoji.on if guild_settings.ticket_cmds else emoji.off
        ticket_log_channel = await mention_ch(guild_settings.ticket_log_channel_id)
        media_only_channel = await mention_ch(guild_settings.media_only_channel_id)
        auto_meme_channel = await mention_ch(guild_settings.auto_meme["channel_id"])
        if guild_settings.auto_meme["subreddit"]:
            auto_meme_channel += f" ([`r/{guild_settings.auto_meme['subreddit']}`](https://reddit.com/r/{guild_settings.auto_meme['subreddit']}))"

        role_id = guild_settings.autorole
        autorole = ctx.guild.get_role(role_id).mention if (role_id and ctx.guild.get_role(role_id)) else emoji.off
        if role_id and not ctx.guild.get_role(role_id):
            await set_autorole(ctx.guild.id, None)  # Reset autorole if role doesn't exist

        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"## {ctx.guild.name}'s Settings"),
                discord.ui.TextDisplay(
                    f"{emoji.mod} **Mod Log Channel**: {mod_log_channel}\n"
                    f"{emoji.owner} **Mod Command Log Channel**: {mod_log_cmd_channel}\n"
                    f"{emoji.msg} **Message Log Channel**: {msg_log_channel}\n"
                    f"{emoji.ticket} **Ticket Commands**: {ticket}\n"
                    f"{emoji.ticket} **Ticket Log Channel**: {ticket_log_channel}\n"
                    f"{emoji.img} **Media Only Channel**: {media_only_channel}\n"
                    f"{emoji.role} **Autorole**: {autorole}\n"
                    f"{emoji.fun} **Auto Meme Channel**: {auto_meme_channel}\n"
                ),
            )
        )
        await ctx.respond(view=view)

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
        choices=[
            "All",
            "Mod Log",
            "Mod Command Log",
            "Message Log",
            "Ticket Commands",
            "Ticket Log",
            "Media Only",
            "Auto Role",
            "Auto Meme",
        ],
    )
    async def reset_settings(self, ctx: discord.ApplicationContext, setting: str):
        """Resets server settings."""
        if setting.lower() == "all":
            await remove_guild(ctx.guild.id)
        else:
            match setting.lower():
                case "mod log":
                    await set_mod_log(ctx.guild.id, None)
                case "mod command log":
                    await set_mod_cmd_log(ctx.guild.id, None)
                case "message log":
                    await set_msg_log(ctx.guild.id, None)
                case "ticket commands":
                    await set_ticket_cmds(ctx.guild.id, False)
                case "ticket log":
                    await set_ticket_log(ctx.guild.id, None)
                case "media only":
                    await set_media_only(ctx.guild.id, None)
                case "auto role":
                    await set_autorole(ctx.guild.id, None)
                case "auto meme":
                    await set_auto_meme(ctx.guild.id, None)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Successfully reset the {setting.lower()} settings."),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Set mod log
    @setting.command(name="mod-log")
    @option("channel", description="Mention the mod log channel")
    async def set_mod_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets mod log channel."""
        await set_mod_log(ctx.guild.id, channel.id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Successfully set mod log channel to {channel.mention}."),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Set mod cmd log
    @setting.command(name="mod-command-log")
    @option("channel", description="Mention the mod command log channel")
    async def set_mod_cmd_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets mod command log channel."""
        await set_mod_cmd_log(ctx.guild.id, channel.id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    f"{emoji.success} Successfully set mod command log channel to {channel.mention}."
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Set message log
    @setting.command(name="message-log")
    @option("channel", description="Mention the message log channel")
    async def set_msg_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets message log channel."""
        await set_msg_log(ctx.guild.id, channel.id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Successfully set message log channel to {channel.mention}."),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

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
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Successfully {status.lower()}d ticket commands."),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Set ticket log
    @setting.command(name="ticket-log")
    @option("channel", description="Mention the ticket log channel")
    async def set_ticket_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets ticket log channel."""
        await set_ticket_log(ctx.guild.id, channel.id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Successfully set ticket log channel to {channel.mention}."),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Set media only channel
    @setting.command(name="media-only")
    @option("channel", description="Mention the media only channel")
    async def set_image_only(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Sets media only channel."""
        if not channel.permissions_for(ctx.guild.me).send_messages:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.error} I don't have permission to send messages in {channel.mention}."
                    ),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await set_media_only(ctx.guild.id, channel.id)
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.success} Successfully set media only channel to {channel.mention}."
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Set autorole
    @setting.command(name="auto-role")
    @option("role", description="Mention the autorole")
    async def set_auto_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Sets autorole. The bot will assign this role to new members."""
        if role >= ctx.guild.me.top_role:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} I can't assign roles higher than my top role."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif role.name == "@everyone":
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} I can't assign the @everyone role."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await set_autorole(ctx.guild.id, role.id)
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.success} Successfully set autorole to {role.mention}.\n-# This role will be assigned to members when they join the server."
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    # Set auto meme
    @setting.command(name="auto-meme")
    @option("channel", description="Mention the auto meme channel.")
    @option("subreddit", description="Subreddit to fetch memes from.", required=False)
    async def set_auto_meme(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, subreddit: str = ""):
        """Sets auto meme channel. Posts memes every 10 minutes."""
        if not channel.permissions_for(ctx.guild.me).send_messages:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.error} I don't have permission to send messages in {channel.mention}."
                    ),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            if subreddit:  # Check if subreddit is provided
                await ctx.defer()
                check = await check_subreddit(subreddit)
                if not check.exist:  # If subreddit is invalid
                    view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay(
                                f"{emoji.error} The subreddit `r/{check.display_name}` does not exist or is invalid."
                            ),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view, ephemeral=True)
                    return
                # Use the display name from the check so that it is formatted correctly
                if check.nsfw and not channel.nsfw:  # If subreddit is NSFW and channel is not NSFW
                    view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay(
                                f"{emoji.error} The subreddit `r/{check.display_name}` is **NSFW**. Please enable **NSFW** in {channel.mention} or choose a different subreddit."
                            ),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view, ephemeral=True)
                    return
            # Finally set the auto meme channel and subreddit
            await set_auto_meme(ctx.guild.id, channel.id, check.display_name if subreddit else None)
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.success} Successfully set auto meme channel to {channel.mention}{f' and subreddit to [`r/{check.display_name}`](https://reddit.com/r/{check.display_name})' if subreddit else ''}.\n"
                        f"-# The bot will post memes every `10 minutes`.\n"
                        f"-# Technically you can use any subreddit, but it is recommended to use subreddits that have memes."
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)


def setup(client: discord.Bot):
    client.add_cog(Settings(client))
