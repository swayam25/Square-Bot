import discord
import datetime
from utils import database as db, emoji
from discord.ext import commands
from discord.commands import slash_command, Option

class Moderation(commands.Cog):
    def __init__(self, client):
        self.client = client
 
# Purge
    @slash_command(guild_ids=db.guild_ids(), name="purge")
    @discord.default_permissions(manage_messages=True)
    async def purge(
        self, ctx,
        amount: Option(int, "Enter an integer between 1 to 100")
    ):
        """Purges the amount of given messages"""
        amount_condition = [
            amount < 1,
            amount > 100
        ]
        if any(amount_condition):
            errorEm = discord.Embed(description=f"{emoji.error} Amount must be between 1 to 100", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        else:
            purgeEm = discord.Embed(title=f"{emoji.bin} Messages Purged", description=f"Successfully purged `{amount}` message(s)", color=db.theme_color)
            await ctx.respond(embed=purgeEm, ephemeral=True)
            await ctx.channel.purge(limit=amount)

# Kick
    @slash_command(guild_ids=db.guild_ids(), name="kick")
    @discord.default_permissions(kick_members=True)
    async def kick(
        self, ctx,
        user: Option(discord.Member, "Mention the user whom you want to kick"),
        reason: Option(str, "Enter the reason for kicking the user", required=False)
    ):
        """Kicks the mentioned user"""
        if user == ctx.author:
            errorEm = discord.Embed(description=f"{emoji.error} You cannot use it on yourself", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            errorEm = discord.Embed(description=f"{emoji.error} Given user has same role or higher role than you", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        else:
            kich_em = discord.Embed(
                title=f"{emoji.kick} Kicked User", 
                description=f"Successfully kicked **{user}** from the server.\n" +
                            f"{emoji.bullet} **Reason**: {reason}",
                color=db.theme_color
            )
            await user.kick(reason=reason)
            await ctx.respond(embed=kich_em)

# Ban
    @slash_command(guild_ids=db.guild_ids(), name="ban")
    @discord.default_permissions(ban_members=True)
    async def ban(
        self, ctx,
        user: Option(discord.Member, "Mention the user whom you want to ban"),
        reason: Option(str, "Enter the reason for banning the user", required=False)
    ):
        """Bans the mentioned user"""
        if user == ctx.author:
            errorEm = discord.Embed(description=f"{emoji.error} You cannot use it on yourself", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            errorEm = discord.Embed(description=f"{emoji.error} Given user has same role or higher role than you", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        else:
            banEm = discord.Embed(
                title=f"{emoji.mod2} Banned User",
                description=f"Successfully banned **{user}** from the server.\n" +
                            f"{emoji.bullet} **Reason**: {reason}",
                color=db.theme_color
            )
            await user.ban(reason=reason)
            await ctx.respond(embed=banEm)

# Timeout user
    @slash_command(guild_ids=db.guild_ids(), name="timeout")
    @discord.default_permissions(moderate_members=True)
    async def timeout_user(
        self, ctx,
        user: Option(discord.Member, "Mention the user whom you want to timeout"),
        minutes: Option(int, "Enter the duration of timeout in minutes"),
        reason: Option(str, "Enter the reason for user timeout", required=False)
    ):
        """Timeouts the mentioned user"""
        if user == ctx.author:
            errorEm = discord.Embed(description=f"{emoji.error} You cannot use it on yourself", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            errorEm = discord.Embed(description=f"{emoji.error} Given user has same role or higher role than you", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        else:
            duration = datetime.timedelta(minutes=minutes)
            await user.timeout_for(duration, reason=reason)
            timeout_em = discord.Embed(
                title=f"{emoji.timer2} Timed out User",
                description=f"Successfully timed out {user.mention}.\n" +
                            f"{emoji.bullet} **Duration**: `{duration}`\n" +
                            f"{emoji.bullet} **Reason**: {reason}", 
                color=db.theme_color
            )
            await ctx.respond(embed=timeout_em)

# Untimeout user
    @slash_command(guild_ids=db.guild_ids(), name="untimeout")
    @discord.default_permissions(moderate_members=True)
    async def untimeout_user(
        self, ctx,
        user: Option(discord.Member, "Mention the user whom you want to untimeout"),
        reason: Option(str, "Enter the reason for user timeout", required=False)
    ):
        """Untimeouts the mentioned user"""
        if user == ctx.author:
            errorEm = discord.Embed(description=f"{emoji.error} You cannot use it on yourself", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            errorEm = discord.Embed(description=f"{emoji.error} Given user has same role or higher role than you", color=db.error_color)
            await ctx.respond(embed=errorEm, ephemeral=True)
        else:
            await user.timeout(None, reason=reason)
            untimeout_em = discord.Embed(
                title=f"{emoji.timer} Untimed out User",
                description=f"Successfully untimed out {user.mention}.\n" +
                            f"{emoji.bullet} **Reason**: {reason}", 
                color=db.theme_color
            )
            await ctx.respond(embed=untimeout_em)

# Lock
    @slash_command(guild_ids=db.guild_ids(), name="lock")
    @discord.default_permissions(manage_channels=True)
    async def lock(
        self, ctx,
        reason: Option(str, "Enter the reason for locking the channel", required=False)
    ):
        """Locks the current channel"""
        lock_em = discord.Embed(
            title=f"{emoji.lock} Channel Locked",
            description=f"Successfull locked {ctx.channel.mention}.\n" +
                        f"{emoji.bullet} **Reason**: {reason}",
            color=db.theme_color
        )
        await ctx.channel.set_permissions(ctx.author, send_messages=True)
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.respond(embed=lock_em)

# Unlock
    @slash_command(guild_ids=db.guild_ids(), name="unlock")
    @discord.default_permissions(manage_channels=True)
    async def unlock(self, ctx):
        """Unlocks the current channel"""
        unlock_em = discord.Embed(
            title=f"{emoji.unlock} Channel Unlocked",
            description=f"Successfull unlocked {ctx.channel.mention}",
            color=db.theme_color
        )
        await ctx.channel.set_permissions(ctx.author, send_messages=True)
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.respond(embed=unlock_em)

# Role add
    @slash_command(guild_ids=db.guild_ids(), name="add-role")
    @discord.default_permissions(manage_roles=True)
    async def add_role(
        self, ctx,
        user: Option(discord.Member, "Mention the user whom you want to add the role"),
        role: Option(discord.Role, "Mention the role which you will add to the user")
    ):
        """Adds the mentioned role to the mentioned user"""
        add_role_em = discord.Embed(
            title=f"{emoji.plus} Role Added",
            description=f"Successfully added {role.mention} to {user.mention}",
            color=db.theme_color
        )
        await user.add_roles(role)
        await ctx.respond(embed=add_role_em)

# Remove role
    @slash_command(guild_ids=db.guild_ids(), name="remove-role")
    @discord.default_permissions(manage_roles=True)
    async def remove_role(
        self, ctx,
        user: Option(discord.Member, "Mention the user whom you want to remove the role"),
        role: Option(discord.Role, "Mention the role which you will remove from the user")
    ):
        """Removes the mentioned role from the mentioned user"""
        remove_role_em = discord.Embed(
            title=f"{emoji.minus} Role Removed",
            description=f"Successfully removed {role.mention} from {user.mention}",
            color=db.theme_color
        )
        await user.remove_roles(role)
        await ctx.respond(embed=remove_role_em)

def setup(client):
    client.add_cog(Moderation(client))
