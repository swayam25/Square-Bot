import asyncio
import discord
import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from square.cogs.starboard import delivery
from square.cogs.starboard.cards import Tally, vote_emoji
from square.core import Client
from square.db import cache
from square.db.funcs import starboard as starboard_db
from square.db.funcs.starboard import board_keys, emoji_key
from square.db.schema import StarboardPostTable, StarboardTable
from square.modules import Module

log = logging.getLogger(__name__)

DELAY = 2
_STARRABLE = (discord.MessageType.default, discord.MessageType.reply)

_pending: dict[int, asyncio.Task] = {}
_running: set[int] = set()
_again: set[int] = set()


def active_boards(guild_id: int) -> list[StarboardTable]:
    if not cache.enabled(guild_id, Module.STARBOARD):
        return []
    return [board for board in starboard_db.boards(guild_id) if board.enabled]


def _parent(channel: discord.abc.GuildChannel | discord.Thread) -> discord.abc.GuildChannel:
    return channel.parent if isinstance(channel, discord.Thread) and channel.parent else channel


def channel_ok(board: StarboardTable, channel: discord.abc.GuildChannel | discord.Thread) -> bool:
    guild = channel.guild
    target = guild.get_channel(board.channel_id)
    if target is None or channel.id in {found.channel_id for found in starboard_db.boards(guild.id)}:
        return False
    parent = _parent(channel)
    ids = {channel.id, parent.id, getattr(parent, "category_id", None)}
    if board.channel_mode == "only" and not ids & set(board.channel_ids):
        return False
    if board.channel_mode == "except" and ids & set(board.channel_ids):
        return False
    # Fixed on purpose: a post from an age-restricted channel never lands where everyone can see it
    return not getattr(parent, "nsfw", False) or getattr(target, "nsfw", False)


def boards_for(guild_id: int, channel: discord.abc.GuildChannel | discord.Thread, key: str) -> list[StarboardTable]:
    return [
        board
        for board in active_boards(guild_id)
        if key in set.union(*board_keys(board)) and channel_ok(board, channel)
    ]


def _blocked(board: StarboardTable, member: discord.Member | discord.User | None) -> bool:
    if not isinstance(member, discord.Member) or not board.blocked_role_ids:
        return False
    return any(role.id in board.blocked_role_ids for role in member.roles)


def eligible(board: StarboardTable, message: discord.Message) -> bool:
    if message.type not in _STARRABLE or not isinstance(message.channel, discord.abc.GuildChannel | discord.Thread):
        return False
    if not channel_ok(board, message.channel):
        return False
    if (message.author.bot or message.webhook_id) and not board.allow_bots:
        return False
    if _blocked(board, message.author):
        return False
    return not board.max_age_days or datetime.now(UTC) - message.created_at <= timedelta(days=board.max_age_days)


def score(board: StarboardTable, message: discord.Message, votes: list[tuple[int, str]]) -> Tally:
    """
    Each vote emoji is counted on its own and the best one wins, so 2 ⭐ and 1 🔥 make 2 ⭐, not 3.

    Downvoters take one each, however many downvote emojis they used.
    """
    guild = message.guild
    _, down = board_keys(board)

    def counts(user_id: int) -> bool:
        if user_id == message.author.id and not board.self_vote:
            return False
        member = guild.get_member(user_id) if guild else None
        return not (member and (member.bot or _blocked(board, member)))

    voters: dict[str, set[int]] = {emoji_key(text): set() for text in board.emojis}
    downs: set[int] = set()
    for user_id, key in votes:
        if (key in voters or key in down) and counts(user_id):
            (voters[key] if key in voters else downs).add(user_id)
    # max keeps the first of a tie, so the board's earlier emoji wins
    best = max(board.emojis, key=lambda text: len(voters[emoji_key(text)]), default=vote_emoji(board))
    return Tally(len(voters.get(emoji_key(best), ())) - len(downs), best)


async def sync_votes(message: discord.Message, keys: set[str]) -> list[tuple[int, str]]:
    """Votes added while Square was away only show as a count mismatch, so those emojis get read again."""
    assert message.guild is not None
    stored = await starboard_db.message_votes(message.id)
    counts = Counter(key for _, key in stored)
    present: set[str] = set()
    changed = False
    for reaction in message.reactions:
        if (key := emoji_key(reaction.emoji)) not in keys:
            continue
        present.add(key)
        if reaction.count == counts.get(key, 0):
            continue
        users = [user.id async for user in reaction.users(limit=None)]
        if reaction.burst:
            users += [user.id async for user in reaction.users(limit=None, type=discord.ReactionType.burst)]
        await starboard_db.replace_votes(message.guild.id, message.id, message.channel.id, key, users)
        changed = True
    if stale := {key for key in counts if key in keys and key not in present}:
        await starboard_db.drop_votes([message.id], stale)
        changed = True
    return await starboard_db.message_votes(message.id) if changed else stored


def schedule(client: Client, guild_id: int, channel_id: int, message_id: int) -> None:
    """Refreshes after `DELAY`, once for every vote in that window."""
    if message_id not in _pending:
        _pending[message_id] = asyncio.create_task(_later(client, guild_id, channel_id, message_id))


