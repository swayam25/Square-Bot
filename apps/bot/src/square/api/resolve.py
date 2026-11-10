"""Turns IDs from a request into live Discord objects, refusing anything the Discord pickers wouldn't offer."""

import discord
import re
from square.settings.errors import SettingError
from typing import Any

_MENTION = re.compile(r"<(#|@&)(\d+)>")


def plain(guild: discord.Guild, text: str) -> str:
    """Swaps channel and role mentions in a message for names, since the dashboard can't render mentions."""

    def name(match: re.Match[str]) -> str:
        kind, item_id = match[1], int(match[2])
        item = guild.get_channel(item_id) if kind == "#" else guild.get_role(item_id)
        return f"{'#' if kind == '#' else '@'}{item.name}" if item else match[0]

    return _MENTION.sub(name, text)


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
