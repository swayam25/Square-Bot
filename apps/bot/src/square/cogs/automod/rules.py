import discord
import emoji as emojis
import re
import time
from collections import deque
from square.core import Client
from square.db.schema import AutomodRuleTable
from square.utils.helpers import plural
from typing import Literal, get_args

Kind = Literal["media", "invites", "flood", "duplicates", "caps", "emojis"]
KINDS: tuple[Kind, ...] = get_args(Kind)

LABELS: dict[Kind, str] = {
    "media": "Media-only channels",
    "invites": "Invite links",
    "flood": "Message flood",
    "duplicates": "Repeated messages",
    "caps": "Capital letters",
    "emojis": "Emoji spam",
}

NOTICES: dict[Kind, str] = {
    "media": "This channel is for **media** only. Send a file or a link.",
    "invites": "Invite links to other servers aren't allowed here.",
    "flood": "Slow down, you're sending messages too fast.",
    "duplicates": "Please don't send the same message again and again.",
    "caps": "Please don't use so many capital letters.",
    "emojis": "Please don't send so many emojis.",
}

# (amount, seconds) a new rule starts with
DEFAULTS: dict[Kind, tuple[int | None, int | None]] = {
    "media": (None, None),
    "invites": (None, None),
    "flood": (5, 5),
    "duplicates": (3, 60),
    "caps": (70, None),
    "emojis": (10, None),
}

# Short messages like "OK" or "LOL" would always trip the capitals rule
MIN_CAPS_LETTERS = 10
MAX_WINDOW = 600
INVITE_CACHE_SECONDS = 3600

_LINK = re.compile(r"https?://\S+", re.IGNORECASE)
_INVITE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord(?:app)?\.com/invite|discord\.gg)/([\w-]{2,32})", re.IGNORECASE
)
_CUSTOM_EMOJI = re.compile(r"<a?:\w{2,32}:\d{17,20}>")
_MENTION = re.compile(r"<(?:@[!&]?|#)\d{17,20}>")
_USER_OR_ROLE = re.compile(r"<@[!&]?(\d{17,20})>")


def has_media(message: discord.Message) -> bool:
    return bool(message.attachments or message.stickers or _LINK.search(message.content))


def has_link(content: str) -> bool:
    return bool(_LINK.search(content))


def invite_codes(content: str) -> list[str]:
    return list(dict.fromkeys(_INVITE.findall(content)))


def caps_percent(content: str) -> int | None:
    text = _LINK.sub("", _MENTION.sub("", _CUSTOM_EMOJI.sub("", content)))
    letters = [char for char in text if char.isupper() or char.islower()]
    if len(letters) < MIN_CAPS_LETTERS:
        return None
    return round(100 * sum(char.isupper() for char in letters) / len(letters))


def emoji_count(content: str) -> int:
    return len(_CUSTOM_EMOJI.findall(content)) + emojis.emoji_count(content)


def mention_count(content: str) -> int:
    return len(set(_USER_OR_ROLE.findall(content)))


def same_text(content: str) -> str:
    return " ".join(content.casefold().split())


_invite_guilds: dict[str, tuple[float, int | None]] = {}


async def invite_guild(client: Client, code: str) -> int | None:
    now = time.monotonic()
    if (found := _invite_guilds.get(code)) and now - found[0] < INVITE_CACHE_SECONDS:
        return found[1]
    try:
        invite = await client.fetch_invite(code, with_counts=False)
        guild_id = invite.guild.id if invite.guild else None
    except discord.HTTPException:
        guild_id = None
    if len(_invite_guilds) > 1000:
        _invite_guilds.clear()
    _invite_guilds[code] = (now, guild_id)
    return guild_id


async def foreign_invite(client: Client, guild: discord.Guild, content: str) -> str | None:
    """The first invite that isn't to `guild`. Dead invites count too, since the bot can't tell where they led."""
    for code in invite_codes(content):
        if await invite_guild(client, code) != guild.id:
            return code
    return None


