import asyncio
from typing import Any, Literal

obj = {}


# Play channel
def play_ch(guild_id: int, channel: Any | None = None, mode: Literal["get", "set"] = "get"):
    """
    Gets or sets the play channel for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        channel (Any | None): The channel to set, or None to get the current value.
        mode (str): The operation mode, either "get" or "set".
    """
    match mode:
        case "get":
            return obj.get(f"{str(guild_id)}-play_ch", None)
        case "set":
            obj.update({f"{str(guild_id)}-play_ch": channel})


# Play msg
def play_msg(guild_id: int, msg: Any | None = None, mode: Literal["get", "set"] = "get"):
    """
    Gets or sets the play message for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        msg (Any | None): The message to set, or None to get the current value.
        mode (str): The operation mode, either "get" or "set".
    """
    match mode:
        case "get":
            return obj.get(f"{str(guild_id)}-play_msg", None)
        case "set":
            obj.update({f"{str(guild_id)}-play_msg": msg})


# Queue msg
def queue_msg(guild_id: int, msg: Any | None = None, mode: Literal["get", "set", "clear"] = "get"):
    """
    Gets or sets the queue message for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        msg (Any | None): The message to set, or None to get the current value.
        mode (str): The operation mode, either "get", "set", or "clear".
    """
    match mode:
        case "get":
            if obj.__contains__(f"{str(guild_id)}-queue_msgs"):
                return obj.get(f"{str(guild_id)}-queue_msgs", None)
            else:
                return []
        case "set":
            if obj.__contains__(f"{str(guild_id)}-queue_msgs"):
                obj[f"{str(guild_id)}-queue_msgs"].append(msg)
            else:
                obj.update({f"{str(guild_id)}-queue_msgs": [msg]})
        case "clear":
            obj.update({f"{str(guild_id)}-queue_msgs": []})


# Equalizer
def equalizer(guild_id: int, name: str = None, mode: Literal["get", "set"] = "get"):
    """
    Gets or sets the equalizer settings for a guild.

    Parameters:
        guild_id (int): The ID of the guild.
        name (str | None): The name of the equalizer to set, or None to get the current value.
        mode (str): The operation mode, either "get" or "set".
    """
    match mode:
        case "get":
            return obj.get(f"{str(guild_id)}-equalizer", None)
        case "set":
            obj.update({f"{str(guild_id)}-equalizer": name})


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
            return obj.get(f"{str(guild_id)}-inactivity_task", None)
        case "set":
            obj.update({f"{str(guild_id)}-inactivity_task": task})
        case "clear":
            obj.update({f"{str(guild_id)}-inactivity_task": None})
