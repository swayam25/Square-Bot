import asyncio
import datetime
import discord
from collections.abc import Callable
from discord.abc import Snowflake
from discord.commands import SlashCommandGroup, message_command, option
from square import logs
from square.core import Client
from square.core.view import error_view, success_view
from square.utils.helpers import fmt_user, plural

PurgeableChannel = discord.TextChannel | discord.VoiceChannel | discord.StageChannel | discord.Thread
# Discord's bulk delete refuses messages older than 14 days, a minute of margin covers clock drift
BULK_DELETE_MAX_AGE = datetime.timedelta(days=14) - datetime.timedelta(minutes=1)


async def purge_messages(
    channel: PurgeableChannel,
    *,
    limit: int | None,
    check: Callable[[discord.Message], bool] | None = None,
    before: Snowflake | None = None,
    after: Snowflake | None = None,
    oldest_first: bool | None = None,
    reason: str | None = None,
) -> tuple[int, int]:
    """
    Bulk-deletes matching messages 100 at a time, fetching the next page while the previous one is deleted.

    Unlike py-cord's `purge`, there is no fixed one-second sleep between chunks (the HTTP client already waits on
    real rate limits), and messages too old for bulk delete are skipped instead of deleted one request at a time.

    Args:
        channel: The channel to purge.
        limit (int | None): How many messages to look through, newest first unless `after` is given.
        check: Only messages it returns True for are deleted.
        before: Only look at messages before this one.
        after: Only look at messages after this one.
        oldest_first (bool | None): Read order, py-cord's default (oldest first when `after` is given) when None.
        reason (str | None): Shown in the audit log.

    Returns:
        tuple[int, int]: Messages deleted, and matching messages skipped for being older than 14 days.
    """
    cutoff = discord.utils.time_snowflake(discord.utils.utcnow() - BULK_DELETE_MAX_AGE)
    deletes: list[asyncio.Task[None]] = []
    batch: list[discord.Message] = []
    deleted = skipped = 0
    async for message in channel.history(limit=limit, before=before, after=after, oldest_first=oldest_first):
        if check is not None and not check(message):
            continue
        if message.id < cutoff:
            skipped += 1
            continue
        batch.append(message)
        if len(batch) == 100:
            deletes.append(asyncio.create_task(channel.delete_messages(batch, reason=reason)))
            deleted += len(batch)
            batch = []
    if batch:
        deletes.append(asyncio.create_task(channel.delete_messages(batch, reason=reason)))
        deleted += len(batch)
    results = await asyncio.gather(*deletes, return_exceptions=True)
    if errors := [r for r in results if isinstance(r, Exception) and not isinstance(r, discord.NotFound)]:
        raise errors[0]
    return deleted, skipped


class Purge:
    client: Client

    purge = SlashCommandGroup(
        name="purge",
        description="Purge related commands.",
        default_member_permissions=discord.Permissions(manage_messages=True),
    )

    async def _purge(self, ctx: discord.ApplicationContext, which: str, **kwargs) -> None:
        channel = ctx.channel
        if not isinstance(channel, PurgeableChannel):
            await ctx.respond(view=error_view("Messages can't be purged in this channel."), ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        logs.acting(ctx.guild.id, discord.AuditLogAction.message_bulk_delete, channel.id, ctx.author)
        deleted, skipped = await purge_messages(channel, reason=f"Purged by {fmt_user(ctx.author)}", **kwargs)
        note = f"\n-# Skipped `{skipped}` older than 14 days, Discord can't bulk delete those." if skipped else ""
        await ctx.respond(
            view=success_view(f"Successfully purged `{deleted}` {plural(deleted, 'message')}{which}.{note}"),
            ephemeral=True,
        )

    @purge.command(name="any")
    @option("amount", description="How many messages to check.", min_value=1, max_value=1000)
    async def purge_any(self, ctx: discord.ApplicationContext, amount: int):
        """Purges the newest messages."""
        await self._purge(ctx, "", limit=amount)

    @purge.command(name="humans")
    @option("amount", description="How many messages to check.", min_value=1, max_value=1000)
    async def purge_humans(self, ctx: discord.ApplicationContext, amount: int):
        """Purges messages sent by humans."""
        await self._purge(ctx, " sent by humans", limit=amount, check=lambda m: not m.author.bot)

    @purge.command(name="bots")
    @option("amount", description="How many messages to check.", min_value=1, max_value=1000)
    async def purge_bots(self, ctx: discord.ApplicationContext, amount: int):
        """Purges messages sent by bots."""
        await self._purge(ctx, " sent by bots", limit=amount, check=lambda m: m.author.bot)

    @purge.command(name="user")
    @option("amount", description="How many messages to check.", min_value=1, max_value=1000)
    @option("user", description="Whose messages to purge.")
    async def purge_user(self, ctx: discord.ApplicationContext, amount: int, user: discord.Member):
        """Purges messages sent by a user."""
        await self._purge(
            ctx,
            f" sent by {user.mention} (`{user.name}`)",
            limit=amount,
            check=lambda m: m.author.id == user.id,
        )

    @purge.command(name="contains")
    @option("amount", description="How many messages to check.", min_value=1, max_value=1000)
    @option("phrase", description="Purge messages that contain this.")
    async def purge_contains(self, ctx: discord.ApplicationContext, amount: int, phrase: str):
        """Purges messages that contain a phrase."""
        needle = phrase.lower()
        await self._purge(ctx, f" containing `{phrase}`", limit=amount, check=lambda m: needle in m.content.lower())

    # Message IDs are strings: Discord's integer options can't hold a 64-bit snowflake
    @purge.command(name="after")
    @option("message_id", description="Purge messages sent after this message ID.")
    @option("amount", description="How many messages to check.", min_value=1, max_value=1000, required=False)
    async def purge_after(self, ctx: discord.ApplicationContext, message_id: str, amount: int = 1000):
        """Purges messages sent after a message ID."""
        if not message_id.isdigit():
            await ctx.respond(view=error_view("Message ID must be a valid integer."), ephemeral=True)
            return
        await self._purge(ctx, f" after `{message_id}`", limit=amount, after=discord.Object(int(message_id)))

    @purge.command(name="from-to")
    @option(
        "from",
        description="The message ID to start at.",
        parameter_name="from_message_id",
    )
    @option("to", description="The message ID to stop at.", parameter_name="to_message_id")
    async def purge_from_to(self, ctx: discord.ApplicationContext, from_message_id: str, to_message_id: str):
        """Purges the messages between two message IDs."""
        if not from_message_id.isdigit() or not to_message_id.isdigit():
            await ctx.respond(view=error_view("Message IDs must be valid integers."), ephemeral=True)
            return
        low, high = sorted((int(from_message_id), int(to_message_id)))
        await self._purge(
            ctx,
            f" between `{low}` and `{high}`",
            limit=1000,
            after=discord.Object(low),
            before=discord.Object(high),
        )

    @message_command(
        name="Purge until here",
        default_member_permissions=discord.Permissions(manage_messages=True),
        contexts={discord.InteractionContextType.guild},
    )
    async def purge_until(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Purges every message from the newest one down to this one, up to 1000."""
        # Newest first, so past the cap the newest messages go and the oldest are what's left
        await self._purge(
            ctx,
            " down to the one you picked",
            limit=1000,
            after=discord.Object(message.id - 1),
            oldest_first=False,
        )
