import asyncio
import discord
import heapq
import io
import logging
import secrets
from datetime import UTC, datetime
from square.cogs.giveaways import cards, files
from square.core import Client
from square.db import cache
from square.db.funcs import giveaways as giveaways_db
from square.db.funcs import invites as invites_db
from square.db.schema import GiveawayTable
from square.modules import Module
from square.utils import storage
from square.utils.guard import Guard
from square.utils.helpers import fmt_count

log = logging.getLogger(__name__)

COUNT_DELAY = 3
# Long sleeps are cut short now and then, so a clock change can't leave one waiting for days
MAX_SLEEP = 3600
RETRY_DELAY = 60
# Editing a message without these strips the role ping, which also pulls it out of everyone's mentions
MENTIONS = discord.AllowedMentions(everyone=True, roles=True, users=False)

_random = secrets.SystemRandom()
_wake = asyncio.Event()
_counting: dict[int, asyncio.Task] = {}
rerolling = Guard()


def now() -> datetime:
    return datetime.now(UTC)


def wake() -> None:
    _wake.set()


def guild_of(client: Client, giveaway: GiveawayTable) -> discord.Guild | None:
    return client.get_guild(giveaway.guild.guild_id)


async def invite_totals(giveaway: GiveawayTable, guild_id: int, user_ids: list[int]) -> dict[int, int]:
    if not user_ids or not cards.needs_invites(giveaway, guild_id):
        return {}
    return await invites_db.fetch_totals(guild_id, user_ids)


def refusal(giveaway: GiveawayTable, member: discord.Member, invites: int = 0) -> str | None:
    has = {role.id for role in member.roles}
    guild_id = member.guild.id
    if blocked := [role_id for role_id in giveaway.blocked_role_ids if role_id in has]:
        return f"People with {cards.role_mention(guild_id, blocked[0])} can't enter this giveaway."
    if required := giveaway.required_role_ids:
        missing = [role_id for role_id in required if role_id not in has]
        if giveaway.require_all_roles and missing:
            return f"You need {', '.join(cards.role_mention(guild_id, role_id) for role_id in missing)} to enter."
        if not giveaway.require_all_roles and len(missing) == len(required):
            roles = ", ".join(cards.role_mention(guild_id, role_id) for role_id in required)
            return f"You need {roles} to enter." if len(required) == 1 else f"You need one of {roles} to enter."
    if giveaway.min_account_days and (now() - member.created_at).days < giveaway.min_account_days:
        return f"Your account needs to be at least {cards.days(giveaway.min_account_days)} old to enter."
    if giveaway.min_member_days and (
        not member.joined_at or (now() - member.joined_at).days < giveaway.min_member_days
    ):
        return f"You need to be in this server for at least {cards.days(giveaway.min_member_days)} to enter."
    if cards.needs_invites(giveaway, guild_id) and invites < giveaway.min_invites:
        return f"You need at least {cards.invites(giveaway.min_invites)} to enter. You have `{fmt_count(invites)}`."
    return None


def role_bonus(giveaway: GiveawayTable, member: discord.Member | None) -> int:
    """Bonus roles don't stack, the biggest one counts."""
    if member is None:
        return 0
    has = {role.id for role in member.roles}
    return max((entries for role_id, entries in giveaway.bonus_roles if role_id in has), default=0)


def weight(giveaway: GiveawayTable, member: discord.Member | None, bonus: int) -> int:
    return 1 + role_bonus(giveaway, member) + bonus


async def draw(guild: discord.Guild, giveaway: GiveawayTable, count: int) -> list[int]:
    """
    Weighted sampling without replacement (Efraimidis-Spirakis): key = `random() ** (1 / weight)`, top keys win.

    Skips anyone drawn before, gone, a bot or no longer qualifying.
    """
    drawn = set(giveaway.drawn_ids)
    keyed: list[tuple[float, int]] = []
    entries = await giveaways_db.fetch_entries(giveaway.id)
    totals = await invite_totals(giveaway, guild.id, [user_id for user_id, _, _ in entries])
    for user_id, bonus, _ in entries:
        member = guild.get_member(user_id)
        if user_id in drawn or member is None or member.bot or refusal(giveaway, member, totals.get(user_id, 0)):
            continue
        keyed.append((_random.random() ** (1 / weight(giveaway, member, bonus)), user_id))
    return [user_id for _, user_id in heapq.nlargest(count, keyed)]