async def _later(client: Client, guild_id: int, channel_id: int, message_id: int) -> None:
    try:
        await asyncio.sleep(DELAY)
    finally:
        _pending.pop(message_id, None)
    await refresh(client, guild_id, channel_id, message_id)


async def refresh(client: Client, guild_id: int, channel_id: int, message_id: int) -> None:
    """Runs one at a time per message. A call while one runs makes it go once more instead."""
    if message_id in _running:
        _again.add(message_id)
        return
    _running.add(message_id)
    try:
        while True:
            _again.discard(message_id)
            try:
                await _refresh(client, guild_id, channel_id, message_id)
            except Exception:
                log.exception("Couldn't refresh message %d on the starboard", message_id)
            if message_id not in _again:
                break
    finally:
        _running.discard(message_id)


async def fetch(client: Client, guild_id: int, channel_id: int, message_id: int) -> discord.Message | None:
    guild = client.get_guild(guild_id)
    channel = guild.get_channel_or_thread(channel_id) if guild else None
    if not isinstance(channel, discord.abc.Messageable):
        return None
    return await channel.fetch_message(message_id)


async def _refresh(client: Client, guild_id: int, channel_id: int, message_id: int) -> None:
    if not (boards := active_boards(guild_id)):
        return
    try:
        message = await fetch(client, guild_id, channel_id, message_id)
    except discord.NotFound:
        await source_gone(client, [message_id])
        return
    except discord.HTTPException:
        return
    if message is None:
        return
    votes = await sync_votes(message, set().union(*(set.union(*board_keys(board)) for board in boards)))
    posts = {post.board_id: post for post in await starboard_db.posts_for([message.id])}
    for board in boards:
        post = posts.get(board.id)
        if (ok := eligible(board, message)) or post:
            await apply(client, board, message, post, score(board, message, votes), ok)


async def apply(
    client: Client,
    board: StarboardTable,
    message: discord.Message,
    post: StarboardPostTable | None,
    tally: Tally,
    ok: bool = True,
) -> None:
    if post and post.post_id:
        if post.forced or board.drop_below is None or tally.points >= board.drop_below:
            await _update(client, board, message, post, tally)
        else:
            await take_down(client, board, post, score=tally.points, emoji=tally.emoji)
    elif (post and post.forced) or (ok and tally.points >= board.threshold):
        await _post(client, board, message, tally)
    elif post and (post.score, post.emoji) != tally:
        await starboard_db.update_post(post, score=tally.points, emoji=tally.emoji)


async def _post(client: Client, board: StarboardTable, message: discord.Message, tally: Tally) -> None:
    if sent := await delivery.send(client, board, message, tally):
        post_id, webhook_id, uploads = sent
        await starboard_db.save_post(
            board,
            message,
            post_id=post_id,
            webhook_id=webhook_id,
            score=tally.points,
            emoji=tally.emoji,
            uploaded=delivery.stored(uploads),
        )


async def _update(
    client: Client, board: StarboardTable, message: discord.Message, post: StarboardPostTable, tally: Tally
) -> None:
    uploads = await delivery.edit(client, board, message, post, tally)
    if uploads is not None:
        await starboard_db.update_post(post, score=tally.points, emoji=tally.emoji, uploaded=delivery.stored(uploads))
        return
    # Its webhook changed or the post vanished, so a fresh one replaces it
    await take_down(client, board, post, score=tally.points, emoji=tally.emoji)
    await _post(client, board, message, tally)


async def take_down(client: Client, board: StarboardTable, post: StarboardPostTable, **values) -> None:
    """Clears the post ID before deleting, so the delete event doesn't read it as a moderator removing it."""
    post_id, webhook_id = post.post_id, post.webhook_id
    await starboard_db.update_post(post, post_id=None, webhook_id=None, **values)
    if post_id:
        await delivery.delete(client, board, post_id, webhook_id)


async def remove(client: Client, board: StarboardTable, post: StarboardPostTable) -> None:
    """
    Takes a message off the board and clears the board's emojis from it.

    Nothing blocks it: if people vote it up again, it comes back.
    """
    await take_down(client, board, post, score=0, emoji=None, forced=False)
    keys = set.union(*board_keys(board))
    await starboard_db.drop_votes([post.message_id], keys)
    try:
        message = await fetch(client, board.guild.guild_id, post.channel_id, post.message_id)
    except discord.HTTPException:
        return
    for reaction in message.reactions if message else []:
        if emoji_key(reaction.emoji) in keys:
            try:
                await reaction.clear()
            except discord.HTTPException:
                pass


async def source_gone(client: Client, message_ids: list[int]) -> None:
    for post in await starboard_db.posts_for(message_ids):
        if post.post_id and not post.board.follow_deletes:
            continue
        await take_down(client, post.board, post)
        await post.delete()
    await starboard_db.drop_votes(message_ids)


async def post_gone(client: Client, post_ids: list[int]) -> None:
    """Someone deleted a post by hand, which works like Remove."""
    for post_id in post_ids:
        if post := await starboard_db.fetch_by_post(post_id):
            await remove(client, post.board, post)
