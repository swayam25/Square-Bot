import asyncio
import discord
import lavalink
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

    Parameters:
        guild_id (int): The ID of the guild.
        channel (Types.PlayerChannel | None): The channel to set, or None to get the current value.
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

    Parameters:
        guild_id (int): The ID of the guild.
        msg (Types.PlayerMessage | None): The message to set, or None to get the current value.
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


# Inactivity Task
def inactivity_task(
    guild_id: int, task: asyncio.Task | None = None, mode: Literal["get", "set", "clear"] = "get"
) -> asyncio.Task | None:
    """
    Gets or sets the inactivity task for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        task (asyncio.Task | None): The task to set, or None to get the current value.
        mode (str): The operation mode, either "get", "set", or "clear".
    """
    match mode:
        case "get":
            guild = store.get(guild_id, {})
            if guild:
                return guild.get("inactivity_task", None)
            return None
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["inactivity_task"] = task
        case "clear":
            if guild_id in store and "inactivity_task" in store[guild_id]:
                del store[guild_id]["inactivity_task"]


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


# Autoplay toggle
def autoplay(
    guild_id: int,
    value: bool | None = None,
    mode: Literal["get", "set", "clear"] = "get",
) -> bool:
    """
    Gets or sets the autoplay flag for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        value (bool | None): The value to set, or None to get the current value.
        mode (str): The operation mode, either "get" or "set".
    """
    match mode:
        case "get":
            return store.get(guild_id, {}).get("autoplay", False)
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["autoplay"] = bool(value)
            return bool(value)
        case "clear":
            if guild_id in store:
                store[guild_id].pop("autoplay", None)


# Last played track (used by autoplay to seed related-track search)
def last_track(
    guild_id: int,
    track: lavalink.AudioTrack | None = None,
    mode: Literal["get", "set", "clear"] = "get",
) -> lavalink.AudioTrack | None:
    """
    Gets, sets, or clears the last played track for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        track: The track to store, or None to retrieve/clear.
        mode (str): The operation mode, either "get", "set", or "clear".
    """
    match mode:
        case "get":
            return store.get(guild_id, {}).get("last_track", None)
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["last_track"] = track
        case "clear":
            if guild_id in store:
                store[guild_id].pop("last_track", None)


# Autoplay history (recently played identifiers, used to filter recommendations)
def autoplay_history(
    guild_id: int,
    identifier: str | None = None,
    mode: Literal["get", "add", "clear"] = "get",
    max_size: int = 30,
) -> list[str]:
    match mode:
        case "get":
            return store.get(guild_id, {}).get("autoplay_history", [])
        case "add":
            if guild_id not in store:
                store[guild_id] = {}
            history: list[str] = store[guild_id].get("autoplay_history", [])
            if identifier and identifier not in history:
                history.append(identifier)
                if len(history) > max_size:
                    history = history[-max_size:]
            store[guild_id]["autoplay_history"] = history
        case "clear":
            if guild_id in store:
                store[guild_id].pop("autoplay_history", None)


_MUSIC_KEYS = {"autoplay", "autoplay_history", "last_track", "play_ch", "play_msg", "play_msg_view"}


def flush_store(guild_id: int) -> None:
    """Removes all music-related keys for a guild from the store."""
    if guild_id in store:
        for key in _MUSIC_KEYS:
            store[guild_id].pop(key, None)