async def _message(client: Client, giveaway: GiveawayTable) -> discord.PartialMessage | None:
    if not giveaway.message_id:
        return None
    channel = client.get_channel(giveaway.channel_id)
    if not isinstance(channel, discord.TextChannel | discord.Thread | discord.VoiceChannel):
        return None
    return channel.get_partial_message(giveaway.message_id)


async def redraw(client: Client, giveaway: GiveawayTable) -> None:
    if message := await _message(client, giveaway):
        try:
            await message.edit(view=cards.giveaway_card(giveaway, giveaway.guild.guild_id), allowed_mentions=MENTIONS)
        except discord.NotFound:
            pass
        except discord.HTTPException:
            log.warning("Couldn't update giveaway %d's message", giveaway.id, exc_info=True)


def recount(client: Client, giveaway_id: int) -> None:
    """Redraws the entry count after `COUNT_DELAY`, once for every press in that window."""
    if giveaway_id not in _counting:
        _counting[giveaway_id] = asyncio.create_task(_recount_later(client, giveaway_id))


async def _recount_later(client: Client, giveaway_id: int) -> None:
    try:
        await asyncio.sleep(COUNT_DELAY)
    finally:
        _counting.pop(giveaway_id, None)
    giveaway = await giveaways_db.fetch_giveaway_by_id(giveaway_id)
    if giveaway and giveaway.status == "running":
        await redraw(client, giveaway)


async def post(client: Client, giveaway: GiveawayTable, image: bytes | None = None) -> bool:
    """
    False when it already started or couldn't post. The stored image is deleted either way.

    Giveaways starting right away are created running, so the scheduler can't post them twice.
    """
    if giveaway.status == "scheduled" and not await giveaways_db.move_status(
        giveaway, "scheduled", "running", starts_at=min(giveaway.starts_at, now())
    ):
        return False
    guild_id = giveaway.guild.guild_id
    if giveaway.image_file and image is None:
        try:
            image = await files.load(guild_id, giveaway.id, giveaway.image_file)
        except storage.ERRORS:
            log.warning("Couldn't read giveaway %d's image, posting it without one", giveaway.id, exc_info=True)
        if image is None:
            await giveaways_db.save_giveaway(giveaway, image_file=None)
    guild = guild_of(client, giveaway)
    channel = guild.get_channel(giveaway.channel_id) if guild else None
    try:
        if not isinstance(channel, discord.TextChannel | discord.Thread | discord.VoiceChannel):
            raise LookupError("channel")
        attached = [attachment(giveaway.image_file, image)] if giveaway.image_file and image else []
        message = await channel.send(
            view=cards.giveaway_card(giveaway, channel.guild.id), files=attached, allowed_mentions=MENTIONS
        )
    except discord.HTTPException, LookupError:
        log.warning("Couldn't post giveaway %d, so it ended without a message", giveaway.id, exc_info=True)
        await giveaways_db.save_giveaway(giveaway, status="ended", ended_at=now())
        return False
    finally:
        if giveaway.image_file:
            await files.drop(guild_id, giveaway.id)
    await giveaways_db.save_giveaway(giveaway, message_id=message.id)
    wake()
    return True


def attachment(name: str, raw: bytes) -> discord.File:
    return discord.File(io.BytesIO(raw), filename=name)


async def swap_image(client: Client, giveaway: GiveawayTable, name: str | None, raw: bytes | None) -> bool:
    """Saves only once Discord took the file. False when the message is gone or Discord refused it."""
    message = await _message(client, giveaway)
    if message is None:
        return False
    previous = giveaway.image_file
    giveaway.image_file = name
    try:
        # A partial message can't send files
        full = await message.fetch()
        await full.edit(
            view=cards.giveaway_card(giveaway, giveaway.guild.guild_id),
            files=[attachment(name, raw)] if name and raw else [],
            attachments=[],
            allowed_mentions=MENTIONS,
        )
    except discord.HTTPException:
        giveaway.image_file = previous
        log.warning("Couldn't change giveaway %d's image", giveaway.id, exc_info=True)
        return False
    await giveaways_db.save_giveaway(giveaway, image_file=name)
    return True


