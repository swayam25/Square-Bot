import discord
import emoji as emojis
import re
import time
import unicodedata
from collections import deque
from square.core import Client
from square.db.schema import AutomodRuleTable
from square.utils.helpers import fmt_count, plural
from typing import Literal, NamedTuple, get_args
from urllib.parse import urlsplit

Kind = Literal[
    "media",
    "invites",
    "masked_links",
    "new_members",
    "flood",
    "duplicates",
    "mention_flood",
    "file_flood",
    "ghost_pings",
    "caps",
    "emojis",
    "zalgo",
    "fonts",
    "repeated_chars",
    "lines",
    "invisible",
]
KINDS: tuple[Kind, ...] = get_args(Kind)
WINDOW_KINDS: tuple[Kind, ...] = ("flood", "duplicates", "mention_flood", "file_flood")

LABELS: dict[Kind, str] = {
    "media": "Media-only channels",
    "invites": "Invite links",
    "masked_links": "Masked links",
    "new_members": "Links from new members",
    "flood": "Message flood",
    "duplicates": "Repeated messages",
    "mention_flood": "Mention flood",
    "file_flood": "File spam",
    "ghost_pings": "Ghost pings",
    "caps": "Capital letters",
    "emojis": "Emoji spam",
    "zalgo": "Zalgo text",
    "fonts": "Fancy fonts",
    "repeated_chars": "Repeated characters",
    "lines": "Walls of text",
    "invisible": "Invisible characters",
}

NOTICES: dict[Kind, str] = {
    "media": "This channel is for **media** only. Send a file or a link.",
    "invites": "Invite links to other servers aren't allowed here.",
    "masked_links": "Links that show one site and open another aren't allowed here.",
    "new_members": "You can't send links or files until you've been here a little longer.",
    "flood": "Slow down, you're sending messages too fast.",
    "duplicates": "Please don't send the same message again and again.",
    "mention_flood": "Please don't ping so many people.",
    "file_flood": "Slow down, you're sending too many files.",
    "ghost_pings": "pinged {pinged} and deleted the message.",
    "caps": "Please don't use so many capital letters.",
    "emojis": "Please don't send so many emojis.",
    "zalgo": "Please don't send zalgo text.",
    "fonts": "Please use normal letters instead of fancy fonts.",
    "repeated_chars": "Please don't repeat the same character so many times.",
    "lines": "Please don't send so many lines at once.",
    "invisible": "Please don't hide invisible characters in your messages.",
}

