"""
Square's server logs.

Listeners and features describe what happened as an `Entry` and call `emit`. The sender filters it with the server's
settings, queues it per log channel and posts a few cards per message through a webhook.
"""

from square.logs.acting import acted_for, acting
from square.logs.card import Entry, clip, person, person_id, when
from square.logs.catalog import EVENTS, Event, Log
from square.logs.sender import bind, edit, emit, ignored, post

__all__ = [
    "EVENTS",
    "Entry",
    "Event",
    "Log",
    "acted_for",
    "acting",
    "bind",
    "clip",
    "edit",
    "emit",
    "ignored",
    "person",
    "person_id",
    "post",
    "when",
]