class Recent:
    """Each member's messages from the last few minutes, for the flood and duplicate rules."""

    def __init__(self):
        self._sent: dict[tuple[int, int], deque[tuple[float, str]]] = {}
        self._warned: dict[tuple[int, int, str], float] = {}
        self._adds = 0

    def add(self, guild_id: int, user_id: int, content: str) -> deque[tuple[float, str]]:
        now = time.monotonic()
        sent = self._sent.setdefault((guild_id, user_id), deque())
        sent.append((now, same_text(content)))
        while sent and now - sent[0][0] > MAX_WINDOW:
            sent.popleft()
        self._adds += 1
        if self._adds % 1000 == 0:
            self._sweep(now)
        return sent

    def flood(self, sent: deque[tuple[float, str]], amount: int, seconds: int) -> bool:
        now = time.monotonic()
        return sum(now - at <= seconds for at, _ in sent) > amount

    def duplicates(self, sent: deque[tuple[float, str]], amount: int, seconds: int) -> bool:
        now, text = time.monotonic(), sent[-1][1]
        return bool(text) and sum(now - at <= seconds and seen == text for at, seen in sent) > amount

    def once(self, guild_id: int, user_id: int, kind: str, seconds: int) -> bool:
        """True for the first hit of a burst, so a flood of 20 messages doesn't hand out 15 warnings."""
        now = time.monotonic()
        key = (guild_id, user_id, kind)
        if now - self._warned.get(key, -seconds - 1) <= seconds:
            return False
        self._warned[key] = now
        return True

    def forget(self, guild_id: int) -> None:
        self._sent = {key: value for key, value in self._sent.items() if key[0] != guild_id}
        self._warned = {key: value for key, value in self._warned.items() if key[0] != guild_id}

    def _sweep(self, now: float) -> None:
        self._sent = {key: sent for key, sent in self._sent.items() if sent and now - sent[-1][0] <= MAX_WINDOW}
        self._warned = {key: at for key, at in self._warned.items() if now - at <= MAX_WINDOW}


def exempt(rule: AutomodRuleTable, member: discord.Member, channel: discord.abc.GuildChannel | discord.Thread) -> bool:
    if rule.exempt_role_ids and any(role.id in rule.exempt_role_ids for role in member.roles):
        return True
    places = {channel.id, getattr(channel, "category_id", None)}
    if isinstance(channel, discord.Thread) and channel.parent:
        places |= {channel.parent.id, channel.parent.category_id}
    return any(place in rule.exempt_channel_ids for place in places if place)


async def content_hit(client: Client, guild: discord.Guild, rule: AutomodRuleTable, content: str) -> str | None:
    match rule.kind:
        case "invites":
            if code := await foreign_invite(client, guild, content):
                return f"Invite {code}"
        case "caps":
            if (percent := caps_percent(content)) is not None and percent > (rule.amount or 100):
                return f"{percent}% capitals"
        case "emojis":
            if (count := emoji_count(content)) > (rule.amount or 0):
                return f"{count} {plural(count, 'emoji')}"
    return None


def _keyword(word: str) -> re.Pattern[str] | None:
    core = word.strip("*")
    if not core:
        return None
    before = "" if word.startswith("*") else r"(?<!\w)"
    after = "" if word.endswith("*") else r"(?!\w)"
    return re.compile(before + re.escape(core) + after, re.IGNORECASE)


def _word_around(content: str, start: int, end: int) -> str:
    while start > 0 and content[start - 1].isalnum():
        start -= 1
    while end < len(content) and content[end].isalnum():
        end += 1
    return content[start:end]


def keyword_hit(content: str, keywords: list[str], patterns: list[str], allow: list[str]) -> str | None:
    """The bot's best guess at what a Discord keyword rule catches. Discord runs Rust regexes, so edge cases differ."""
    allowed = [found for word in allow if (found := _keyword(word))]

    def first(pattern: re.Pattern[str]) -> str | None:
        for match in pattern.finditer(content):
            word = _word_around(content, match.start(), match.end())
            if not any(ok.search(word) for ok in allowed):
                return match.group(0)
        return None

    for word in keywords:
        if (pattern := _keyword(word)) and (found := first(pattern)):
            return found
    for source in patterns:
        try:
            pattern = re.compile(source, re.IGNORECASE)
        except re.error:
            continue
        if found := first(pattern):
            return found
    return None
