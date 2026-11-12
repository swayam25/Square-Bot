import discord
import re
from typing import Any


class SettingError(Exception):
    """A change the bot refuses, like a role above its own. The message is meant for the person who asked."""


_MENTION = re.compile(r"<(#|@&|@!?)(\d+)>")
_CUSTOM_EMOJI = re.compile(r"<a?:\w+:\d+>\s*")
# Lazy label, so titles with their own brackets ("Song [Remix]") still match up to the link
_LINK = re.compile(r"\[(.+?)\]\(<?https?://[^\s)>]+>?\)")
_MARKERS = re.compile(r"\*\*|__|~~|`")
_ESCAPED = re.compile(r"\\([*_`~|>\[\]()#-])")
_LINE_PREFIX = re.compile(r"^(?:-#|#{1,3}|>)\s+")
_TRAILING_TAG = re.compile(r"\s\[([^\[\]]+)\]\.$")


def plain(guild: discord.Guild, text: str) -> str:
    return " ".join(part for part in split(guild, text) if part)


def split(guild: discord.Guild, text: str) -> tuple[str, str | None]:

    def name(match: re.Match[str]) -> str:
        kind, item_id = match[1], int(match[2])
        if kind == "#":
            item = guild.get_channel(item_id)
            return f"#{item.name}" if item else "#unknown"
        if kind == "@&":
            role = guild.get_role(item_id)
            return f"@{role.name}" if role else "@unknown"
        member = guild.get_member(item_id)
        return f"@{member.display_name}" if member else "@unknown"

    def clean(line: str) -> str:
        line = _LINK.sub(r"\1", _CUSTOM_EMOJI.sub("", line))
        line = _ESCAPED.sub(r"\1", _MARKERS.sub("", line))
        line = _TRAILING_TAG.sub(r" (\1).", _LINE_PREFIX.sub("", line.strip()))
        return " ".join(_MENTION.sub(name, line).split())

    main: list[str] = []
    notes: list[str] = []
    for line in text.splitlines():
        (notes if line.lstrip().startswith("-# ") else main).append(clean(line))
    note = " ".join(n for n in notes if n)
    return " ".join(m for m in main if m), note or None


def _channel(guild: discord.Guild, channel_id: str | None, kind: Any, what: str) -> Any:
    if channel_id is None:
        return None
    channel = guild.get_channel(int(channel_id))
    if not isinstance(channel, kind):
        raise SettingError(f"That isn't a {what} in this server.")
    return channel


def text_channel(guild: discord.Guild, channel_id: str | None) -> discord.TextChannel | None:
    return _channel(guild, channel_id, discord.TextChannel, "text channel")


def voice_channel(guild: discord.Guild, channel_id: str | None) -> discord.VoiceChannel | discord.StageChannel | None:
    return _channel(guild, channel_id, discord.VoiceChannel | discord.StageChannel, "voice channel")


def category(guild: discord.Guild, channel_id: str | None) -> discord.CategoryChannel | None:
    return _channel(guild, channel_id, discord.CategoryChannel, "category")


def role(guild: discord.Guild, role_id: str | None) -> discord.Role | None:
    if role_id is None:
        return None
    if (found := guild.get_role(int(role_id))) is None:
        raise SettingError("That role isn't in this server.")
    return found


def roles(guild: discord.Guild, role_ids: list[str]) -> list[discord.Role]:
    picked = [found for role_id in dict.fromkeys(role_ids) if (found := role(guild, role_id))]
    if any(found.is_default() for found in picked):
        raise SettingError("@everyone can't be picked here.")
    return picked