# (amount, seconds) a new rule starts with
DEFAULTS: dict[Kind, tuple[int | None, int | None]] = {
    "media": (None, None),
    "invites": (None, None),
    "masked_links": (None, None),
    "new_members": (30, None),
    "flood": (5, 5),
    "duplicates": (3, 60),
    "mention_flood": (10, 30),
    "file_flood": (5, 10),
    "ghost_pings": (None, 60),
    "caps": (70, None),
    "emojis": (10, None),
    "zalgo": (3, None),
    "fonts": (50, None),
    "repeated_chars": (9, None),
    "lines": (15, None),
    "invisible": (None, None),
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
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
_MASKED = re.compile(r"\[([^\]\n]+)\]\(\s*<?(https?://[^\s)>]+)>?(?:\s+\"[^\"]*\")?\s*\)", re.IGNORECASE)
# Only link text that is itself a web address counts, so [notes](url) or [click here](url) are fine
_SHOWN_HOST = re.compile(r"^\s*(?:https?://)?(?:www\.)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?:[/:?#]\S*)?\s*$", re.IGNORECASE)
# Persian, Urdu and Indic writing needs the zero-width non-joiner, and right-to-left writers type direction marks
_ALLOWED_FORMAT = frozenset("\u200c\u200e\u200f")
_BLANK = frozenset("\u034f\u115f\u1160\u17b4\u17b5\u2800\u3164\uffa0")


def has_media(message: discord.Message) -> bool:
    return bool(message.attachments or message.stickers or _LINK.search(message.content))


def has_link(content: str) -> bool:
    return bool(_LINK.search(content))


def invite_codes(content: str) -> list[str]:
    return list(dict.fromkeys(_INVITE.findall(content)))


def _plain(content: str) -> str:
    return _LINK.sub("", _MENTION.sub("", _CUSTOM_EMOJI.sub("", content)))


def caps_percent(content: str) -> int | None:
    letters = [char for char in _plain(content) if char.isupper() or char.islower()]
    if len(letters) < MIN_CAPS_LETTERS:
        return None
    return round(100 * sum(char.isupper() for char in letters) / len(letters))


def emoji_count(content: str) -> int:
    return len(_CUSTOM_EMOJI.findall(content)) + emojis.emoji_count(content)


def mention_count(content: str) -> int:
    return len(set(_USER_OR_ROLE.findall(content)))


def same_text(content: str) -> str:
    return " ".join(content.casefold().split())


def most_marks(content: str) -> int:
    """The most accent marks stacked on one character."""
    most = run = 0
    for char in content:
        run = run + 1 if unicodedata.category(char) in ("Mn", "Me") else 0
        most = max(most, run)
    return most


def _fancy(char: str) -> bool:
    if char.isascii():
        return False
    plain = unicodedata.normalize("NFKC", char)
    if len(plain) == 1 and plain.isascii() and plain.isalpha():
        return True
    return unicodedata.name(char, "").startswith("LATIN LETTER SMALL CAPITAL")


def fancy_letters(content: str) -> tuple[int, int]:
    """(fancy letters, all letters). Fancy means math, fullwidth, circled, squared, superscript or small caps."""
    letters = [char for char in emojis.replace_emoji(_plain(content), "") if char.isalpha() or _fancy(char)]
    return sum(_fancy(char) for char in letters), len(letters)


def invisible_char(content: str) -> str | None:
    """Emoji sequences hide joiners on purpose, so they're taken out first."""
    for char in emojis.replace_emoji(content, ""):
        if char in _BLANK or (unicodedata.category(char) == "Cf" and char not in _ALLOWED_FORMAT):
            return char
    return None


def longest_run(content: str) -> tuple[int, str]:
    """The longest run of one character, leaving out code, links, mentions, emojis and spaces."""
    text = emojis.replace_emoji(_plain(_CODE.sub("", content)), "").casefold()
    most, most_char, run, last = 0, "", 0, ""
    for char in text:
        if char.isspace():
            run, last = 0, ""
            continue
        run = run + 1 if char == last else 1
        last = char
        if run > most:
            most, most_char = run, char
    return most, most_char


def line_count(content: str) -> int:
    return len(content.splitlines())


def masked_link(content: str) -> tuple[str, str] | None:
    """(shown site, real site) of the first link whose text names a different site than it opens."""
    for text, url in _MASKED.findall(content):
        if not (shown := _SHOWN_HOST.match(text)):
            continue
        shown_host = shown.group(1).casefold()
        real_host = (urlsplit(url).hostname or "").removeprefix("www.")
        if real_host != shown_host and not real_host.endswith(f".{shown_host}"):
            return shown_host, real_host
    return None


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


class Sent(NamedTuple):
    at: float
    text: str
    mentions: int
    files: int
    kinds: frozenset[str]  # The window rules that applied where it was sent. Others don't count it


class Recent:
    """Each member's messages from the last few minutes, for the rules that count over time."""

    def __init__(self):
        self._sent: dict[tuple[int, int], deque[Sent]] = {}
        self._warned: dict[tuple[int, int, str], float] = {}
        self._adds = 0

    def add(self, guild_id: int, user_id: int, entry: Sent) -> deque[Sent]:
        sent = self._sent.setdefault((guild_id, user_id), deque())
        sent.append(entry)
        while sent and entry.at - sent[0].at > MAX_WINDOW:
            sent.popleft()
        self._adds += 1
        if self._adds % 1000 == 0:
            self._sweep(entry.at)
        return sent

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
        self._sent = {key: sent for key, sent in self._sent.items() if sent and now - sent[-1].at <= MAX_WINDOW}
        self._warned = {key: at for key, at in self._warned.items() if now - at <= MAX_WINDOW}


def window_hit(rule: AutomodRuleTable, sent: deque[Sent]) -> str | None:
    """Only the newest message can trip a rule, so a calm message after a burst isn't caught."""
    default_amount, default_seconds = DEFAULTS[rule.kind]
    amount, seconds = rule.amount or default_amount or 0, rule.seconds or default_seconds or 0
    last = sent[-1]
    counted = [entry for entry in sent if rule.kind in entry.kinds and last.at - entry.at <= seconds]
    match rule.kind:
        case "flood":
            if len(counted) > amount:
                return f"Over {fmt_count(amount)} {plural(amount, 'message')} in {seconds}s"
        case "duplicates":
            if last.text and sum(entry.text == last.text for entry in counted) > amount:
                return f"Same message over {fmt_count(amount)} {plural(amount, 'time')} in {seconds}s"
        case "mention_flood":
            if last.mentions and (total := sum(entry.mentions for entry in counted)) > amount:
                return f"{fmt_count(total)} {plural(total, 'mention')} in {seconds}s"
        case "file_flood":
            if last.files and (total := sum(entry.files for entry in counted)) > amount:
                return f"{fmt_count(total)} {plural(total, 'file')} in {seconds}s"
    return None


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
                return f"{fmt_count(count)} {plural(count, 'emoji')}"
        case "masked_links":
            if found := masked_link(content):
                return f"Shows {found[0]}, opens {found[1]}"
        case "zalgo":
            if (marks := most_marks(content)) > (rule.amount or 0):
                return f"{marks} marks on one letter"
        case "fonts":
            fancy, letters = fancy_letters(content)
            if fancy and fancy * 100 > (rule.amount or 0) * letters:
                return f"{round(100 * fancy / letters)}% fancy letters"
        case "repeated_chars":
            run, char = longest_run(content)
            if run > (rule.amount or 0):
                return f'"{char}" {run} times in a row'
        case "lines":
            if (lines := line_count(content)) > (rule.amount or 0):
                return f"{lines} lines"
        case "invisible":
            if char := invisible_char(content):
                return f"Invisible character U+{ord(char):04X}"
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
