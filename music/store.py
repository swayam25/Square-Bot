import asyncio
import discord
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
    mode: Literal["get", "set", "clear"] = "get",
) -> Types.PlayerMessage | None:
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
            if guild:
                return guild.get("play_msg", None)
            return None
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["play_msg"] = msg
        case "clear":
            if guild_id in store and "play_msg" in store[guild_id]:
                del store[guild_id]["play_msg"]


# Queue msg
def queue_msg(
    guild_id: int, msg: Types.PlayerMessage | None = None, mode: Literal["get", "set", "clear"] = "get"
) -> list[Types.PlayerMessage]:
    """
    Gets or sets the queue message for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        msg (Types.PlayerMessage | None): The message to set, or None to get the current value.
        mode (str): The operation mode, either "get", "set", or "clear".
    """
    match mode:
        case "get":
            guild = store.get(guild_id, {})
            if guild:
                return guild.get("queue_msg", [])
            return []
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            if "queue_msg" not in store[guild_id]:
                store[guild_id]["queue_msg"] = []
            if msg is not None:
                store[guild_id]["queue_msg"].append(msg)
        case "clear":
            if guild_id in store and "queue_msg" in store[guild_id]:
                del store[guild_id]["queue_msg"]


# Equalizer
def equalizer(guild_id: int, name: str | None = None, mode: Literal["get", "set", "clear"] = "get") -> str | None:
    """
    Gets or sets the equalizer settings for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        name (str | None): The equalizer name to set, or None to get the current value.
        mode (str): The operation mode, either "get", "set" or "clear".
    """
    match mode:
        case "get":
            guild = store.get(guild_id, {})
            if guild:
                return guild.get("equalizer", None)
            return None
        case "set":
            if guild_id not in store:
                store[guild_id] = {}
            store[guild_id]["equalizer"] = name
        case "clear":
            if guild_id in store and "equalizer" in store[guild_id]:
                del store[guild_id]["equalizer"]


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
