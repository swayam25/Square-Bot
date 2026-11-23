import asyncio
import datetime
import discord
from babel.dates import format_timedelta
from collections.abc import Awaitable, Callable
from discord import ui
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from square import logs
from square.cogs.moderation.common import role_refusal
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view
from square.utils import bans, config, mod_dm
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count, parse_duration, plural


class MassModeration(Cog, name="Mass Moderation", description="Moderate your server in bulk.", order=2):
    def __init__(self, client: Client):
        self.client = client

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
        missing: str = "User not found.",
    ) -> tuple[list, list[tuple]] | None:
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
                errors.append((f"`{user.replace('`', '')}`", missing))
                continue
            if error := check(_user):
                errors.append((f"{_user.mention} (`{_user.name}`)", error))
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
    ) -> DesignerView:
        suffix = {config.color.red: "_red", config.color.orange: "_orange", config.color.green: "_green"}.get(color, "")

        def icon(name: str) -> str:
            return getattr(emoji, f"{name}{suffix}")

        lines = [f"Successfully {summary} {fmt_count(len(users))} {plural(len(users), 'user')}."]
        lines += [f"{icon(name)} **{label}**: {value}" for name, label, value in fields]
        lines.append(f"{icon('user')} **Users**: {', '.join(users)}")
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
        audit: discord.AuditLogAction,
    ):
        done: list[str] = []
        for target in targets:
            logs.acting(ctx.guild.id, audit, target.id, ctx.author)
        results = await asyncio.gather(*(action(target) for target in targets), return_exceptions=True)
        for target, result in zip(targets, results, strict=True):
            if isinstance(result, discord.HTTPException):
                errors.append((f"{target.mention} (`{target.name}`)", result.text or "Something went wrong."))
            elif isinstance(result, BaseException):
                raise result
            else:
                done.append(f"{target.mention} (`{target.name}`)")
        if done:
            await ctx.respond(view=self._result_view(title, summary, done, fields, config.color.green))
        if errors:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"## {error_title}"),
                    ui.TextDisplay("\n".join(f"{emoji.bullet_red} {obj}: {error}" for obj, error in errors)),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    @mass.command(name="kick")
    @option("users", description="Who to kick. Separate them with spaces.", required=True)
    @option("reason", description="Why they're kicked.", required=False)
    async def mass_kick_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Kicks the mentioned users."""
        await ctx.defer()
        if resolved := await self._resolve(ctx, users, "kick"):
            await self._run(
                ctx,
                *resolved,
                action=lambda m: mod_dm.send_before(
                    m,
                    mod_dm.view(
                        ctx.guild,
                        "You got kicked",
                        config.color.orange,
                        mod_dm.moderation_rows(reason, ctx.author),
                        member=False,
                    ),
                    m.kick(reason=reason),
                ),
                title="Mass Kicked Users",
                summary="kicked",
                error_title="Can't Kick Users",
                fields=[("note", "Reason", reason or "No reason given")],
                audit=discord.AuditLogAction.kick,
            )

    @mass.command(name="ban")
    @option("users", description="Who to ban. Separate them with spaces.", required=True)
    @option(
        "delete_messages",
        description="How far back to delete their messages, like 1h or 7d (default). 0 deletes none.",
        required=False,
    )
    @option("reason", description="Why they're banned.", required=False)
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
                action=lambda m: mod_dm.send_before(
                    m,
                    mod_dm.view(
                        ctx.guild,
                        "You got banned",
                        config.color.red,
                        mod_dm.moderation_rows(reason, ctx.author),
                        member=False,
                    ),
                    ctx.guild.ban(m, reason=reason, delete_message_seconds=dur),
                ),
                title="Mass Banned Users",
                summary="banned",
                error_title="Can't Ban Users",
                fields=[
                    ("note", "Reason", reason or "No reason given"),
                    (
                        "bin",
                        "Delete Message Duration",
                        f"`{format_timedelta(del_after, locale='en')}`" if del_after else "Kept all messages",
                    ),
                ],
                audit=discord.AuditLogAction.ban,
            )

    @mass.command(name="unban")
    @option(
        "users",
        description="Usernames or IDs to unban. Separate them with spaces.",
        required=True,
    )
    @option("reason", description="Why they're unbanned.", required=False)
    async def mass_unban_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Unbans the given users."""
        await ctx.defer()
        banned = await bans.banned_users(ctx.guild)

        async def convert(text: str) -> discord.User:
            if user := bans.find(banned, text):
                return user
            raise ValueError(text)

        resolved = await self._resolve(
            ctx, users, "unban", check=lambda user: None, convert=convert, missing="Isn't banned here."
        )
        if resolved:
            await self._run(
                ctx,
                *resolved,
                action=lambda u: ctx.guild.unban(u, reason=reason),
                title="Mass Unbanned Users",
                summary="unbanned",
                error_title="Can't Unban Users",
                fields=[("note", "Reason", reason or "No reason given")],
                audit=discord.AuditLogAction.unban,
            )

    @mass.command(name="timeout")
    @option("users", description="Who to time out. Separate them with spaces.", required=True)
    @option("duration", description="How long it lasts, like 10min, 1d or 2w.")
    @option("reason", description="Why they're timed out.", required=False)
    async def mass_timeout_users(self, ctx: discord.ApplicationContext, users: str, duration: str, reason: str = None):
        """Times out the mentioned users."""
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

        async def timeout(member: discord.Member) -> None:
            until = discord.utils.utcnow() + dur
            await member.timeout(until, reason=reason)
            await mod_dm.send(member, mod_dm.timed_out(ctx.guild, until, reason, ctx.author))

        if resolved:
            await self._run(
                ctx,
                *resolved,
                action=timeout,
                title="Mass Timed Out Users",
                summary="timed out",
                error_title="Can't Timeout Users",
                fields=[
                    ("duration", "Duration", f"`{format_timedelta(dur, locale='en')}`"),
                    ("note", "Reason", reason or "No reason given"),
                ],
                audit=discord.AuditLogAction.member_update,
            )

    @mass.command(name="untimeout")
    @option("users", description="Whose timeouts to remove. Separate them with spaces.", required=True)
    @option("reason", description="Why their timeouts are removed.", required=False)
    async def mass_untimeout_users(self, ctx: discord.ApplicationContext, users: str, reason: str = None):
        """Removes the mentioned users' timeouts."""
        await ctx.defer()

        async def untimeout(member: discord.Member) -> None:
            was_timed_out = member.timed_out
            await member.timeout(None, reason=reason)
            if was_timed_out:
                dm = mod_dm.view(
                    ctx.guild,
                    "Your timeout was removed",
                    config.color.green,
                    mod_dm.moderation_rows(reason, ctx.author),
                )
                await mod_dm.send(member, dm)

        if resolved := await self._resolve(ctx, users, "untimeout"):
            await self._run(
                ctx,
                *resolved,
                action=untimeout,
                title="Mass Untimed Out Users",
                summary="untimed out",
                error_title="Can't Untimeout Users",
                fields=[("note", "Reason", reason or "No reason given")],
                audit=discord.AuditLogAction.member_update,
            )

    async def _mass_role(self, ctx: discord.ApplicationContext, users: str, roles: str, add: bool):
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
                errors.append((f"`{role.replace('`', '')}`", "Role not found."))
                continue
            if refusal := role_refusal(ctx.author, _role):
                errors.append((_role.mention, refusal))
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
            summary=f"{past} {fmt_count(len(_roles))} {plural(len(_roles), 'role')} {prep}",
            error_title=f"Can't {verb.capitalize()} Roles",
            fields=[("role", "Roles", ", ".join(role.mention for role in _roles))],
            audit=discord.AuditLogAction.member_role_update,
        )

    @mass.command(name="role-add")
    @option(
        "users",
        description="Who gets the roles. Separate them with spaces.",
        required=True,
    )
    @option(
        "roles",
        description="The roles to give. Separate them with spaces.",
        required=True,
    )
    async def mass_role_add(self, ctx: discord.ApplicationContext, users: str, roles: str):
        """Adds the mentioned roles to the mentioned users."""
        await self._mass_role(ctx, users, roles, add=True)

    @mass.command(name="role-remove")
    @option(
        "users",
        description="Who loses the roles. Separate them with spaces.",
        required=True,
    )
    @option(
        "roles",
        description="The roles to take away. Separate them with spaces.",
        required=True,
    )
    async def mass_role_remove(self, ctx: discord.ApplicationContext, users: str, roles: str):
        """Removes the mentioned roles from the mentioned users."""
        await self._mass_role(ctx, users, roles, add=False)


def setup(client: Client):
    client.add_cog(MassModeration(client))
