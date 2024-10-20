import discord
import datetime
from utils import database as db, emoji
from discord.ext import commands
from discord.commands import option, SlashCommandGroup

class MassModeration(commands.Cog):
    def __init__(self, client):
        self.client = client

# Mass slash cmd group
    mass = SlashCommandGroup(guild_ids=db.guild_ids(), name="mass", description="Mass moderation commands")

# Mass kick
    @mass.command(name="kick")
    @discord.default_permissions(kick_members=True)
    @option("users", description="Mention the users whom you want to kick. Use \",\" to separate users.", required=True)
    @option("reason", description="Enter the reason for kicking the user", required=False)
    async def mass_kick_users(self, ctx, users: str, reason: str = None):
        """Kicks mentioned users."""
        await ctx.defer()
        users: list = users.split(",")
        _users: list = []
        errors: list[tuple] = []
        if len(users) > 10:
            error_em = discord.Embed(description=f"{emoji.error} You can only mass kick upto 10 users.", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            for user in users:
                try:
                    _user = await commands.MemberConverter().convert(ctx, user.strip())
                except:
                    errors.append((user.strip(), "User not found."))
                    users.pop(users.index(user))
                    continue
                if _user == ctx.author:
                    errors.append((ctx.author.mention, "You cannot use it on yourself."))
                    users.pop(users.index(user))
                    continue
                elif _user.top_role.position >= ctx.author.top_role.position:
                    errors.append((_user.mention, "User has same role or higher role than you."))
                    users.pop(users.index(user))
                    continue
                _users.append(_user.mention)
                await _user.kick(reason=reason)
            if len(_users) > 0:
                mass_kick_em = discord.Embed(
                    title=f"{emoji.kick} Mass Kicked Users",
                    description=f"Successfully kicked {len(users)} users.\n" +
                                f"{emoji.bullet} **Reason**: {reason}\n" +
                                f"{emoji.bullet} **Users**: {", ".join(_users)}",
                    color=db.theme_color
                )
                await ctx.respond(embed=mass_kick_em)
                if db.mod_cmd_log_ch(ctx.guild.id):
                    log_ch = await self.client.fetch_channel(db.mod_cmd_log_ch(ctx.guild.id))
                    mass_kick_em.description += f"\n{emoji.bullet} **Moderator**: {ctx.author.mention}"
                    await log_ch.send(embed=mass_kick_em)
            if len(errors) > 0:
                error_em = discord.Embed(
                    title=f"{emoji.error} Can't kick users",
                    description="\n".join([f"{emoji.bullet} **{user}**: {reason}" for user, reason in errors]),
                    color=db.error_color
                )
                await ctx.respond(embed=error_em, ephemeral=True)

# Mass ban
    @mass.command(name="ban")
    @discord.default_permissions(ban_members=True)
    @option("users", description="Mention the users whom you want to ban. Use \",\" to separate users.", required=True)
    @option("reason", description="Enter the reason for banning the user", required=False)
    async def mass_ban_users(self, ctx, users: str, reason: str = None):
        """Bans mentioned users."""
        await ctx.defer()
        users: list = users.split(",")
        _users: list = []
        errors: list[tuple] = []
        if len(users) > 10:
            error_em = discord.Embed(description=f"{emoji.error} You can only mass ban upto 10 users.", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            for user in users:
                try:
                    _user = await commands.MemberConverter().convert(ctx, user.strip())
                except:
                    errors.append((user.strip(), "User not found."))
                    users.pop(users.index(user))
                    continue
                if _user == ctx.author:
                    errors.append((ctx.author.mention, "You cannot use it on yourself."))
                    users.pop(users.index(user))
                    continue
                elif _user.top_role.position >= ctx.author.top_role.position:
                    errors.append((_user.mention, "User has same role or higher role than you."))
                    users.pop(users.index(user))
                    continue
                _users.append(_user.mention)
                await _user.ban(reason=reason)
            if len(_users) > 0:
                mass_ban_em = discord.Embed(
                    title=f"{emoji.mod2} Mass Banned Users",
                    description=f"Successfully banned {len(users)} users.\n" +
                                f"{emoji.bullet} **Reason**: {reason}\n" +
                                f"{emoji.bullet} **Users**: {", ".join(_users)}",
                    color=db.theme_color
                )
                await ctx.respond(embed=mass_ban_em)
                if db.mod_cmd_log_ch(ctx.guild.id):
                    log_ch = await self.client.fetch_channel(db.mod_cmd_log_ch(ctx.guild.id))
                    mass_ban_em.description += f"\n{emoji.bullet} **Moderator**: {ctx.author.mention}"
                    await log_ch.send(embed=mass_ban_em)
            if len(errors) > 0:
                error_em = discord.Embed(
                    title=f"{emoji.error} Can't ban users",
                    description="\n".join([f"{emoji.bullet} **{user}**: {reason}" for user, reason in errors]),
                    color=db.error_color
                )
                await ctx.respond(embed=error_em, ephemeral=True)

# Mass timeout users
    @mass.command(name="timeout")
    @discord.default_permissions(moderate_members=True)
    @option("users", description="Mention the users whom you want to timeout. Use \",\" to separate users.", required=True)
    @option("minutes", description="Enter the duration of timeout in minutes")
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def mass_timeout_users(self, ctx, users: str, minutes: int, reason: str = None):
        """Timeouts mentioned users."""
        await ctx.defer()
        users: list = users.split(",")
        _users: list = []
        duration = datetime.timedelta(minutes=minutes)
        errors: list[tuple] = []
        if len(users) > 10:
            error_em = discord.Embed(description=f"{emoji.error} You can only mass timeout upto 10 users.", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            for user in users:
                try:
                    _user = await commands.MemberConverter().convert(ctx, user.strip())
                except:
                    errors.append((user.strip(), "User not found."))
                    users.pop(users.index(user))
                    continue
                if _user == ctx.guild.owner:
                    errors.append((_user.mention, "You cannot use it on server owner."))
                    users.pop(users.index(user))
                    continue
                elif _user == ctx.author:
                    errors.append((ctx.author.mention, "You cannot use it on yourself."))
                    users.pop(users.index(user))
                    continue
                elif _user.top_role.position >= ctx.author.top_role.position:
                    errors.append((_user.mention, "User has same role or higher role than you."))
                    users.pop(users.index(user))
                    continue
                _users.append(_user.mention)
                await _user.timeout_for(duration, reason=reason)
            if len(_users) > 0:
                mass_timeout_em = discord.Embed(
                    title=f"{emoji.timer2} Mass Timed out Users",
                    description=f"Successfully timed out {len(users)} users.\n" +
                                f"{emoji.bullet} **Duration**: `{duration}`\n" +
                                f"{emoji.bullet} **Reason**: {reason}\n" +
                                f"{emoji.bullet} **Users**: {", ".join(_users)}",
                    color=db.theme_color
                )
                await ctx.respond(embed=mass_timeout_em)
                if db.mod_cmd_log_ch(ctx.guild.id):
                    log_ch = await self.client.fetch_channel(db.mod_cmd_log_ch(ctx.guild.id))
                    mass_timeout_em.description += f"\n{emoji.bullet} **Moderator**: {ctx.author.mention}"
                    await log_ch.send(embed=mass_timeout_em)
            if len(errors) > 0:
                error_em = discord.Embed(
                    title=f"{emoji.error} Can't timeout users",
                    description="\n".join([f"{emoji.bullet} **{user}**: {reason}" for user, reason in errors]),
                    color=db.error_color
                )
                await ctx.respond(embed=error_em, ephemeral=True)


# Mass untimeout users
    @mass.command(name="untimeout")
    @discord.default_permissions(moderate_members=True)
    @option("users", description="Mention the users whom you want to untimeout. Use \",\" to separate users.", required=True)
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def mass_untimeout_users(self, ctx, users: str, reason: str = None):
        """Untimeouts mentioned users."""
        await ctx.defer()
        users: list = users.split(",")
        _users: list = []
        errors: list[tuple] = []
        if len(users) > 10:
            error_em = discord.Embed(description=f"{emoji.error} You can only mass untimeout upto 10 users.", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            for user in users:
                try:
                    _user = await commands.MemberConverter().convert(ctx, user.strip())
                except:
                    errors.append((user.strip(), "User not found."))
                    users.pop(users.index(user))
                    continue
                if _user == ctx.author:
                    errors.append((ctx.author.mention, "You cannot use it on yourself."))
                    users.pop(users.index(user))
                    continue
                elif _user.top_role.position >= ctx.author.top_role.position:
                    errors.append((_user.mention, "User has same role or higher role than you."))
                    users.pop(users.index(user))
                    continue
                _users.append(_user.mention)
                await _user.timeout(None, reason=reason)
            if len(_users) > 0:
                mass_untimeout_em = discord.Embed(
                    title=f"{emoji.timer} Mass Untimed out Users",
                    description=f"Successfully untimed out {len(users)} users.\n" +
                                f"{emoji.bullet} **Reason**: {reason}\n" +
                                f"{emoji.bullet} **Users**: {', '.join(_users)}",
                    color=db.theme_color
                )
                await ctx.respond(embed=mass_untimeout_em)
                if db.mod_cmd_log_ch(ctx.guild.id):
                    log_ch = await self.client.fetch_channel(db.mod_cmd_log_ch(ctx.guild.id))
                    mass_untimeout_em.description += f"\n{emoji.bullet} **Moderator**: {ctx.author.mention}"
                    await log_ch.send(embed=mass_untimeout_em)
            if len(errors) > 0:
                error_em = discord.Embed(
                    title=f"{emoji.error} Can't untimeout users",
                    description="\n".join([f"{emoji.bullet} **{user}**: {reason}" for user, reason in errors]),
                    color=db.error_color
                )
                await ctx.respond(embed=error_em, ephemeral=True)

def setup(client):
    client.add_cog(MassModeration(client))