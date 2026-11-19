import enum
from typing import Literal, get_args


class Log(enum.StrEnum):
    MODERATION = "moderation"
    AUTOMOD = "automod"
    MEMBERS = "members"
    MESSAGES = "messages"
    VOICE = "voice"
    SERVER = "server"
    TICKETS = "tickets"

    @property
    def label(self) -> str:
        return "AutoMod" if self is Log.AUTOMOD else self.value.capitalize()


Event = Literal[
    "bans",
    "kicks",
    "timeouts",
    "warnings",
    "discord_rules",
    "square_rules",
    "joins",
    "leaves",
    "nicknames",
    "member_roles",
    "profiles",
    "edits",
    "deletes",
    "purges",
    "pins",
    "voice_activity",
    "voice_moderation",
    "channels",
    "roles",
    "server_profile",
    "emojis",
    "invites",
    "webhooks",
    "bots",
    "automod_rules",
]

EVENTS: dict[Event, Log] = {
    "bans": Log.MODERATION,
    "kicks": Log.MODERATION,
    "timeouts": Log.MODERATION,
    "warnings": Log.MODERATION,
    "discord_rules": Log.AUTOMOD,
    "square_rules": Log.AUTOMOD,
    "joins": Log.MEMBERS,
    "leaves": Log.MEMBERS,
    "nicknames": Log.MEMBERS,
    "member_roles": Log.MEMBERS,
    "profiles": Log.MEMBERS,
    "edits": Log.MESSAGES,
    "deletes": Log.MESSAGES,
    "purges": Log.MESSAGES,
    "pins": Log.MESSAGES,
    "voice_activity": Log.VOICE,
    "voice_moderation": Log.VOICE,
    "channels": Log.SERVER,
    "roles": Log.SERVER,
    "server_profile": Log.SERVER,
    "emojis": Log.SERVER,
    "invites": Log.SERVER,
    "webhooks": Log.SERVER,
    "bots": Log.SERVER,
    "automod_rules": Log.SERVER,
}

# Tickets has no events to switch off: its cards are posted and edited in place, see `logs.post`
if set(EVENTS) != set(get_args(Event)):
    raise RuntimeError("Every log event needs a log")

# Mod records stay complete: ignored channels, roles and bots never hide these
UNFILTERED = frozenset((Log.MODERATION, Log.AUTOMOD, Log.TICKETS))
