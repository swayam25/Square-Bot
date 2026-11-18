import datetime
import discord
from babel.dates import format_timedelta
from discord import ui
from discord.commands import option, slash_command
from discord.ext import commands
from square.cogs.moderation.purge import Purge
from square.cogs.moderation.roles import Roles
from square.cogs.moderation.timeouts import TimeoutEnds
from square.cogs.moderation.warnings import Warnings
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, not_in_server, success_view
from square.utils import bans, config, mod_dm
from square.utils.emoji import emoji
from square.utils.helpers import fmt_user, parse_duration


def _dms_closed(messaged: bool) -> str:
    return "" if messaged else "\n-# They have DMs closed, so they weren't told."


class Moderation(
    Purge,
    Roles,
    Warnings,
    TimeoutEnds,
    Cog,
    name="Moderation",
    description="Moderate your server & keep it managed by using commands.",
    emoji=emoji.mod,
    order=1,
):
    def __init__(self, client: Client):
        self.client = client
        self.timeout_ends = {}

    @slash_command(name="kick")
    @discord.default_permissions(kick_members=True)
    @option("user", description="Mention the user whom you want to kick")
    @option("reason", description="Enter the reason for kicking the user", required=False)
    async def kick(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str = None):
        """Kicks the mentioned user."""
        if await not_in_server(ctx, user):
            return
        if user == ctx.author:
            view = error_view("You cannot use it on yourself")
            await ctx.respond(view=view, ephemeral=True)
        elif isinstance(user, discord.Member) and user.top_role.position >= ctx.author.top_role.position:
            view = error_view("Given user has same role or higher role than you")
            await ctx.respond(view=view, ephemeral=True)
        else:
            dm = mod_dm.view(
                ctx.guild,
                "You got kicked",
                config.color.orange,
                mod_dm.moderation_rows(reason, ctx.author),
                member=False,
            )
            messaged = await mod_dm.send_before(user, dm, user.kick(reason=reason))
            view = DesignerView(
                ui.Container(
                    ui.Section(
                        ui.TextDisplay("## Kicked User"),
                        ui.TextDisplay(
                            f"Successfully kicked {user.mention} (`{user.name}`) from the server.\n{emoji.description_green} **Reason**: {reason or 'No reason given'}"
                            + _dms_closed(messaged)
                        ),
                        accessory=ui.Thumbnail(url=user.display_avatar.url),
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    @slash_command(name="ban")
    @discord.default_permissions(ban_members=True)
    @option("user", description="Mention the user whom you want to ban.")
    @option(
        "delete_messages",
        description="Enter the duration of messages to delete. Ex: 1min, 2h, 7d (default), 0 (disable) etc...",
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
            view = error_view("You cannot use it on yourself")
            await ctx.respond(view=view, ephemeral=True)
        elif isinstance(user, discord.Member) and user.top_role.position >= ctx.author.top_role.position:
            view = error_view("Given user has same role or higher role than you")
            await ctx.respond(view=view, ephemeral=True)
        else:
            dur, del_after = None, None
            if delete_messages and delete_messages != "0":
                del_after = parse_duration(delete_messages, max_duration="7d")
                dur = int(del_after.total_seconds()) if del_after else None
            dm = mod_dm.view(
                ctx.guild,
                "You got banned",
                config.color.red,
                mod_dm.moderation_rows(reason, ctx.author),
                member=False,
            )
            removal = ctx.guild.ban(user, reason=reason, delete_message_seconds=dur)
            # A user outside the server shares no server with the bot, so a DM can't reach them
            if isinstance(user, discord.Member):
                messaged = await mod_dm.send_before(user, dm, removal)
            else:
                await removal
                messaged = True
            view = DesignerView(
                ui.Container(
                    ui.Section(
                        ui.TextDisplay("## Banned User"),
                        ui.TextDisplay(
                            f"Successfully banned {user.mention} (`{user.name}`) from the server.\n"
                            f"{emoji.id_green} **ID**: `{user.id}`\n"
                            f"{emoji.description_green} **Reason**: {reason or 'No reason given'}\n"
                            f"{emoji.bin_green} **Delete Message Duration**: {f'`{format_timedelta(del_after, locale="en")}`' if del_after else 'Kept all messages'}"
                            + _dms_closed(messaged)
                        ),
                        accessory=ui.Thumbnail(url=user.display_avatar.url),
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    @slash_command(name="unban")
    @discord.default_permissions(ban_members=True)
    @option(
        "user",
        description="Enter the username or ID of the user you want to unban",
        autocomplete=bans.autocomplete,
    )
    @option("reason", description="Enter the reason for unbanning the user", required=False)
    async def unban(self, ctx: discord.ApplicationContext, user: str, reason: str = None):
        """Unbans a user by their username or ID."""
        found = bans.find_cached(ctx.guild.id, user)
        if found is None:
            if bans.parse_id(user) is None:
                await ctx.defer()  # Reading a long ban list can outlast Discord's 3 second reply window
            found = await bans.lookup(ctx.guild, user)
        if found is None:
            view = error_view(f"`{user.replace('`', '')}` isn't banned here.")
            if ctx.response.is_done():
                # The deferred reply is public, so it goes and the refusal is sent privately instead
                await ctx.interaction.delete_original_response()
                await ctx.followup.send(view=view, ephemeral=True)
            else:
                await ctx.respond(view=view, ephemeral=True)
            return
        await ctx.guild.unban(found, reason=reason)
        await ctx.respond(view=success_view(f"Successfully unbanned {found.mention} (`{found.name}`)."))

    @commands.Cog.listener("on_member_ban")
    async def _ban_added(self, guild: discord.Guild, user: discord.User | discord.Member):
        # A Member's display name would carry their old nickname into the unban suggestions
        bans.remember(guild.id, self.client.get_user(user.id) or user)

    @commands.Cog.listener("on_member_unban")
    async def _ban_removed(self, guild: discord.Guild, user: discord.User):
        bans.forget(guild.id, user.id)

    @slash_command(name="timeout")
    @discord.default_permissions(moderate_members=True)
    @option("user", description="Mention the user whom you want to timeout")
    @option("duration", description="Enter the duration of timeout. Ex: 1d, 2w etc...")
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def timeout_user(
        self, ctx: discord.ApplicationContext, user: discord.Member, duration: str, reason: str = None
    ):
        """Timeouts the mentioned user."""
        if await not_in_server(ctx, user):
            return
        if user == ctx.author:
            view = error_view("You cannot use it on yourself.")
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = error_view("Given user has same role or higher role than you.")
            await ctx.respond(view=view, ephemeral=True)
        else:
            try:
                dur: datetime.timedelta = parse_duration(duration)
            except ValueError as e:
                view = error_view(f"{e}")
                await ctx.respond(view=view, ephemeral=True)
                return
            until = discord.utils.utcnow() + dur
            await user.timeout(until, reason=reason)
            messaged = await mod_dm.send(user, mod_dm.timed_out(ctx.guild, until, reason, ctx.author)) is not None
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Timed out User"),
                    ui.TextDisplay(
                        f"Successfully timed out {user.mention} (`{user.name}`).\n"
                        f"{emoji.duration_green} **Duration**: `{format_timedelta(dur, locale='en')}`\n"
                        f"{emoji.description_green} **Reason**: {reason or 'No reason given'}" + _dms_closed(messaged)
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    @slash_command(name="untimeout")
    @discord.default_permissions(moderate_members=True)
    @option("user", description="Mention the user whom you want to untimeout")
    @option("reason", description="Enter the reason for user timeout", required=False)
    async def untimeout_user(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str = None):
        """Untimeouts the mentioned user."""
        if await not_in_server(ctx, user):
            return
        if user == ctx.author:
            view = error_view("You cannot use it on yourself")
            await ctx.respond(view=view, ephemeral=True)
        elif user.top_role.position >= ctx.author.top_role.position:
            view = error_view("Given user has same role or higher role than you")
            await ctx.respond(view=view, ephemeral=True)
        else:
            was_timed_out = user.timed_out
            await user.timeout(None, reason=reason)
            messaged = True
            if was_timed_out:
                dm = mod_dm.view(
                    ctx.guild,
                    "Your timeout was removed",
                    config.color.green,
                    mod_dm.moderation_rows(reason, ctx.author),
                )
                messaged = await mod_dm.send(user, dm) is not None
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Untimed out User"),
                    ui.TextDisplay(
                        f"Successfully untimed out {user.mention} (`{user.name}`).\n{emoji.description_green} **Reason**: {reason or 'No reason given'}"
                        + _dms_closed(messaged)
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=view)

    @staticmethod
    async def _set_send_messages(
        ctx: discord.ApplicationContext, allow: bool | None
    ) -> discord.abc.GuildChannel | None:
        """
        Sets `send_messages` for @everyone in the current channel, keeping the rest of its overwrite.

        Replacing the whole overwrite would wipe denies like `view_channel` and expose private channels.
        Returns the channel, or None (after replying) if this channel has no permission overwrites, e.g. a thread.
        """
        channel = ctx.channel
        if ctx.guild is None or not isinstance(channel, discord.abc.GuildChannel):
            await ctx.respond(view=error_view("This channel can't be locked."), ephemeral=True)
            return None
        everyone = ctx.guild.default_role
        overwrite = channel.overwrites_for(everyone)
        overwrite.send_messages = allow
        await channel.set_permissions(
            everyone,
            overwrite=None if overwrite.is_empty() else overwrite,
            reason=f"{'Unlocked' if allow is None else 'Locked'} by {fmt_user(ctx.author)}",
        )
        return channel

    @slash_command(name="lock")
    @discord.default_permissions(manage_channels=True)
    @option("reason", description="Enter the reason for locking the channel", required=False)
    async def lock(self, ctx: discord.ApplicationContext, reason: str = None):
        """Locks the current channel."""
        if not (channel := await self._set_send_messages(ctx, False)):
            return
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Channel Locked"),
                ui.TextDisplay(
                    f"Successfully locked {channel.mention}.\n{emoji.description_green} **Reason**: {reason or 'No reason given'}"
                ),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    @slash_command(name="unlock")
    @discord.default_permissions(manage_channels=True)
    async def unlock(self, ctx: discord.ApplicationContext):
        """Unlocks the current channel."""
        if channel := await self._set_send_messages(ctx, None):  # None means inherited again, not a forced allow
            await ctx.respond(view=success_view(f"Successfully unlocked {channel.mention}."))


def setup(client: Client):
    client.add_cog(Moderation(client))