async def finish(client: Client, giveaway: GiveawayTable) -> bool:
    """False when it had already ended."""
    if not await giveaways_db.move_status(giveaway, "running", "ended", ended_at=now()):
        return False
    winners: list[int] = []
    if guild := guild_of(client, giveaway):
        winners = await draw(guild, giveaway, giveaway.winner_count)
    await giveaways_db.save_giveaway(giveaway, winner_ids=winners, drawn_ids=winners)
    await redraw(client, giveaway)
    await _announce(client, giveaway, winners)
    return True


async def reroll(client: Client, giveaway: GiveawayTable, replace: list[int] | None = None) -> list[int]:
    """Swaps out `replace` (all winners when None). With fewer people left than asked for, only that many change."""
    guild = guild_of(client, giveaway)
    if guild is None:
        return []
    outgoing = [user_id for user_id in giveaway.winner_ids if replace is None or user_id in replace]
    new = await draw(guild, giveaway, giveaway.winner_count if replace is None else len(outgoing))
    if not new:
        return []
    swapped = set(outgoing[: len(new)])
    kept = [user_id for user_id in giveaway.winner_ids if user_id not in swapped]
    await giveaways_db.save_giveaway(giveaway, winner_ids=kept + new, drawn_ids=giveaway.drawn_ids + new)
    await redraw(client, giveaway)
    await _announce(client, giveaway, new, reroll=True)
    return new


async def _announce(client: Client, giveaway: GiveawayTable, winners: list[int], *, reroll: bool = False) -> None:
    if message := await _message(client, giveaway):
        try:
            await message.reply(
                view=cards.winners_card(giveaway, winners, reroll=reroll),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False, replied_user=False),
            )
        except discord.HTTPException:
            log.warning("Couldn't announce giveaway %d's winners", giveaway.id, exc_info=True)
    if winners and giveaway.winner_role_id and (guild := guild_of(client, giveaway)):
        role = guild.get_role(giveaway.winner_role_id)
        for user_id in winners:
            if role and (member := guild.get_member(user_id)) and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Won the giveaway: {giveaway.prize}"[:512])
                except discord.HTTPException:
                    log.warning("Couldn't give giveaway %d's winner role", giveaway.id, exc_info=True)
                    break


async def remove(client: Client, giveaway: GiveawayTable) -> None:
    message = await _message(client, giveaway)
    await giveaways_db.delete_giveaway(giveaway)
    if giveaway.image_file:
        await files.drop(giveaway.guild.guild_id, giveaway.id)
    if message:
        try:
            await message.delete()
        except discord.HTTPException:
            pass


async def schedule(client: Client) -> None:
    """
    Sleeps until the next start or end, and `wake()` cuts it short.

    Scheduled giveaways wait while the module is off, running ones still end on time.
    """
    while True:
        _wake.clear()
        delay: float = MAX_SLEEP
        try:
            startable = cache.guild_ids_with_module(Module.GIVEAWAYS)
            starting, ending = await giveaways_db.fetch_due(now(), startable)
            stuck = False
            for giveaway in starting:
                if guild_of(client, giveaway) is None:
                    stuck = True
                else:
                    await post(client, giveaway)
            for giveaway in ending:
                if guild_of(client, giveaway) is None:
                    stuck = True
                else:
                    await finish(client, giveaway)
            if due := await giveaways_db.next_due(startable):
                delay = min(delay, max((due - now()).total_seconds(), RETRY_DELAY if stuck else 0))
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("The giveaway scheduler failed, retrying in %ds", RETRY_DELAY)
            delay = RETRY_DELAY
        try:
            await asyncio.wait_for(_wake.wait(), delay)
        except TimeoutError:
            pass


async def redraw_invite_rules(client: Client, guild_id: int) -> None:
    for giveaway in await giveaways_db.fetch_running_with_invites(guild_id):
        await redraw(client, giveaway)


async def redraw_running(client: Client) -> None:
    """Catches counts that changed right before a restart."""
    for giveaway in await giveaways_db.fetch_running():
        if guild_of(client, giveaway):
            await redraw(client, giveaway)
