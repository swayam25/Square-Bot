import discord
import secrets
from datetime import datetime
from square.db import cache
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import StarboardPostTable, StarboardTable, StarboardVoteTable
from tortoise.functions import Count, Sum
from tortoise.transactions import in_transaction
from typing import Any


def emoji_key(value: str | discord.PartialEmoji) -> str:
    """One key per emoji, however it was written: `⭐` and `⭐️` match, custom ones match by ID."""
    parsed = discord.PartialEmoji.from_str(value) if isinstance(value, str) else value
    return str(parsed.id) if parsed.id else (parsed.name or "").replace("\ufe0f", "")


def board_keys(board: StarboardTable) -> tuple[set[str], set[str]]:
    return {emoji_key(value) for value in board.emojis}, {emoji_key(value) for value in board.downvote_emojis}


def boards(guild_id: int) -> list[StarboardTable]:
    return cache.get(guild_id).starboards


async def create_board(guild_id: int, **values: Any) -> StarboardTable:
    guild = await fetch_guild_settings(guild_id)
    board = await StarboardTable.create(guild=guild, **values)
    cache.entry(guild_id).starboards.append(board)
    return board


def fetch_board(guild_id: int, board_id: int) -> StarboardTable | None:
    return next((board for board in boards(guild_id) if board.id == board_id), None)


def board_in(guild_id: int, channel_id: int) -> StarboardTable | None:
    return next((board for board in boards(guild_id) if board.channel_id == channel_id), None)


async def save_board(guild_id: int, board: StarboardTable, **values: Any) -> None:
    for key, value in values.items():
        setattr(board, key, value)
    await board.save(update_fields=list(values))
    if cached := fetch_board(guild_id, board.id):
        for key, value in values.items():
            setattr(cached, key, value)
    await prune_votes(guild_id)


async def delete_board(guild_id: int, board: StarboardTable) -> None:
    await board.delete()
    cache.entry(guild_id).starboards = [found for found in boards(guild_id) if found.id != board.id]
    await prune_votes(guild_id)


async def prune_votes(guild_id: int) -> None:
    keys = set()
    for board in boards(guild_id):
        up, down = board_keys(board)
        keys |= up | down
    await StarboardVoteTable.filter(guild__guild_id=guild_id).exclude(emoji__in=keys).delete()


async def add_vote(guild_id: int, message_id: int, channel_id: int, user_id: int, key: str) -> None:
    guild = await fetch_guild_settings(guild_id)
    await StarboardVoteTable.get_or_create(
        message_id=message_id, user_id=user_id, emoji=key, defaults={"guild": guild, "channel_id": channel_id}
    )


async def remove_vote(message_id: int, user_id: int, key: str) -> None:
    await StarboardVoteTable.filter(message_id=message_id, user_id=user_id, emoji=key).delete()


async def message_votes(message_id: int) -> list[tuple[int, str]]:
    """Every `(user_id, emoji key)` on a message."""
    return await StarboardVoteTable.filter(message_id=message_id).values_list("user_id", "emoji")


async def replace_votes(guild_id: int, message_id: int, channel_id: int, key: str, user_ids: list[int]) -> None:
    guild = await fetch_guild_settings(guild_id)
    async with in_transaction() as conn:
        await StarboardVoteTable.filter(message_id=message_id, emoji=key).using_db(conn).delete()
        await StarboardVoteTable.bulk_create(
            [
                StarboardVoteTable(
                    guild=guild, message_id=message_id, channel_id=channel_id, user_id=user_id, emoji=key
                )
                for user_id in set(user_ids)
            ],
            using_db=conn,
        )


async def drop_votes(message_ids: list[int], keys: set[str] | None = None) -> None:
    query = StarboardVoteTable.filter(message_id__in=message_ids)
    if keys is not None:
        query = query.filter(emoji__in=keys)
    await query.delete()


async def sweep(before: datetime) -> None:
    """Drops votes older than `before`, and post rows that never made a board or left it."""
    await StarboardVoteTable.filter(created_at__lt=before).delete()
    await StarboardPostTable.filter(post_id__isnull=True, created_at__lt=before).delete()


async def forget_channel(channel_id: int) -> None:
    """Votes go with the channel. Posts stay as history, the ones from boards in it lose their message."""
    await StarboardVoteTable.filter(channel_id=channel_id).delete()


async def fetch_post(board_id: int, message_id: int) -> StarboardPostTable | None:
    return await StarboardPostTable.filter(board_id=board_id, message_id=message_id).first()


async def fetch_by_post(post_id: int) -> StarboardPostTable | None:
    return await StarboardPostTable.filter(post_id=post_id).select_related("board", "board__guild").first()


async def posts_for(message_ids: list[int]) -> list[StarboardPostTable]:
    return await StarboardPostTable.filter(message_id__in=message_ids).select_related("board", "board__guild")


async def save_post(board: StarboardTable, message: discord.Message, **values: Any) -> StarboardPostTable:
    post, created = await StarboardPostTable.get_or_create(
        board=board,
        message_id=message.id,
        defaults={"channel_id": message.channel.id, "author_id": message.author.id, **values},
    )
    if not created and values:
        for key, value in values.items():
            setattr(post, key, value)
        await post.save(update_fields=list(values))
    return post


async def update_post(post: StarboardPostTable, **values: Any) -> None:
    for key, value in values.items():
        setattr(post, key, value)
    await post.save(update_fields=list(values))


async def clear_post_ids(board_ids: list[int]) -> None:
    await StarboardPostTable.filter(board_id__in=board_ids).update(post_id=None)


async def top_posts(board_ids: list[int], author_id: int | None, limit: int) -> list[StarboardPostTable]:
    query = StarboardPostTable.filter(board_id__in=board_ids, post_id__isnull=False)
    if author_id:
        query = query.filter(author_id=author_id)
    return await query.order_by("-score", "-id").limit(limit).select_related("board")


async def random_post(board_ids: list[int]) -> StarboardPostTable | None:
    query = StarboardPostTable.filter(board_id__in=board_ids, post_id__isnull=False)
    total = await query.count()
    if not total:
        return None
    return await query.order_by("id").offset(secrets.randbelow(total)).first().select_related("board")


async def user_stats(board_ids: list[int], user_id: int) -> dict[str, int]:
    totals = dict(
        await StarboardPostTable.filter(board_id__in=board_ids, post_id__isnull=False)
        .annotate(total=Sum("score"))
        .group_by("author_id")
        .values_list("author_id", "total")
    )
    received = int(totals.get(user_id) or 0)
    rank = 1 + sum(1 for total in totals.values() if total > received) if user_id in totals else 0
    scores = await StarboardPostTable.filter(
        board_id__in=board_ids, author_id=user_id, post_id__isnull=False
    ).values_list("score", flat=True)
    return {
        "received": received,
        "posts": len(scores),
        "best": max(scores, default=0),
        "rank": rank,
    }


async def post_counts(board_ids: list[int]) -> dict[int, int]:
    return dict(
        await StarboardPostTable.filter(board_id__in=board_ids, post_id__isnull=False)
        .annotate(n=Count("id"))
        .group_by("board_id")
        .values_list("board_id", "n")
    )
