"""
Works out which permissions a refused Discord call wanted.

Discord's 403 never names the permission, but py-cord's docstrings do. The traceback leads to the library method that
failed, its docs to the permissions it wants, and the bot's live permissions to the ones it actually lacks.
"""

import discord
import inspect
import re
import traceback
from collections.abc import Iterator
from dataclasses import dataclass, field
from types import FrameType, TracebackType

_PERMISSION = re.compile(r"Permissions\.(\w+)|`+(\w+)`+")
_SAME_AS = re.compile(r"(?:Same as|similar to) :meth:`[.~]*(\w+)`")
_FORBIDDEN_SECTION = re.compile(r"Forbidden\s*\n\s+(.+(?:\n[ \t]+\S.*)*)")
_FIRST_PERSON = {
    "You do not have": "I don't have",
    "You don't have": "I don't have",
    "You are not allowed": "I'm not allowed",
}


@dataclass
class Refusal:
    """
    What a refused call was trying to do.

    Attributes:
        action (str | None): The library's description of the refusal, reworded as the bot speaking.
        needed (list[str]): Permissions the call's docs name. Empty when they name none.
        missing (list[str]): The `needed` ones the bot doesn't have.
        place (str | None): A mention of the channel the permissions were checked in.
    """

    action: str | None = None
    needed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    place: str | None = None


def _library_frames(tb: TracebackType | None) -> Iterator[FrameType]:
    """The py-cord frames at the end of a traceback, innermost first, stopping at the code that called into it."""
    for frame in reversed([frame for frame, _ in traceback.walk_tb(tb)]):
        if not frame.f_globals.get("__name__", "").startswith("discord"):
            return
        yield frame


def _running_function(frame: FrameType) -> object | None:
    parts = frame.f_code.co_qualname.split(".")
    if "<locals>" in parts:
        return None
    found = frame.f_globals.get(parts[0])
    for part in parts[1:]:
        found = getattr(found, part, None)
    return found


def _permissions_in(doc: str, owner: object | None = None) -> list[str]:
    """The permissions a docstring names, following a "Same as :meth:`x`" to the method it defers to."""
    named = (first or second for first, second in _PERMISSION.findall(doc))
    found = list(dict.fromkeys(name for name in named if name in discord.Permissions.VALID_FLAGS))
    if not found and (same_as := _SAME_AS.search(doc)):
        if other := inspect.getdoc(getattr(owner, same_as.group(1), None)):
            return _permissions_in(other, owner)
    return found


def _action_in(doc: str) -> str | None:
    """The docstring's Forbidden entry as the bot speaking, when it's worded so that reads naturally."""
    if not (section := _FORBIDDEN_SECTION.search(doc)):
        return None
    text = " ".join(section.group(1).split())
    for you, me in _FIRST_PERSON.items():
        if text.startswith(you):
            return text.replace(you, me, 1)
    return None


def explain(error: discord.Forbidden, guild: discord.Guild | None, channel: object | None = None) -> Refusal:
    """
    Explains a 403 from the call that raised it.

    Args:
        error (:class:`discord.Forbidden`): The refusal, with its traceback.
        guild (:class:`discord.Guild` | None): The guild it happened in.
        channel (object | None): Where it happened, used when the call wasn't made on a channel.

    Returns:
        :class:`Refusal`: As much as could be worked out. Everything is empty for a call with no docs.
    """
    refusal = Refusal()
    subject = None
    for frame in _library_frames(error.__traceback__):
        if not (doc := inspect.getdoc(_running_function(frame))):
            continue
        subject = frame.f_locals.get("self", subject)
        refusal.action = refusal.action or _action_in(doc)
        if needed := _permissions_in(doc, type(subject)):
            refusal.needed = needed
            break
    if not refusal.needed or guild is None or guild.me is None:
        return refusal
    # A message's permissions are its channel's. A guild, member or role has no channel, so server-wide ones apply.
    target = subject if hasattr(subject, "permissions_for") else getattr(subject, "channel", None)
    if hasattr(target, "permissions_for"):
        permissions = target.permissions_for(guild.me)
        refusal.place = getattr(target, "mention", None)
    else:
        permissions = guild.me.guild_permissions
    refusal.missing = [name for name in refusal.needed if not getattr(permissions, name, False)]
    return refusal
