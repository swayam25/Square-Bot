import discord
from litestar import Router, delete, get, patch, post
from litestar.di import Provide
from litestar.params import Parameter
from msgspec import UNSET, structs
from square.api import resolve
from square.api.auth import provide_guild
from square.api.refusals import REFUSED, refused
from square.api.resolve import SettingError
from square.api.schemas import (
    MAX_STARBOARDS,
    Starboard,
    StarboardCreate,
    StarboardPatch,
)
from square.core import Client
from square.db.funcs import starboard as starboard_db
from square.db.funcs.starboard import emoji_key
from square.db.schema import StarboardTable
from square.modules import Module
from typing import Annotated, Any

BoardId = Annotated[int, Parameter(ge=1, le=2**31 - 1)]
_SOURCES = (
    discord.TextChannel,
    discord.ForumChannel,
    discord.VoiceChannel,
    discord.StageChannel,
    discord.CategoryChannel,
)


def _out(board: StarboardTable, posts: int) -> Starboard:
    return Starboard(
        id=board.id,
        channel_id=str(board.channel_id),
        enabled=board.enabled,
        emojis=board.emojis,
        downvote_emojis=board.downvote_emojis,
        threshold=board.threshold,
        drop_below=board.drop_below,
        self_vote=board.self_vote,
        allow_bots=board.allow_bots,
        channel_mode=board.channel_mode,  # type: ignore[arg-type]
        channel_ids=[str(channel_id) for channel_id in board.channel_ids],
        blocked_role_ids=[str(role_id) for role_id in board.blocked_role_ids],
        max_age_days=board.max_age_days,
        follow_deletes=board.follow_deletes,
        color=board.color,
        posts=posts,
    )


async def _all(guild: discord.Guild) -> list[Starboard]:
    boards = starboard_db.boards(guild.id)
    counts = await starboard_db.post_counts([board.id for board in boards])
    return [_out(board, counts.get(board.id, 0)) for board in boards]


def _found(guild: discord.Guild, board_id: int) -> StarboardTable:
    if board := starboard_db.fetch_board(guild.id, board_id):
        return board
    raise SettingError("That starboard is gone. It may have been deleted.")


def _board_channel(guild: discord.Guild, channel_id: str, board_id: int | None = None) -> int:
    channel = resolve.text_channel(guild, channel_id)
    assert channel is not None
    if (taken := starboard_db.board_in(guild.id, channel.id)) and taken.id != board_id:
        raise SettingError(f"#{channel.name} is already a starboard.")
    perms = channel.permissions_for(guild.me)
    if not (perms.view_channel and perms.send_messages and perms.attach_files):
        raise SettingError(f"Square can't send messages with files in #{channel.name}.")
    return channel.id


def _emojis(client: Client, values: list[str]) -> list[str]:
    picked: dict[str, str] = {}
    for value in values:
        text = resolve.emoji(client, value)
        assert text is not None
        picked.setdefault(emoji_key(text), text)
    return list(picked.values())


def _channels(guild: discord.Guild, channel_ids: list[str]) -> list[int]:
    found = [guild.get_channel(int(channel_id)) for channel_id in dict.fromkeys(channel_ids)]
    if any(not isinstance(channel, _SOURCES) for channel in found):
        raise SettingError("One of those channels isn't in this server.")
    return [channel.id for channel in found if channel]


def _check(emojis: list[str], downvote_emojis: list[str], threshold: int, drop_below: int | None) -> None:
    up = {emoji_key(value) for value in emojis}
    if not up:
        raise SettingError("A starboard needs at least one vote emoji.")
    if up & {emoji_key(value) for value in downvote_emojis}:
        raise SettingError("An emoji can't count as both a vote and a downvote.")
    if drop_below is not None and drop_below > threshold:
        raise SettingError("Posts can't leave the board above the votes it takes to get on it.")


@get("/", summary="This server's starboards")
async def list_starboards(guild: discord.Guild) -> list[Starboard]:
    return await _all(guild)


@post("/", summary="Make a channel a starboard", status_code=200, responses=REFUSED)
async def create_starboard(client: Client, guild: discord.Guild, data: StarboardCreate) -> Starboard:
    if len(starboard_db.boards(guild.id)) >= MAX_STARBOARDS:
        raise SettingError(f"A server can have up to {MAX_STARBOARDS} starboards.")
    values = {
        "channel_id": _board_channel(guild, data.channel_id),
        "emojis": _emojis(client, data.emojis),
        "threshold": data.threshold,
    }
    _check(values["emojis"], [], data.threshold, None)
    board = await starboard_db.create_board(guild.id, **values)
    return _out(board, 0)


@patch("/{board_id:int}", summary="Change a starboard", responses=REFUSED)
async def update_starboard(client: Client, guild: discord.Guild, board_id: BoardId, data: StarboardPatch) -> Starboard:
    board = _found(guild, board_id)
    sent = {field: value for field, value in structs.asdict(data).items() if value is not UNSET}
    changes: dict[str, Any] = {}
    for field, value in sent.items():
        match field:
            case "channel_id":
                changes[field] = _board_channel(guild, value, board.id)
            case "emojis" | "downvote_emojis":
                changes[field] = _emojis(client, value)
            case "channel_ids":
                changes[field] = _channels(guild, value)
            case "blocked_role_ids":
                changes[field] = [role.id for role in resolve.roles(guild, value)]
            case _:
                changes[field] = value
    after = {
        key: changes.get(key, getattr(board, key)) for key in ("emojis", "downvote_emojis", "threshold", "drop_below")
    }
    _check(**after)
    moved = "channel_id" in changes and changes["channel_id"] != board.channel_id
    if changes:
        await starboard_db.save_board(guild.id, board, **changes)
    if moved:
        # Old posts stay where they are, and messages voted on again post in the new channel
        await starboard_db.clear_post_ids([board.id])
    counts = await starboard_db.post_counts([board.id])
    return _out(board, counts.get(board.id, 0))


@delete("/{board_id:int}", summary="Stop a channel being a starboard", status_code=204, responses=REFUSED)
async def delete_starboard(guild: discord.Guild, board_id: BoardId) -> None:
    """Posts already on the board stay in the channel."""
    await starboard_db.delete_board(guild.id, _found(guild, board_id))


router = Router(
    "/guilds/{guild_id:str}/starboards",
    opt={"module": Module.STARBOARD},
    tags=["Starboard"],
    exception_handlers={SettingError: refused},
    dependencies={"guild": Provide(provide_guild, sync_to_thread=False)},
    route_handlers=[list_starboards, create_starboard, update_starboard, delete_starboard],
)
