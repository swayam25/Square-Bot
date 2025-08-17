import datetime
import discord
from babel.dates import format_timedelta
from core import Client
from core.view import View
from db.funcs.guild import fetch_guild_settings
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from utils import config
from utils.emoji import emoji
from utils.helpers import parse_duration


class MassModeration(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # Mass slash cmd group
    mass = SlashCommandGroup(
        name="mass",
        description="Mass moderation commands.",
        default_member_permissions=discord.Permissions(manage_guild=True),
    )

    # Mass kick
    @mass.command(name="kick")
    @option("users", description='Mention the users whom you want to kick. Use " " to separate users.', required=True)
    @option("reason", description="Enter the reason for kicking the user", required=False)
    async def mass_kick_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Kicks mentioned users."""
        await ctx.defer()
        users: list = users.split()
        _users: list = []
        errors: list[tuple] = []
        if len(users) > 10:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} You can only mass kick upto 10 users."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            for user in users:
                try:
                    _user = await commands.MemberConverter().convert(ctx, user.strip())
                except Exception:
                    errors.append((user.strip(), "User not found."))
                    continue
                if _user == ctx.author:
                    errors.append((ctx.author.mention, "You cannot use it on yourself."))
                    continue
                elif _user.top_role.position >= ctx.author.top_role.position:
                    errors.append((_user.mention, "User has same role or higher role than you."))
                    continue
                else:
                    _users.append(_user.mention)
                await _user.kick(reason=reason)
            if len(_users) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Mass Kicked Users"),
                        discord.ui.TextDisplay(
                            f"Successfully kicked {len(_users)} users.\n"
                            f"{emoji.description} **Reason**: {reason}\n"
                            f"{emoji.user} **Users**: {', '.join(_users)}"
                        ),
                    )
                )
                await ctx.respond(view=view)
                channel_id = (await fetch_guild_settings(ctx.guild.id)).mod_cmd_log_channel_id
                if channel_id:
                    log_ch = await self.client.fetch_channel(channel_id)
                    mod_view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay("## Mass Kicked Users"),
                            discord.ui.TextDisplay(
                                f"Successfully kicked {len(_users)} users.\n"
                                f"{emoji.description_red} **Reason**: {reason}\n"
                                f"{emoji.user_red} **Users**: {', '.join(_users)}\n"
                                f"{emoji.owner_red} **Moderator**: {ctx.author.mention}"
                            ),
                            color=config.color.red,
                        )
                    )
                    await log_ch.send(view=mod_view)
            if len(errors) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Can't kick users"),
                        discord.ui.TextDisplay(
                            "\n".join([f"{emoji.bullet_red} **{user}**: {reason}" for user, reason in errors])
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    # Mass ban
    @mass.command(name="ban")
    @option("users", description='Mention the users whom you want to ban. Use " " to separate users.', required=True)
    @option(
        "delete_messages",
        description="Enter the duration of messages to delete. Ex: 1m, 2h, 7d (default), 0 (disable) etc...",
        required=False,
    )
    @option("reason", description="Enter the reason for banning the user", required=False)
    async def mass_ban_users(
        self, ctx: discord.ApplicationContext, users: str, delete_messages: str = "7d", reason: str = None
    ):
        """Bans mentioned users."""
        await ctx.defer()
        users: list = users.split()
        _users: list = []
        errors: list[tuple] = []
        dur, del_after = None, None
        if delete_messages and delete_messages != "0":
            del_after = parse_duration(delete_messages, max_duration="7d")
            dur = int(del_after.total_seconds()) if del_after else None
        if len(users) > 10:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} You can only mass ban upto 10 users."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            for user in users:
                try:
                    _user = await commands.MemberConverter().convert(ctx, user.strip())
                except Exception:
                    errors.append((user.strip(), "User not found."))
                    continue
                if _user == ctx.author:
                    errors.append((ctx.author.mention, "You cannot use it on yourself."))
                    continue
                elif _user.top_role.position >= ctx.author.top_role.position:
                    errors.append((_user.mention, "User has same role or higher role than you."))
                    continue
                _users.append(_user.mention)
                await ctx.guild.ban(_user, reason=reason, delete_message_seconds=dur)
            if len(_users) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Mass Banned Users"),
                        discord.ui.TextDisplay(
                            f"Successfully banned {len(_users)} users.\n"
                            f"{emoji.description_red} **Reason**: {reason}\n"
                            f"{emoji.user_red} **Users**: {', '.join(_users)}"
                            f"{emoji.bin_red} **Delete Message Duration**: `{format_timedelta(del_after)}`"
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view)
                channel_id = (await fetch_guild_settings(ctx.guild.id)).mod_cmd_log_channel_id
                if channel_id:
                    log_ch = await self.client.fetch_channel(channel_id)
                    mod_view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay("## Mass Banned Users"),
                            discord.ui.TextDisplay(
                                f"Successfully banned {len(_users)} users.\n"
                                f"{emoji.description_red} **Reason**: {reason}\n"
                                f"{emoji.user_red} **Users**: {', '.join(_users)}\n"
                                f"{emoji.owner_red} **Moderator**: {ctx.author.mention}"
                            ),
                            color=config.color.red,
                        )
                    )
                    await log_ch.send(view=mod_view)
            if len(errors) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Can't ban users"),
                        discord.ui.TextDisplay(
                            "\n".join([f"{emoji.bullet_red} **{user}**: {reason}" for user, reason in errors])
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    # Mass unban
    @mass.command(name="unban")
    @option(
        "users", description='Enter the user IDs whom you want to unban. Use " " to separate user IDs.', required=True
    )
    @option("reason", description="Enter the reason for unbanning the user", required=False)
    async def mass_unban_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Unbans mentioned users."""
        await ctx.defer()
        users: list = users.split()
        _users: list = []
        errors: list[tuple] = []
        if len(users) > 10:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} You can only mass unban upto 10 users."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            for user in users:
                try:
                    user_id = int(user.strip())
                    _user = await self.client.fetch_user(user_id)
                except Exception:
                    errors.append((user.strip(), "User not found."))
                    continue
                _users.append(_user.mention)
                await ctx.guild.unban(_user, reason=reason)
            if len(_users) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Mass Unbanned Users"),
                        discord.ui.TextDisplay(
                            f"Successfully unbanned {len(_users)} users.\n"
                            f"{emoji.description} **Reason**: {reason}\n"
                            f"{emoji.user} **Users**: {', '.join(_users)}"
                        ),
                    )
                )
                await ctx.respond(view=view)
                channel_id = (await fetch_guild_settings(ctx.guild.id)).mod_cmd_log_channel_id
                if channel_id:
                    log_ch = await self.client.fetch_channel(channel_id)
                    mod_view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay("## Mass Unbanned Users"),
                            discord.ui.TextDisplay(
                                f"Successfully unbanned {len(_users)} users.\n"
                                f"{emoji.description} **Reason**: {reason}\n"
                                f"{emoji.user} **Users**: {', '.join(_users)}\n"
                                f"{emoji.owner} **Moderator**: {ctx.author.mention}"
                            ),
                        )
                    )
                    await log_ch.send(view=mod_view)
            if len(errors) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Can't unban users"),
                        discord.ui.TextDisplay(
                            "\n".join([f"{emoji.bullet_red} **{user}**: {reason}" for user, reason in errors])
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    # Mass timeout users
    @mass.command(name="timeout")
    @option(
        "users", description='Mention the users whom you want to timeout. Use " " to separate users.', required=True
    )
    @option("duration", description="Enter the duration of timeout. Ex: 1d, 2w etc...")
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def mass_timeout_users(self, ctx: discord.ApplicationContext, users: str, duration: str, reason: str = None):
        """Timeouts mentioned users."""
        await ctx.defer()
        users: list = users.split()
        _users: list = []
        try:
            dur: datetime.timedelta = parse_duration(duration)
        except ValueError as e:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} {e}"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        errors: list[tuple] = []
        if len(users) > 10:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} You can only mass timeout upto 10 users."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            for user in users:
                try:
                    _user = await commands.MemberConverter().convert(ctx, user.strip())
                except Exception:
                    errors.append((user.strip(), "User not found."))
                    continue
                if _user == ctx.guild.owner:
                    errors.append((_user.mention, "You cannot use it on server owner."))
                    continue
                elif _user == ctx.author:
                    errors.append((ctx.author.mention, "You cannot use it on yourself."))
                    continue
                elif _user.top_role.position >= ctx.author.top_role.position:
                    errors.append((_user.mention, "User has same role or higher role than you."))
                    continue
                else:
                    _users.append(_user.mention)
                await _user.timeout_for(dur, reason=reason)
            if len(_users) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Mass Timed out Users"),
                        discord.ui.TextDisplay(
                            f"Successfully timed out {len(_users)} users.\n"
                            f"{emoji.duration} **Duration**: `{format_timedelta(dur)}`\n"
                            f"{emoji.description} **Reason**: {reason}\n"
                            f"{emoji.user} **Users**: {', '.join(_users)}"
                        ),
                    )
                )
                await ctx.respond(view=view)
                channel_id = (await fetch_guild_settings(ctx.guild.id)).mod_cmd_log_channel_id
                if channel_id:
                    log_ch = await self.client.fetch_channel(channel_id)
                    mod_view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay("## Mass Timed out Users"),
                            discord.ui.TextDisplay(
                                f"Successfully timed out {len(_users)} users.\n"
                                f"{emoji.duration_red} **Duration**: `{format_timedelta(dur)}`\n"
                                f"{emoji.description_red} **Reason**: {reason}\n"
                                f"{emoji.user_red} **Users**: {', '.join(_users)}\n"
                                f"{emoji.owner_red} **Moderator**: {ctx.author.mention}"
                            ),
                            color=config.color.red,
                        )
                    )
                    await log_ch.send(view=mod_view)
            if len(errors) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Can't timeout users"),
                        discord.ui.TextDisplay(
                            "\n".join([f"{emoji.bullet_red} **{user}**: {reason}" for user, reason in errors])
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    # Mass untimeout users
    @mass.command(name="untimeout")
    @option(
        "users", description='Mention the users whom you want to untimeout. Use " " to separate users.', required=True
    )
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def mass_untimeout_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Untimeouts mentioned users."""
        await ctx.defer()
        users: list = users.split()
        _users: list = []
        errors: list[tuple] = []
        if len(users) > 10:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} You can only mass untimeout upto 10 users."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            for user in users:
                try:
                    _user = await commands.MemberConverter().convert(ctx, user.strip())
                except Exception:
                    errors.append((user.strip(), "User not found."))
                    continue
                if _user == ctx.author:
                    errors.append((ctx.author.mention, "You cannot use it on yourself."))
                    continue
                elif _user.top_role.position >= ctx.author.top_role.position:
                    errors.append((_user.mention, "User has same role or higher role than you."))
                    continue
                else:
                    _users.append(_user.mention)
                await _user.timeout(None, reason=reason)
            if len(_users) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Mass Untimed out Users"),
                        discord.ui.TextDisplay(
                            f"Successfully untimed out {len(_users)} users.\n"
                            f"{emoji.description} **Reason**: {reason}\n"
                            f"{emoji.user} **Users**: {', '.join(_users)}"
                        ),
                    )
                )
                await ctx.respond(view=view)
                channel_id = (await fetch_guild_settings(ctx.guild.id)).mod_cmd_log_channel_id
                if channel_id:
                    log_ch = await self.client.fetch_channel(channel_id)
                    mod_view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay("## Mass Untimed out Users"),
                            discord.ui.TextDisplay(
                                f"Successfully untimed out {len(_users)} users.\n"
                                f"{emoji.description_red} **Reason**: {reason}\n"
                                f"{emoji.user_red} **Users**: {', '.join(_users)}\n"
                                f"{emoji.owner_red} **Moderator**: {ctx.author.mention}"
                            ),
                            color=config.color.red,
                        )
                    )
                    await log_ch.send(view=mod_view)
            if len(errors) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Can't untimeout users"),
                        discord.ui.TextDisplay(
                            "\n".join([f"{emoji.bullet_red} **{user}**: {reason}" for user, reason in errors])
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    # Mass role add
    @mass.command(name="role-add")
    @option(
        "users",
        description='Mention the users whom you want to add the role. Use " " to separate users.',
        required=True,
    )
    @option(
        "roles",
        description='Mention the roles which you will add to the users. Use " " to separate roles.',
        required=True,
    )
    async def mass_role_add(self, ctx: discord.ApplicationContext, users: str, roles: str):
        """Adds mentioned roles to mentioned users."""
        await ctx.defer()
        users: list = users.split()
        roles: list = roles.split()
        _users: list = []
        _roles: list = []
        role_errors: list[tuple] = []
        user_errors: list[tuple] = []
        if len(users) > 10 or len(roles) > 10:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} You can only mass add 10 roles upto 10 users."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            for role in roles:  # Check roles
                try:
                    _role = await commands.RoleConverter().convert(ctx, role.strip())
                except Exception:
                    role_errors.append((role.strip(), "Role not found."))
                    continue
                if _role.position >= ctx.guild.get_member(self.client.user.id).top_role.position:
                    role_errors.append((_role.mention, "Role has same or higher position than me."))
                    continue
                else:
                    _roles.append(_role)
            if len(_roles) > 0:
                for user in users:  # Check users
                    try:
                        _user = await commands.MemberConverter().convert(ctx, user.strip())
                    except Exception:
                        user_errors.append((user.strip(), "User not found."))
                        continue
                    if _user.top_role.position >= ctx.author.top_role.position:
                        user_errors.append((_user.mention, "User has same role or higher role than you."))
                        continue
                    else:
                        _users.append(_user.mention)
                    for role in _roles:
                        await _user.add_roles(role)
            if len(_users) > 0 and len(_roles) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Mass Added Roles"),
                        discord.ui.TextDisplay(
                            f"Successfully added {len(_roles)} roles to {len(_users)} users.\n"
                            f"{emoji.user} **Users**: {', '.join(_users)}\n"
                            f"{emoji.role} **Roles**: {', '.join([role.mention for role in _roles])}"
                        ),
                    )
                )
                await ctx.respond(view=view)
                channel_id = (await fetch_guild_settings(ctx.guild.id)).mod_cmd_log_channel_id
                if channel_id:
                    log_ch = await self.client.fetch_channel(channel_id)
                    mod_view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay("## Mass Added Roles"),
                            discord.ui.TextDisplay(
                                f"Successfully added {len(_roles)} roles to {len(_users)} users.\n"
                                f"{emoji.user_red} **Users**: {', '.join(_users)}\n"
                                f"{emoji.role_red} **Roles**: {', '.join([role.mention for role in _roles])}\n"
                                f"{emoji.owner_red} **Moderator**: {ctx.author.mention}"
                            ),
                            color=config.color.red,
                        )
                    )
                    await log_ch.send(view=mod_view)
            if len(role_errors) > 0 or len(user_errors) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Can't add roles"),
                        discord.ui.TextDisplay(
                            "\n".join(
                                [f"{emoji.bullet_red} **{obj}**: {reason}" for obj, reason in role_errors + user_errors]
                            )
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    # Mass role remove
    @mass.command(name="role-remove")
    @option(
        "users",
        description='Mention the users whom you want to remove the role. Use " " to separate users.',
        required=True,
    )
    @option(
        "roles",
        description='Mention the roles which you will remove from the users. Use " " to separate roles.',
        required=True,
    )
    async def mass_role_remove(self, ctx: discord.ApplicationContext, users: str, roles: str):
        """Removes mentioned roles from mentioned users."""
        await ctx.defer()
        users: list = users.split()
        roles: list = roles.split()
        _users: list = []
        _roles: list = []
        role_errors: list[tuple] = []
        user_errors: list[tuple] = []
        if len(users) > 10 or len(roles) > 10:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} You can only mass remove 10 roles upto 10 users."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            for role in roles:  # Check roles
                try:
                    _role = await commands.RoleConverter().convert(ctx, role.strip())
                except Exception:
                    role_errors.append((role.strip(), "Role not found."))
                    continue
                if _role.position >= ctx.guild.get_member(self.client.user.id).top_role.position:
                    role_errors.append((_role.mention, "Role has same or higher position than me."))
                    continue
                else:
                    _roles.append(_role)
            if len(_roles) > 0:
                for user in users:  # Check users
                    try:
                        _user = await commands.MemberConverter().convert(ctx, user.strip())
                    except Exception:
                        user_errors.append((user.strip(), "User not found."))
                        continue
                    if _user.top_role.position >= ctx.author.top_role.position:
                        user_errors.append((_user.mention, "User has same role or higher role than you."))
                        continue
                    else:
                        _users.append(_user.mention)
                    for role in _roles:
                        await _user.remove_roles(role)
            if len(_users) > 0 and len(_roles) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Mass Removed Roles"),
                        discord.ui.TextDisplay(
                            f"Successfully removed {len(_roles)} roles from {len(_users)} users.\n"
                            f"{emoji.user} **Users**: {', '.join(_users)}\n"
                            f"{emoji.role} **Roles**: {', '.join([role.mention for role in _roles])}"
                        ),
                    )
                )
                await ctx.respond(view=view)
                channel_id = (await fetch_guild_settings(ctx.guild.id)).mod_cmd_log_channel_id
                if channel_id:
                    log_ch = await self.client.fetch_channel(channel_id)
                    mod_view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay("## Mass Removed Roles"),
                            discord.ui.TextDisplay(
                                f"Successfully removed {len(_roles)} roles from {len(_users)} users.\n"
                                f"{emoji.user_red} **Users**: {', '.join(_users)}\n"
                                f"{emoji.role_red} **Roles**: {', '.join([role.mention for role in _roles])}\n"
                                f"{emoji.owner_red} **Moderator**: {ctx.author.mention}"
                            ),
                            color=config.color.red,
                        )
                    )
                    await log_ch.send(view=mod_view)
            if len(role_errors) > 0 or len(user_errors) > 0:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Can't remove roles"),
                        discord.ui.TextDisplay(
                            "\n".join(
                                [f"{emoji.bullet_red} **{obj}**: {reason}" for obj, reason in role_errors + user_errors]
                            )
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)


def setup(client: Client):
    client.add_cog(MassModeration(client))
