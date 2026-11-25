import datetime
import discord
from collections import OrderedDict, deque
from dataclasses import dataclass
from square.db import cache
from square.logs.catalog import Log
from square.logs.sender import ignored

MAX_PER_CHANNEL = 200
SNIPES_PER_CHANNEL = 20


@dataclass(frozen=True, slots=True)
class SavedFile:
    name: str
    url: str
    proxy_url: str
    size: int
    spoiler: bool
    media: bool


@dataclass(frozen=True, slots=True)
class SavedSticker:
    name: str
    url: str | None  # None for Lottie stickers, which Discord can't show as a picture


@dataclass(slots=True)
class Saved:
    id: int
    channel_id: int
    author_id: int
    author_name: str
    author_avatar: str
    bot: bool
    content: str
    files: tuple[SavedFile, ...]
    sticker: SavedSticker | None
    forwarded: str | None  # The original message's link

    @property
    def sent_at(self) -> datetime.datetime:
        return discord.utils.snowflake_time(self.id)


@dataclass(slots=True)
class Snipe:
    message: Saved
    at: datetime.datetime
    deleted_by: str | None = None


# Only what the Messages log and /snipe show, in RAM only: nothing here is ever written to the database
_messages: dict[int, dict[int, OrderedDict[int, Saved]]] = {}
_snipes: dict[int, dict[int, deque[Snipe]]] = {}
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
    # A forward keeps its text, files and sticker in a snapshot, the message itself is empty
    snapshot = message.snapshots[0].message if message.snapshots and message.snapshots[0].message else None
    shown = snapshot or message
    forwarded = None
    if snapshot and (reference := message.reference) and reference.channel_id and reference.message_id:
        place = reference.guild_id or "@me"
        forwarded = f"https://discord.com/channels/{place}/{reference.channel_id}/{reference.message_id}"
    sticker = shown.stickers[0] if shown.stickers else None
    channel[message.id] = Saved(
        id=message.id,
        channel_id=message.channel.id,
        author_id=message.author.id,
        author_name=message.author.name,
        author_avatar=message.author.display_avatar.url,
        bot=message.author.bot,
        content=shown.content,
        files=tuple(
            SavedFile(
                item.filename,
                item.url,
                item.proxy_url,
                item.size,
                item.is_spoiler(),
                (item.content_type or "").startswith(("image/", "video/")),
            )
            for item in shown.attachments
        ),
        sticker=SavedSticker(sticker.name, None if sticker.format is discord.StickerFormatType.lottie else sticker.url)
        if sticker
        else None,
        forwarded=forwarded,
    )
    if len(channel) > MAX_PER_CHANNEL:
        _evicted[message.channel.id] = channel.popitem(last=False)[0]


def unknown(guild: discord.Guild, channel_id: int, message_id: int) -> bool:
    """Whether a message Square doesn't remember is one it never could have: sent before it started, or pushed out."""
    if not active(guild.id) or ignored(guild, channel_id):
        return False
    return message_id < _started or message_id <= _evicted.get(channel_id, 0)


def _push(guild_id: int, channel_id: int, snipe: Snipe) -> None:
    rings = _snipes.setdefault(guild_id, {})
    rings.setdefault(channel_id, deque(maxlen=SNIPES_PER_CHANNEL)).appendleft(snipe)


def edited(guild_id: int, channel_id: int, message_id: int, content: str) -> Saved | None:
    """The message as it was before the edit, or None when it isn't remembered or the text didn't change."""
    saved = _messages.get(guild_id, {}).get(channel_id, {}).get(message_id)
    if saved is None or saved.content == content:
        return None
    before = Saved(*(getattr(saved, name) for name in Saved.__slots__))
    saved.content = content
    return before


def deleted(guild_id: int, channel_id: int, message_id: int) -> Snipe | None:
    saved = _messages.get(guild_id, {}).get(channel_id, {}).pop(message_id, None)
    if saved is None:
        return None
    snipe = Snipe(saved, discord.utils.utcnow())
    _push(guild_id, channel_id, snipe)
    return snipe


def deleted_many(guild_id: int, channel_id: int, message_ids: set[int]) -> list[Saved]:
    """Bulk deletes are moderation, so they never show up in /snipe."""
    channel = _messages.get(guild_id, {}).get(channel_id, {})
    found = [saved for message_id in message_ids if (saved := channel.pop(message_id, None))]
    return sorted(found, key=lambda saved: saved.id)


def snipes(guild_id: int, channel_id: int) -> list[Snipe]:
    return list(_snipes.get(guild_id, {}).get(channel_id, ()))


def forget(guild_id: int) -> None:
    for channel_id in _messages.pop(guild_id, {}):
        _evicted.pop(channel_id, None)
    _snipes.pop(guild_id, None)


def prune(guild: discord.Guild) -> None:
    """Drops what the server's log settings no longer allow keeping, after they change."""
    if not active(guild.id):
        forget(guild.id)
        return
    for channels in (_messages.get(guild.id, {}), _snipes.get(guild.id, {})):
        for channel_id in [channel_id for channel_id in channels if ignored(guild, channel_id)]:
            del channels[channel_id]
