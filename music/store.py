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
            if guild:
                return (guild.get("play_msg", None), guild.get("play_msg_view", None))
            return None
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
