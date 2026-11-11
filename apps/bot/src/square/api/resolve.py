"""Turns IDs from a request into live Discord objects, refusing anything the Discord pickers wouldn't offer."""

import discord
import re
from square.settings.errors import SettingError
from typing import Any

_MENTION = re.compile(r"<(#|@&|@!?)(\d+)>")
_CUSTOM_EMOJI = re.compile(r"<a?:\w+:\d+>\s*")


def plain(guild: discord.Guild, text: str) -> str:
    """
    Makes a bot message readable outside Discord.

    Mentions become names and custom emoji go, since the dashboard can render neither. Markdown stays.
    """

    def name(match: re.Match[str]) -> str:
        kind, item_id = match[1], int(match[2])
        if kind == "#":
            item = guild.get_channel(item_id)
            return f"#{item.name}" if item else match[0]
        if kind == "@&":
            role = guild.get_role(item_id)
            return f"@{role.name}" if role else match[0]
        member = guild.get_member(item_id)
        return f"@{member.display_name}" if member else "@unknown"

    return _MENTION.sub(name, _CUSTOM_EMOJI.sub("", text)).strip()


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
    """Roles in the order given, without repeats. Refuses @everyone, which Discord's role picker never offers."""
    picked = [found for role_id in dict.fromkeys(role_ids) if (found := role(guild, role_id))]
    if any(found.is_default() for found in picked):
        raise SettingError("@everyone can't be picked here.")
    return picked
