import datetime
import discord
from collections import OrderedDict, deque
from dataclasses import dataclass
from square.db import cache
from square.logs.catalog import Log
from square.logs.sender import ignored
from typing import Literal

MAX_PER_CHANNEL = 200
SNIPES_PER_CHANNEL = 20

type SnipeKind = Literal["deleted", "edited"]


@dataclass(slots=True)
class Saved:
    id: int
    channel_id: int
    author_id: int
    author_name: str
    author_avatar: str
    bot: bool
    content: str
    files: tuple[str, ...]
    stickers: tuple[str, ...]

    @property
    def sent_at(self) -> datetime.datetime:
        return discord.utils.snowflake_time(self.id)


@dataclass(slots=True)
class Snipe:
    message: Saved
    at: datetime.datetime
    after: str | None = None
    deleted_by: str | None = None


# Only what the Messages log and /snipe show, in RAM only: nothing here is ever written to the database
_messages: dict[int, dict[int, OrderedDict[int, Saved]]] = {}
_snipes: dict[tuple[int, SnipeKind], dict[int, deque[Snipe]]] = {}
_evicted: dict[int, int] = {}
_started = discord.utils.time_snowflake(discord.utils.utcnow())


def active(guild_id: int) -> bool:
    return cache.log_channel(guild_id, Log.MESSAGES) is not None


def remember(message: discord.Message) -> None:
    guild = message.guild
    if guild is None or not active(guild.id):
        return
    # Bots and ignored roles are kept and filtered when shown, so a missing message means one Square never saw
    if ignored(guild, message.channel.id):
        return
    channel = _messages.setdefault(guild.id, {}).setdefault(message.channel.id, OrderedDict())
    channel[message.id] = Saved(
        id=message.id,
        channel_id=message.channel.id,
        author_id=message.author.id,
        author_name=message.author.name,
        author_avatar=message.author.display_avatar.url,
        bot=message.author.bot,
        content=message.content,
        files=tuple(attachment.filename for attachment in message.attachments),
        stickers=tuple(sticker.name for sticker in message.stickers),
    )
    if len(channel) > MAX_PER_CHANNEL:
        _evicted[message.channel.id] = channel.popitem(last=False)[0]


def unknown(guild: discord.Guild, channel_id: int, message_id: int) -> bool:
    """Whether a message Square doesn't remember is one it never could have: sent before it started, or pushed out."""
    if not active(guild.id) or ignored(guild, channel_id):
        return False
    return message_id < _started or message_id <= _evicted.get(channel_id, 0)


def _push(guild_id: int, kind: SnipeKind, channel_id: int, snipe: Snipe) -> None:
    rings = _snipes.setdefault((guild_id, kind), {})
    rings.setdefault(channel_id, deque(maxlen=SNIPES_PER_CHANNEL)).appendleft(snipe)


def edited(guild_id: int, channel_id: int, message_id: int, content: str) -> Saved | None:
    """The message as it was before the edit, or None when it isn't remembered or the text didn't change."""
    saved = _messages.get(guild_id, {}).get(channel_id, {}).get(message_id)
    if saved is None or saved.content == content:
        return None
    before = Saved(*(getattr(saved, name) for name in Saved.__slots__))
    saved.content = content
    _push(guild_id, "edited", channel_id, Snipe(before, discord.utils.utcnow(), after=content))
    return before


def deleted(guild_id: int, channel_id: int, message_id: int) -> Snipe | None:
    saved = _messages.get(guild_id, {}).get(channel_id, {}).pop(message_id, None)
    if saved is None:
        return None
    snipe = Snipe(saved, discord.utils.utcnow())
    _push(guild_id, "deleted", channel_id, snipe)
    return snipe


def deleted_many(guild_id: int, channel_id: int, message_ids: set[int]) -> list[Saved]:
    """Bulk deletes are moderation, so they never show up in /snipe."""
    channel = _messages.get(guild_id, {}).get(channel_id, {})
    found = [saved for message_id in message_ids if (saved := channel.pop(message_id, None))]
    return sorted(found, key=lambda saved: saved.id)


def snipes(guild_id: int, channel_id: int, kind: SnipeKind) -> list[Snipe]:
    return list(_snipes.get((guild_id, kind), {}).get(channel_id, ()))


def forget_snipe(guild_id: int, channel_id: int, kind: SnipeKind, snipe: Snipe) -> None:
    ring = _snipes.get((guild_id, kind), {}).get(channel_id)
    if ring and snipe in ring:
        ring.remove(snipe)


def forget(guild_id: int) -> None:
    for channel_id in _messages.pop(guild_id, {}):
        _evicted.pop(channel_id, None)
    for kind in ("deleted", "edited"):
        _snipes.pop((guild_id, kind), None)


def prune(guild: discord.Guild) -> None:
    """Drops what the server's log settings no longer allow keeping, after they change."""
    if not active(guild.id):
        forget(guild.id)
        return
    for channels in (
        _messages.get(guild.id, {}),
        *(_snipes.get((guild.id, kind), {}) for kind in ("deleted", "edited")),
    ):
        for channel_id in [channel_id for channel_id in channels if ignored(guild, channel_id)]:
            del channels[channel_id]
