import datetime
import discord
from babel.dates import format_timedelta
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from utils import config
from utils.emoji import emoji
from utils.helpers import parse_duration


class Moderation(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Purge slash cmd group
    purge = SlashCommandGroup(
        name="purge",
        description="Purge related commands.",
        default_member_permissions=discord.Permissions(manage_messages=True),
    )

    # Purge any
    @purge.command(name="any")
    @option("amount", description="Enter an integer between 1 to 1000.")
    async def purge_any(self, ctx: discord.ApplicationContext, amount: int):
        """Purges the amount of given messages."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            error_em = discord.Embed(
                description=f"{emoji.error} Amount must be between 1 to 1000.", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount)
            purge_em = discord.Embed(
                title=f"{emoji.bin} Messages Purged",
                description=f"Successfully purged `{amount}` message(s)",
                color=config.color.theme,
            )
            await ctx.respond(embed=purge_em, ephemeral=True)

    # Purge humans
    @purge.command(name="humans")
    @option("amount", description="Enter an integer between 1 to 1000.")
    async def purge_humans(self, ctx: discord.ApplicationContext, amount: int):
        """Purges the amount of given messages sent by humans."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            error_em = discord.Embed(
                description=f"{emoji.error} Amount must be between 1 to 1000.", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount, check=lambda m: not m.author.bot)
            purge_em = discord.Embed(
                title=f"{emoji.bin} Messages Purged",
                description=f"Successfully purged `{amount}` message(s) sent by humans",
                color=config.color.theme,
            )
            await ctx.respond(embed=purge_em, ephemeral=True)

    # Purge bots
    @purge.command(name="bots")
    @option("amount", description="Enter an integer between 1 to 1000.")
    async def purge_bots(self, ctx: discord.ApplicationContext, amount: int):
        """Purges the amount of given messages sent by bots."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            error_em = discord.Embed(
                description=f"{emoji.error} Amount must be between 1 to 1000.", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount, check=lambda m: m.author.bot)
            purge_em = discord.Embed(
                title=f"{emoji.bin} Messages Purged",
                description=f"Successfully purged `{amount}` message(s) sent by bots",
                color=config.color.theme,
            )
            await ctx.respond(embed=purge_em, ephemeral=True)

    # Purge user
    @purge.command(name="user")
    @option("amount", description="Enter an integer between 1 to 1000.")
    @option("user", description="Mention the user whose messages you want to purge.")
    async def purge_user(self, ctx: discord.ApplicationContext, amount: int, user: discord.Member):
        """Purges the amount of given messages sent by the mentioned user."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            error_em = discord.Embed(
                description=f"{emoji.error} Amount must be between 1 to 1000.", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount, check=lambda m: m.author.id == user.id)
            purge_em = discord.Embed(
                title=f"{emoji.bin} Messages Purged",
                description=f"Successfully purged `{amount}` message(s) sent by {user.mention}",
                color=config.color.theme,
            )
            await ctx.respond(embed=purge_em, ephemeral=True)

    # Purge containing phrase
    @purge.command(name="contains")
    @option("amount", description="Enter an integer between 1 to 1000.")
    @option("phrase", description="Enter the phrase to purge messages containing it.")
    async def purge_contains(self, ctx: discord.ApplicationContext, amount: int, phrase: str):
        """Purges the amount of given messages containing the given phrase."""
        amount_condition = [amount < 1, amount > 1000]
        await ctx.defer(ephemeral=True)
        if any(amount_condition):
            error_em = discord.Embed(
                description=f"{emoji.error} Amount must be between 1 to 1000.", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            await ctx.channel.purge(limit=amount, check=lambda m: phrase.lower() in m.content.lower())
            purge_em = discord.Embed(
                title=f"{emoji.bin} Messages Purged",
                description=f"Successfully purged `{amount}` message(s) containing `{phrase}`",
                color=config.color.theme,
            )
            await ctx.respond(embed=purge_em, ephemeral=True)

    # Kick
    @slash_command(name="kick")
    @discord.default_permissions(kick_members=True)
    @option("user", description="Mention the user whom you want to kick")
    @option("reason", description="Enter the reason for kicking the user", required=False)
    async def kick(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str = None):
        """Kicks the mentioned user."""
        if user == ctx.author:
            error_em = discord.Embed(
                description=f"{emoji.error} You cannot use it on yourself", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            error_em = discord.Embed(
                description=f"{emoji.error} Given user has same role or higher role than you",
                color=config.color.error,
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            kich_em = discord.Embed(
                title=f"{emoji.kick} Kicked User",
                description=f"Successfully kicked **{user}** from the server.\n"
                + f"{emoji.bullet2} **Reason**: {reason}",
                color=config.color.error,
            )
            await user.kick(reason=reason)
            await ctx.respond(embed=kich_em)

    # Ban
    @slash_command(name="ban")
    @discord.default_permissions(ban_members=True)
    @option("user", description="Mention the user whom you want to ban")
    @option("reason", description="Enter the reason for banning the user", required=False)
    async def ban(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str = None):
        """Bans the mentioned user."""
        if user == ctx.author:
            error_em = discord.Embed(
                description=f"{emoji.error} You cannot use it on yourself", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            error_em = discord.Embed(
                description=f"{emoji.error} Given user has same role or higher role than you",
                color=config.color.error,
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            ban_em = discord.Embed(
                title=f"{emoji.mod2} Banned User",
                description=f"Successfully banned **{user}** from the server.\n"
                + f"{emoji.bullet2} **Reason**: {reason}",
                color=config.color.error,
            )
            await user.ban(reason=reason)
            await ctx.respond(embed=ban_em)

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
            error_em = discord.Embed(
                description=f"{emoji.error} You cannot use it on yourself.", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            error_em = discord.Embed(
                description=f"{emoji.error} Given user has same role or higher role than you.",
                color=config.color.error,
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            try:
                dur: datetime.timedelta = parse_duration(duration)
            except ValueError as e:
                error_em = discord.Embed(description=f"{emoji.error} {e}", color=config.color.error)
                await ctx.respond(embed=error_em, ephemeral=True)
                return
            await user.timeout_for(dur, reason=reason)
            timeout_em = discord.Embed(
                title=f"{emoji.timer2} Timed out User",
                description=f"Successfully timed out {user.mention}.\n"
                + f"{emoji.bullet2} **Duration**: `{format_timedelta(dur, locale='en_IN')}`\n"
                + f"{emoji.bullet2} **Reason**: {reason}",
                color=config.color.error,
            )
            await ctx.respond(embed=timeout_em)

    # Untimeout user
    @slash_command(name="untimeout")
    @discord.default_permissions(moderate_members=True)
    @option("user", description="Mention the user whom you want to untimeout")
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def untimeout_user(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str = None):
        """Untimeouts the mentioned user."""
        if user == ctx.author:
            error_em = discord.Embed(
                description=f"{emoji.error} You cannot use it on yourself", color=config.color.error
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            error_em = discord.Embed(
                description=f"{emoji.error} Given user has same role or higher role than you",
                color=config.color.error,
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            await user.timeout(None, reason=reason)
            untimeout_em = discord.Embed(
                title=f"{emoji.timer} Untimed out User",
                description=f"Successfully untimed out {user.mention}.\n" + f"{emoji.bullet} **Reason**: {reason}",
                color=config.color.theme,
            )
            await ctx.respond(embed=untimeout_em)

    # Lock
    @slash_command(name="lock")
    @discord.default_permissions(manage_channels=True)
    @option("reason", description="Enter the reason for locking the channel", required=False)
    async def lock(self, ctx: discord.ApplicationContext, reason: str = None):
        """Locks the current channel."""
        lock_em = discord.Embed(
            title=f"{emoji.lock} Channel Locked",
            description=f"Successfull locked {ctx.channel.mention}.\n" + f"{emoji.bullet} **Reason**: {reason}",
            color=config.color.theme,
        )
        await ctx.channel.set_permissions(ctx.author, send_messages=True)
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.respond(embed=lock_em)

    # Unlock
    @slash_command(name="unlock")
    @discord.default_permissions(manage_channels=True)
    async def unlock(self, ctx: discord.ApplicationContext):
        """Unlocks the current channel."""
        unlock_em = discord.Embed(
            title=f"{emoji.unlock} Channel Unlocked",
            description=f"Successfull unlocked {ctx.channel.mention}",
            color=config.color.theme,
        )
        await ctx.channel.set_permissions(ctx.author, send_messages=True)
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.respond(embed=unlock_em)

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
        add_role_em = discord.Embed(
            title=f"{emoji.plus} Role Added",
            description=f"Successfully added {role.mention} to {user.mention}",
            color=config.color.theme,
        )
        await user.add_roles(role)
        await ctx.respond(embed=add_role_em)

    # Remove role
    @role.command(name="remove")
    @option("user", description="Mention the user whom you want to remove the role")
    @option("role", description="Mention the role which you will remove from the user")
    async def remove_role(self, ctx: discord.ApplicationContext, user: discord.Member, role: discord.Role):
        """Removes the mentioned role from the mentioned user."""
        remove_role_em = discord.Embed(
            title=f"{emoji.minus} Role Removed",
            description=f"Successfully removed {role.mention} from {user.mention}",
            color=config.color.theme,
        )
        await user.remove_roles(role)
        await ctx.respond(embed=remove_role_em)


def setup(client: discord.Bot):
    client.add_cog(Moderation(client))
