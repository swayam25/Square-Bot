import discord
import time
from collections.abc import Callable
from discord import ui
from discord.commands import SlashCommandGroup, option
from square import logs
from square.cogs.moderation.common import role_refusal
from square.core import Client
from square.core.view import DesignerView, error_view, not_in_server, success_view
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_user, plural


class Roles:
    client: Client

    role = SlashCommandGroup(
        name="role",
        description="Role related commands.",
        default_member_permissions=discord.Permissions(manage_roles=True),
    )
    role_add = role.create_subgroup(name="add", description="Add role commands.")
    role_remove = role.create_subgroup(name="remove", description="Remove role commands.")

    async def _bulk_role(
        self,
        ctx: discord.ApplicationContext,
        role: discord.Role,
        add: bool,
        target: str,
        check: Callable[[discord.Member], bool],
    ):
        if error := role_refusal(ctx.author, role):
            await ctx.respond(view=error_view(error), ephemeral=True)
            return

        verb, past, prep = ("add", "added", "to") if add else ("remove", "removed", "from")
        members = [m for m in ctx.guild.members if check(m) and (role in m.roles) != add]
        if not members:
            view = error_view(f"No {target} found to {verb} {role.mention} {prep}.")
            await ctx.respond(view=view, ephemeral=True)
            return

        def progress_view(count: int) -> DesignerView:
            return DesignerView(
                ui.Container(
                    ui.TextDisplay(
                        f"{emoji.loading} {'Adding' if add else 'Removing'} {role.mention} {prep} {target}... "
                        f"`[{count}/{len(members)}]`"
                    ),
                )
            )

        msg = await ctx.respond(view=progress_view(0))
        errors: list[tuple] = []
        reason = f"Role {verb} {target} by {fmt_user(ctx.author)}"
        last_edit = time.monotonic()
        for count, member in enumerate(members, start=1):
            try:
                logs.acting(ctx.guild.id, discord.AuditLogAction.member_role_update, member.id, ctx.author)
                if add:
                    await member.add_roles(role, reason=reason)
                else:
                    await member.remove_roles(role, reason=reason)
            except discord.Forbidden:
                errors.append((f"{member.mention} (`{member.name}`)", "Missing permissions."))
            except discord.HTTPException as e:
                errors.append((f"{member.mention} (`{member.name}`)", e.text or "Something went wrong."))
            # Throttled so progress edits don't compete with the role updates for rate limits.
            if time.monotonic() - last_edit >= 2 and count < len(members):
                await msg.edit(view=progress_view(count))
                last_edit = time.monotonic()

        updated = len(members) - len(errors)
        if updated > 0:
            await msg.edit(
                view=success_view(
                    f"Successfully {past} {role.mention} {prep} `{updated}` {plural(updated, target[:-1], target)}."
                )
            )
        if errors:
            lines = [f"{emoji.bullet_red} {member}: {err}" for member, err in errors[:15]]
            if len(errors) > 15:
                lines.append(f"{emoji.bullet_red} *...and `{len(errors) - 15}` more.*")
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"## Can't {verb.capitalize()} Role"),
                    ui.TextDisplay("\n".join(lines)),
                    color=config.color.red,
                )
            )
            if updated > 0:
                await ctx.respond(view=view, ephemeral=True)
            else:
                await msg.edit(view=view)

    @role_add.command(name="user")
    @option("user", description="Who gets the role.")
    @option("role", description="The role to give.")
    async def add_role_user(self, ctx: discord.ApplicationContext, user: discord.Member, role: discord.Role):
        """Adds the mentioned role to the mentioned user."""
        if await not_in_server(ctx, user):
            return
        if user.top_role.position >= ctx.author.top_role.position:
            view = error_view("Given user has same role or higher role than you.")
            await ctx.respond(view=view, ephemeral=True)
            return
        if error := role_refusal(ctx.author, role):
            await ctx.respond(view=error_view(error), ephemeral=True)
            return
        logs.acting(ctx.guild.id, discord.AuditLogAction.member_role_update, user.id, ctx.author)
        await user.add_roles(role)
        view = success_view(f"Successfully added {role.mention} to {user.mention} (`{user.name}`).")
        await ctx.respond(view=view)

    @role_add.command(name="all")
    @option("role", description="The role to give every member.")
    async def add_role_all(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Adds the mentioned role to all members."""
        await self._bulk_role(ctx, role, add=True, target="members", check=lambda m: True)

    @role_add.command(name="bots")
    @option("role", description="The role to give every bot.")
    async def add_role_bots(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Adds the mentioned role to all bots."""
        await self._bulk_role(ctx, role, add=True, target="bots", check=lambda m: m.bot)

    @role_add.command(name="humans")
    @option("role", description="The role to give every human.")
    async def add_role_humans(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Adds the mentioned role to all humans."""
        await self._bulk_role(ctx, role, add=True, target="humans", check=lambda m: not m.bot)

    @role_remove.command(name="user")
    @option("user", description="Who loses the role.")
    @option("role", description="The role to take away.")
    async def remove_role_user(self, ctx: discord.ApplicationContext, user: discord.Member, role: discord.Role):
        """Removes the mentioned role from the mentioned user."""
        if await not_in_server(ctx, user):
            return
        if user.top_role.position >= ctx.author.top_role.position:
            view = error_view("Given user has same role or higher role than you.")
            await ctx.respond(view=view, ephemeral=True)
            return
        if error := role_refusal(ctx.author, role):
            await ctx.respond(view=error_view(error), ephemeral=True)
            return
        logs.acting(ctx.guild.id, discord.AuditLogAction.member_role_update, user.id, ctx.author)
        await user.remove_roles(role)
        view = success_view(f"Successfully removed {role.mention} from {user.mention} (`{user.name}`).")
        await ctx.respond(view=view)

    @role_remove.command(name="all")
    @option("role", description="The role to take from every member.")
    async def remove_role_all(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Removes the mentioned role from all members."""
        await self._bulk_role(ctx, role, add=False, target="members", check=lambda m: True)

    @role_remove.command(name="bots")
    @option("role", description="The role to take from every bot.")
    async def remove_role_bots(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Removes the mentioned role from all bots."""
        await self._bulk_role(ctx, role, add=False, target="bots", check=lambda m: m.bot)

    @role_remove.command(name="humans")
    @option("role", description="The role to take from every human.")
    async def remove_role_humans(self, ctx: discord.ApplicationContext, role: discord.Role):
        """Removes the mentioned role from all humans."""
        await self._bulk_role(ctx, role, add=False, target="humans", check=lambda m: not m.bot)
