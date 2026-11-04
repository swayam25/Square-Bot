import asyncio
import datetime
import discord
from babel.dates import format_timedelta
from collections.abc import Awaitable, Callable
from discord import ui
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view
from square.utils import config, server_log
from square.utils.emoji import emoji
from square.utils.helpers import parse_duration


class MassModeration(
    Cog, name="Mass Moderation", description="Moderate your server in bulk.", emoji=emoji.mass_mod, order=2
):
    def __init__(self, client: Client):
        self.client = client

    # Mass slash cmd group
    mass = SlashCommandGroup(
        name="mass",
        description="Mass moderation commands.",
        default_member_permissions=discord.Permissions(manage_guild=True),
    )

    @staticmethod
    def _hierarchy_error(ctx: discord.ApplicationContext, member: discord.Member) -> str | None:
        if member == ctx.author:
            return "You cannot use it on yourself."
        if member.top_role.position >= ctx.author.top_role.position:
            return "User has same role or higher role than you."
        return None

    async def _resolve(
        self,
        ctx: discord.ApplicationContext,
        users: str,
        verb: str,
        check: Callable[[discord.Member], str | None] | None = None,
        convert: Callable[[str], Awaitable[discord.abc.User]] | None = None,
    ) -> tuple[list, list[tuple]] | None:
        """Resolves the given users, returning the valid ones and errors, or `None` if over the limit."""
        if len(users.split()) > 10:
            await ctx.respond(view=error_view(f"You can only mass {verb} upto 10 users."), ephemeral=True)
            return None
        convert = convert or (lambda user: commands.MemberConverter().convert(ctx, user))
        check = check or (lambda member: self._hierarchy_error(ctx, member))
        resolved: list = []
        errors: list[tuple] = []
        for user in users.split():
            try:
                _user = await convert(user)
            except commands.BadArgument, ValueError, discord.HTTPException:
                errors.append((user, "User not found."))
                continue
            if error := check(_user):
                errors.append((_user.mention, error))
            else:
                resolved.append(_user)
        return resolved, errors

    @staticmethod
    def _result_view(
        title: str,
        summary: str,
        users: list[str],
        fields: list[tuple[str, str, str]],
        color: int | None,
        moderator: discord.abc.User | None = None,
    ) -> DesignerView:
        suffix = {config.color.red: "_red", config.color.orange: "_orange", config.color.green: "_green"}.get(color, "")

        def icon(name: str) -> str:
            return getattr(emoji, f"{name}{suffix}")

        # Logs (with a moderator) read like the logging cog: title and fields only.
        lines = [] if moderator else [f"Successfully {summary} {len(users)} users."]
        lines += [f"{icon(name)} **{label}**: {value}" for name, label, value in fields]
        lines.append(f"{icon('user')} **Users**: {', '.join(users)}")
        if moderator:
            lines.append(f"{icon('owner')} **Moderator**: {moderator.mention}")
        return DesignerView(
            ui.Container(
                ui.TextDisplay(f"## {title}"),
                ui.TextDisplay("\n".join(lines)),
                color=color,
            )
        )

    async def _run(
        self,
        ctx: discord.ApplicationContext,
        targets: list,
        errors: list[tuple],
        action: Callable[[discord.abc.User], Awaitable],
        title: str,
        summary: str,
        error_title: str,
        fields: list[tuple[str, str, str]],
        log_color: int | None,
    ):
        """Runs the action on every target, then reports results, logs them and lists errors."""
        done: list[str] = []
        # Sent together, the HTTP client still queues them per Discord's rate limits
        results = await asyncio.gather(*(action(target) for target in targets), return_exceptions=True)
        for target, result in zip(targets, results, strict=True):
            if isinstance(result, discord.HTTPException):
                errors.append((target.mention, result.text or "Something went wrong."))
            elif isinstance(result, BaseException):
                raise result
            else:
                done.append(target.mention)
        if done:
            await ctx.respond(view=self._result_view(title, summary, done, fields, config.color.green))
            log_view = self._result_view(title, summary, done, fields, log_color, moderator=ctx.author)
            await server_log.send(self.client, ctx.guild, server_log.LogType.MODERATION, log_view)
        if errors:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"## {error_title}"),
                    ui.TextDisplay("\n".join(f"{emoji.bullet_red} **{obj}**: {error}" for obj, error in errors)),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Mass kick
    @mass.command(name="kick")
    @option("users", description='Mention the users whom you want to kick. Use " " to separate users.', required=True)
    @option("reason", description="Enter the reason for kicking the user", required=False)
    async def mass_kick_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Kicks mentioned users."""
        await ctx.defer()
        if resolved := await self._resolve(ctx, users, "kick"):
            await self._run(
                ctx,
                *resolved,
                action=lambda m: m.kick(reason=reason),
                title="Mass Kicked Users",
                summary="kicked",
                error_title="Can't kick users",
                fields=[("description", "Reason", reason)],
                log_color=config.color.orange,
            )

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
        dur, del_after = None, None
        if delete_messages and delete_messages != "0":
            del_after = parse_duration(delete_messages, max_duration="7d")
            dur = int(del_after.total_seconds()) if del_after else None
        if resolved := await self._resolve(ctx, users, "ban"):
            await self._run(
                ctx,
                *resolved,
                action=lambda m: ctx.guild.ban(m, reason=reason, delete_message_seconds=dur),
                title="Mass Banned Users",
                summary="banned",
                error_title="Can't ban users",
                fields=[
                    ("description", "Reason", reason),
                    ("bin", "Delete Message Duration", f"`{format_timedelta(del_after, locale='en')}`"),
                ],
                log_color=config.color.red,
            )

    # Mass unban
    @mass.command(name="unban")
    @option(
        "users", description='Enter the user IDs whom you want to unban. Use " " to separate user IDs.', required=True
    )
    @option("reason", description="Enter the reason for unbanning the user", required=False)
    async def mass_unban_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Unbans mentioned users."""
        await ctx.defer()
        resolved = await self._resolve(
            ctx,
            users,
            "unban",
            check=lambda user: None,
            convert=lambda user: self.client.fetch_user(int(user)),
        )
        if resolved:
            await self._run(
                ctx,
                *resolved,
                action=lambda u: ctx.guild.unban(u, reason=reason),
                title="Mass Unbanned Users",
                summary="unbanned",
                error_title="Can't unban users",
                fields=[("description", "Reason", reason)],
                log_color=config.color.green,
            )

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
        try:
            dur: datetime.timedelta = parse_duration(duration)
        except ValueError as e:
            await ctx.respond(view=error_view(str(e)), ephemeral=True)
            return
        resolved = await self._resolve(
            ctx,
            users,
            "timeout",
            check=lambda m: (
                "You cannot use it on server owner." if m == ctx.guild.owner else self._hierarchy_error(ctx, m)
            ),
        )
        if resolved:
            await self._run(
                ctx,
                *resolved,
                action=lambda m: m.timeout_for(dur, reason=reason),
                title="Mass Timed out Users",
                summary="timed out",
                error_title="Can't timeout users",
                fields=[
                    ("duration", "Duration", f"`{format_timedelta(dur, locale='en')}`"),
                    ("description", "Reason", reason),
                ],
                log_color=config.color.orange,
            )

    # Mass untimeout users
    @mass.command(name="untimeout")
    @option(
        "users", description='Mention the users whom you want to untimeout. Use " " to separate users.', required=True
    )
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def mass_untimeout_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Untimeouts mentioned users."""
        await ctx.defer()
        if resolved := await self._resolve(ctx, users, "untimeout"):
            await self._run(
                ctx,
                *resolved,
                action=lambda m: m.timeout(None, reason=reason),
                title="Mass Untimed out Users",
                summary="untimed out",
                error_title="Can't untimeout users",
                fields=[("description", "Reason", reason)],
                log_color=config.color.green,
            )

    async def _mass_role(self, ctx: discord.ApplicationContext, users: str, roles: str, add: bool):
        """Adds or removes the given roles for the given users."""
        await ctx.defer()
        verb, past, prep = ("add", "added", "to") if add else ("remove", "removed", "from")
        if len(users.split()) > 10 or len(roles.split()) > 10:
            await ctx.respond(view=error_view(f"You can only mass {verb} 10 roles upto 10 users."), ephemeral=True)
            return
        _roles: list[discord.Role] = []
        errors: list[tuple] = []
        for role in roles.split():
            try:
                _role = await commands.RoleConverter().convert(ctx, role)
            except commands.BadArgument:
                errors.append((role, "Role not found."))
                continue
            if _role.position >= ctx.guild.me.top_role.position:
                errors.append((_role.mention, "Role has same or higher position than me."))
            else:
                _roles.append(_role)
        members: list[discord.Member] = []
        if _roles:
            members, user_errors = await self._resolve(ctx, users, f"{verb} roles")
            errors += user_errors
        await self._run(
            ctx,
            members,
            errors,
            action=lambda m: m.add_roles(*_roles) if add else m.remove_roles(*_roles),
            title=f"Mass {past.capitalize()} Roles",
            summary=f"{past} {len(_roles)} roles {prep}",
            error_title=f"Can't {verb} roles",
            fields=[("role", "Roles", ", ".join(role.mention for role in _roles))],
            log_color=None,
        )

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
        await self._mass_role(ctx, users, roles, add=True)

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
        await self._mass_role(ctx, users, roles, add=False)


def setup(client: Client):
    client.add_cog(MassModeration(client))
