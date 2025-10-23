import datetime
import discord
from babel.dates import format_timedelta
from core import Client
from core.view import DesignerView
from discord import ui
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from utils import config
from utils.emoji import emoji
from utils.helpers import parse_duration


class Moderation(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # Purge slash cmd group
    purge = SlashCommandGroup(
        name="purge",
        description="Purge related commands.",
        default_member_permissions=discord.Permissions(manage_messages=True),
    )

    # Purge any
    @purge.command(name="any")
    @option("amount", description="Enter an integer.", min_value=1, max_value=1000)
    async def purge_any(self, ctx: discord.ApplicationContext, amount: int):
        """Purges the amount of given messages."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Amount must be."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully purged `{amount}` messages."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Purge humans
    @purge.command(name="humans")
    @option("amount", description="Enter an integer.", min_value=1, max_value=1000)
    async def purge_humans(self, ctx: discord.ApplicationContext, amount: int):
        """Purges the amount of given messages sent by humans."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Amount must be."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount, check=lambda m: not m.author.bot)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully purged `{amount}` messages sent by humans"),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Purge bots
    @purge.command(name="bots")
    @option("amount", description="Enter an integer.", min_value=1, max_value=1000)
    async def purge_bots(self, ctx: discord.ApplicationContext, amount: int):
        """Purges the amount of given messages sent by bots."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Amount must be."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount, check=lambda m: m.author.bot)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully purged `{amount}` messages sent by bots"),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Purge user
    @purge.command(name="user")
    @option("amount", description="Enter an integer.", min_value=1, max_value=1000)
    @option("user", description="Mention the user whose messages you want to purge.")
    async def purge_user(self, ctx: discord.ApplicationContext, amount: int, user: discord.Member):
        """Purges the amount of given messages sent by the mentioned user."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Amount must be."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount, check=lambda m: m.author.id == user.id)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully purged `{amount}` messages sent by {user.mention}"),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Purge containing phrase
    @purge.command(name="contains")
    @option("amount", description="Enter an integer.", min_value=1, max_value=1000)
    @option("phrase", description="Enter the phrase to purge messages containing it.")
    async def purge_contains(self, ctx: discord.ApplicationContext, amount: int, phrase: str):
        """Purges the amount of given messages containing the given phrase."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Amount must be."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount, check=lambda m: phrase.lower() in m.content.lower())
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully purged `{amount}` messages containing `{phrase}`"),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Purge after
    @purge.command(name="after")
    @option("message_id", description="Enter the message ID after which you want to purge messages.")
    @option("amount", description="Enter an integer.", min_value=1, max_value=1000, required=False)
    async def purge_after(self, ctx: discord.ApplicationContext, message_id: str, amount: int = 1000):
        """Purges the amount of given messages after the given message ID."""
        amount_condition = [amount < 1, amount > 1000]
        if not message_id.isdigit():
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Message ID must be a valid integer."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        message_id = int(
            message_id
        )  # Discord uses Javascript and Python have different integer sizes, so we convert it to int.
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Amount must be."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            try:
                message = await ctx.channel.fetch_message(message_id)
                await ctx.channel.purge(limit=amount, check=lambda m: m.id > message.id)
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(
                            f"{emoji.success} Successfully purged `{amount}` messages after `{message.id}`."
                        ),
                        color=config.color.green,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
            except discord.NotFound:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.error} Message with ID `{message_id}` not found."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    # Kick
    @slash_command(name="kick")
    @discord.default_permissions(kick_members=True)
    @option("user", description="Mention the user whom you want to kick")
    @option("reason", description="Enter the reason for kicking the user", required=False)
    async def kick(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str = None):
        """Kicks the mentioned user."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif isinstance(user, discord.Member) and user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await user.kick(reason=reason)
            view = DesignerView(
                ui.Container(
                    ui.Section(
                        ui.TextDisplay("## Kicked User"),
                        ui.TextDisplay(
                            f"Successfully kicked **{user}** from the server.\n{emoji.description_red} **Reason**: {reason}"
                        ),
                        accessory=ui.Thumbnail(url=user.display_avatar.url),
                    ),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view)

    # Ban
    @slash_command(name="ban")
    @discord.default_permissions(ban_members=True)
    @option("user", description="Mention the user whom you want to ban.")
    @option(
        "delete_messages",
        description="Enter the duration of messages to delete. Ex: 1m, 2h, 7d (default), 0 (disable) etc...",
        required=False,
    )
    @option("reason", description="Enter the reason for banning the user.", required=False)
    async def ban(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        delete_messages: str = "7d",
        reason: str = None,
    ):
        """Bans the a user from the server."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif isinstance(user, discord.Member) and user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            dur, del_after = None, None
            if delete_messages and delete_messages != "0":
                del_after = parse_duration(delete_messages, max_duration="7d")
                dur = int(del_after.total_seconds()) if del_after else None
            await ctx.guild.ban(user, reason=reason, delete_message_seconds=dur)
            view = DesignerView(
                ui.Container(
                    ui.Section(
                        ui.TextDisplay("## Banned User"),
                        ui.TextDisplay(
                            f"Successfully banned **{user.display_name}** from the server.\n"
                            f"{emoji.id_red} **ID**: `{user.id}`\n"
                            f"{emoji.user_red} **User**: `{user}`\n"
                            f"{emoji.description_red} **Reason**: {reason}\n"
                            f"{emoji.bin_red} **Delete Message Duration**: `{format_timedelta(del_after)}`"
                        ),
                        accessory=ui.Thumbnail(url=user.display_avatar.url),
                    ),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view)

    # Unban user
    @slash_command(name="unban")
    @discord.default_permissions(ban_members=True)
    @option("user_id", description="Enter the user ID whom you want to unban")
    @option("reason", description="Enter the reason for unbanning the user", required=False)
    async def unban(self, ctx: discord.ApplicationContext, user_id: str, reason: str = None):
        """Unbans the user with the given ID."""
        if not user_id.isdigit():
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} User ID must be a valid integer."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        user_id = int(user_id)
        try:
            user = await self.client.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Successfully unbanned {user.mention}."),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)
        except discord.NotFound:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} User with ID `{user_id}` not found."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Timeout user
    @slash_command(name="timeout")
    @discord.default_permissions(moderate_members=True)
    @option("user", description="Mention the user whom you want to timeout")
    @option("duration", description="Enter the duration of timeout. Ex: 1d, 2w etc...")
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def timeout_user(
        self, ctx: discord.ApplicationContext, user: discord.Member, duration: str, reason: str = None
    ):
        """Timeouts the mentioned user."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            try:
                dur: datetime.timedelta = parse_duration(duration)
            except ValueError as e:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.error} {e}"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
                return
            await user.timeout_for(dur, reason=reason)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Timed out User"),
                    ui.TextDisplay(
                        f"Successfully timed out {user.mention}.\n"
                        f"{emoji.duration} **Duration**: `{format_timedelta(dur)}`\n"
                        f"{emoji.description} **Reason**: {reason}"
                    ),
                )
            )
            await ctx.respond(view=view)

    # Untimeout user
    @slash_command(name="untimeout")
    @discord.default_permissions(moderate_members=True)
    @option("user", description="Mention the user whom you want to untimeout")
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def untimeout_user(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str = None):
        """Untimeouts the mentioned user."""
        if user == ctx.author:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} You cannot use it on yourself"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await user.timeout(None, reason=reason)
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Untimed out User"),
                    ui.TextDisplay(
                        f"Successfully untimed out {user.mention}.\n{emoji.description} **Reason**: {reason}"
                    ),
                )
            )
            await ctx.respond(view=view)

    # Lock
    @slash_command(name="lock")
    @discord.default_permissions(manage_channels=True)
    @option("reason", description="Enter the reason for locking the channel", required=False)
    async def lock(self, ctx: discord.ApplicationContext, reason: str = None):
        """Locks the current channel."""
        await ctx.channel.set_permissions(ctx.author, send_messages=True)
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Channel Locked"),
                ui.TextDisplay(f"Successfully locked {ctx.channel.mention}.\n{emoji.description} **Reason**: {reason}"),
            )
        )
        await ctx.respond(view=view)

    # Unlock
    @slash_command(name="unlock")
    @discord.default_permissions(manage_channels=True)
    async def unlock(self, ctx: discord.ApplicationContext):
        """Unlocks the current channel."""
        await ctx.channel.set_permissions(ctx.author, send_messages=True)
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"{emoji.success} Successfully unlocked {ctx.channel.mention}.",
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Role slash cmd group
    role = SlashCommandGroup(
        name="role",
        description="Role related commands.",
        default_member_permissions=discord.Permissions(manage_roles=True),
    )

    # Role add
    @role.command(name="add")
    @option("user", description="Mention the user whom you want to add the role")
    @option("role", description="Mention the role which you will add to the user")
    async def add_role(self, ctx: discord.ApplicationContext, user: discord.Member, role: discord.Role):
        """Adds the mentioned role to the mentioned user."""
        if user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        if role.position >= ctx.guild.me.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given role position is same or higher than my role."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        await user.add_roles(role)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"{emoji.success} Successfully added {role.mention} to {user.mention}.",
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Remove role
    @role.command(name="remove")
    @option("user", description="Mention the user whom you want to remove the role")
    @option("role", description="Mention the role which you will remove from the user")
    async def remove_role(self, ctx: discord.ApplicationContext, user: discord.Member, role: discord.Role):
        """Removes the mentioned role from the mentioned user."""
        if user.top_role.position >= ctx.author.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given user has same role or higher role than you."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        if role.position >= ctx.guild.me.top_role.position:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Given role position is same or higher than my role."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        await user.remove_roles(role)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"{emoji.success} Successfully removed {role.mention} from {user.mention}.",
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)


def setup(client: Client):
    client.add_cog(Moderation(client))
