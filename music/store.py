import asyncio
import discord
from core.view import DesignerView
from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class Types:
    PlayerChannel = (
        discord.TextChannel | discord.VoiceChannel | discord.StageChannel | discord.ForumChannel | discord.Thread
    )
    PlayerMessage = discord.Message


store: dict[
    int,
    dict[str, Any],
] = {}


# Play channel
def play_ch(
    guild_id: int,
    channel: Types.PlayerChannel | None = None,
    mode: Literal["get", "set"] = "get",
) -> Types.PlayerChannel | None:
    """
    Gets or sets the play channel for a guild.

    Args:
        guild_id (int): The ID of the guild.
        channel (:class:`Types.PlayerChannel` | None): The channel to set, or None to get the current value.
        mode (str): The operation mode, either "get" or "set".
    """
    match mode:
        case "get":
            guild = store.get(guild_id, {})
            if guild:
                return guild.get("play_ch", None)
            return None
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["play_ch"] = channel


# Play msg
def play_msg(
    guild_id: int,
    msg: Types.PlayerMessage | None = None,
    view: DesignerView | None = None,
    mode: Literal["get", "set", "clear"] = "get",
) -> tuple[Types.PlayerMessage, DesignerView] | None:
    """
    Gets or sets the play message for a guild.

    Args:
        guild_id (int): The ID of the guild.
        msg (:class:`Types.PlayerMessage` | None): The message to set, or None to get the current value.
        view (:class:`DesignerView` | None): The view to set, or None to get the current value.
        mode (str): The operation mode, either "get", "set", or "clear".
    """
    match mode:
        case "get":
            guild = store.get(guild_id, {})
            return (guild.get("play_msg", None), guild.get("play_msg_view", None))
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["play_msg"] = msg
            store[guild_id]["play_msg_view"] = view
        case "clear":
            if guild_id in store and "play_msg" in store[guild_id]:
                del store[guild_id]["play_msg"]
                del store[guild_id]["play_msg_view"]


def render_task(
    guild_id: int, task: asyncio.Task | None = None, mode: Literal["get", "set", "clear"] = "get"
) -> asyncio.Task | None:
    match mode:
        case "get":
            return store.get(guild_id, {}).get("render_task", None)
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["render_task"] = task
        case "clear":
            if guild_id in store and "render_task" in store[guild_id]:
                del store[guild_id]["render_task"]


# Synced lyrics cache for the currently playing track
def lyrics(
    guild_id: int,
    identifier: str | None = None,
    lines: list[tuple[int, str]] | None = None,
    mode: Literal["get", "set", "clear"] = "get",
) -> tuple[str, list[tuple[int, str]]] | None:
    """
    Gets, sets, or clears the cached lyrics for a guild.

    Args:
        guild_id (int): The ID of the guild.
        identifier (str | None): The track identifier the lyrics belong to.
        lines (list[tuple[int, str]] | None): Timestamped lyric lines.
        mode (str): The operation mode, either "get", "set", or "clear".

    Returns:
        tuple[str, list[tuple[int, str]]] | None: The cached (identifier, lines) pair, or None.
    """
    match mode:
        case "get":
            return store.get(guild_id, {}).get("lyrics", None)
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["lyrics"] = (identifier, lines or [])
        case "clear":
            if guild_id in store:
                store[guild_id].pop("lyrics", None)


# Lyrics updater task
def lyrics_task(
    guild_id: int, task: asyncio.Task | None = None, mode: Literal["get", "set", "clear"] = "get"
) -> asyncio.Task | None:
    match mode:
        case "get":
            return store.get(guild_id, {}).get("lyrics_task", None)
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["lyrics_task"] = task
        case "clear":
            if guild_id in store and "lyrics_task" in store[guild_id]:
                del store[guild_id]["lyrics_task"]


# Accumulated visual height (estimated chat lines) posted since the player message was last sent
def chat_weight(
    guild_id: int,
    value: int | None = None,
    mode: Literal["get", "add", "clear"] = "get",
) -> int:
    """
    Gets, adds to, or clears the accumulated chat weight for a guild.

    Args:
        guild_id (int): The ID of the guild.
        value (int | None): The number of estimated lines to add (for "add" mode).
        mode (str): The operation mode, either "get", "add", or "clear".

    Returns:
        int: The accumulated weight after the operation (0 for "clear").
    """
    match mode:
        case "get":
            return store.get(guild_id, {}).get("chat_weight", 0)
        case "add":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["chat_weight"] = store[guild_id].get("chat_weight", 0) + (value or 0)
            return store[guild_id]["chat_weight"]
        case "clear":
            if guild_id in store:
                store[guild_id].pop("chat_weight", None)
            return 0


_MUSIC_KEYS = {
    "chat_weight",
    "lyrics",
    "lyrics_task",
    "play_ch",
    "play_msg",
    "play_msg_view",
    "render_task",
}


def flush_store(guild_id: int) -> None:
    """
    Removes all music-related keys for a guild from the store.

    Drops the guild entry entirely once it is empty so destroyed players leave no per-guild residue.
    Tasks are only removed here, not cancelled - cancel them first via :func:`player.cleanup_guild`.
    """
    guild = store.get(guild_id)
    if guild is None:
        return
    for key in _MUSIC_KEYS:
        guild.pop(key, None)
    if not guild:
        store.pop(guild_id, None)
