import discord
from babel.dates import format_timedelta
from collections.abc import Callable
from datetime import timedelta
from square.logs.card import Row, person_id
from typing import Any


def _text(value: Any) -> str:
    return f"`{value}`" if value not in (None, "") else "Empty"


def _yes(value: Any) -> str:
    return "Yes" if value else "No"


def _channel(value: Any) -> str:
    return f"<#{value}>" if value else "No channel"


def _user(value: Any) -> str:
    return person_id(int(value)) if value else "Nobody"


def _seconds(value: Any) -> str:
    if not value:
        return "Off"
    return format_timedelta(timedelta(seconds=int(value)), threshold=1.1, locale="en")


def _minutes(value: Any) -> str:
    return _seconds(int(value) * 60) if value else "Off"


def _color(value: Any) -> str:
    return f"`#{int(value):06x}`" if value else "Default"


def _changed(_: Any) -> str:
    return "Changed"


def _limit(value: Any) -> str:
    return str(value) if value else "No limit"


def _enum(kind: type[discord.Enum]) -> Callable[[Any], str]:
    def show(value: Any) -> str:
        found = discord.enums.try_enum(kind, value)
        return str(getattr(found, "name", value)).replace("_", " ").capitalize()

    return show


# Only these keys are shown. Everything else Discord reports (positions, internal flags) would only add noise
_KEYS: dict[str, tuple[str, str, Callable[[Any], str]]] = {
    "name": ("keyboard", "Name", _text),
    "topic": ("topic", "Topic", _text),
    "description": ("topic", "Description", _text),
    "nsfw": ("lock", "Age-Restricted", _yes),
    "rate_limit_per_user": ("duration", "Slowmode", _seconds),
    "bitrate": ("mic", "Bitrate", lambda value: f"{int(value) // 1000} kbps"),
    "user_limit": ("members", "User Limit", _limit),
    "parent_id": ("category", "Category", _channel),
    "type": ("label", "Type", _enum(discord.ChannelType)),
    "archived": ("archive", "Closed", _yes),
    "locked": ("lock", "Locked", _yes),
    "auto_archive_duration": ("date", "Hide After", _minutes),
    "color": ("img", "Color", _color),
    "hoist": ("members", "Shown Separately", _yes),
    "mentionable": ("mention", "Mentionable", _yes),
    "icon_hash": ("star", "Icon", _changed),
    "unicode_emoji": ("star", "Icon", _text),
    "avatar_hash": ("img", "Avatar", _changed),
    "banner_hash": ("img", "Banner", _changed),
    "splash_hash": ("boost", "Invite Background", _changed),
    "owner_id": ("crown", "Owner", _user),
    "afk_channel_id": ("voice", "AFK Channel", _channel),
    "afk_timeout": ("duration", "AFK Timeout", _seconds),
    "system_channel_id": ("channel", "System Channel", _channel),
    "rules_channel_id": ("warning", "Rules Channel", _channel),
    "public_updates_channel_id": ("ping", "Updates Channel", _channel),
    "verification_level": ("verification", "Verification Level", _enum(discord.VerificationLevel)),
    "explicit_content_filter": ("lock", "Content Filter", _enum(discord.ContentFilter)),
    "default_message_notifications": ("mention", "Notifications", _enum(discord.NotificationLevel)),
    "vanity_url_code": ("invite", "Vanity Link", _text),
    "code": ("invite", "Code", _text),
    "channel_id": ("channel", "Channel", _channel),
    "max_uses": ("members", "Max Uses", _limit),
    "max_age": ("duration", "Expires After", lambda value: _seconds(value) if value else "Never"),
    "temporary": ("user", "Temporary", _yes),
    "enabled": ("mod", "Turned On", _yes),
    "tags": ("star", "Emoji", _text),
}


def _permission_names(value: Any) -> set[str]:
    perms = discord.Permissions(int(value or 0))
    return {name.replace("_", " ").title() for name, on in perms if on}


def permission_rows(before: Any, after: Any) -> list[Row]:
    """A role's permissions, which are only ever on or off."""
    old, new = _permission_names(before), _permission_names(after)
    rows: list[Row] = []
    if gained := sorted(new - old):
        rows.append(("add", "Permissions Added", ", ".join(gained)))
    if lost := sorted(old - new):
        rows.append(("remove", "Permissions Removed", ", ".join(lost)))
    return rows


def overwrite_rows(changes: list[dict[str, Any]] | None) -> list[Row]:
    """A channel's permission overwrite, with Discord's three states: allowed, denied, or reset to neither."""
    old_allow, new_allow = (
        _permission_names(value(changes, "allow", old=True)),
        _permission_names(value(changes, "allow")),
    )
    old_deny, new_deny = _permission_names(value(changes, "deny", old=True)), _permission_names(value(changes, "deny"))
    rows: list[Row] = []
    if allowed := sorted(new_allow - old_allow):
        rows.append(("success", "Allowed", ", ".join(allowed)))
    if denied := sorted(new_deny - old_deny):
        rows.append(("error", "Denied", ", ".join(denied)))
    if reset := sorted((old_allow | old_deny) - (new_allow | new_deny)):
        rows.append(("reset", "Reset", ", ".join(reset)))
    return rows


def rows(
    changes: list[dict[str, Any]] | None, *, created: bool = False, deleted: bool = False, skip: frozenset = frozenset()
) -> list[Row]:
    """
    One row per change a person would care about.

    Updates read "old → new". A created thing shows only its new values and a deleted one only its old values, so
    a deleted channel still shows the name it had. Those leave out empty and default values like "Slowmode: Off".
    """
    found: list[Row] = []
    for change in changes or []:
        key, old, new = change.get("key"), change.get("old_value"), change.get("new_value")
        if key == "permissions":
            if created or deleted:
                continue
            found += permission_rows(old, new)
            continue
        if key not in _KEYS or key in skip:
            continue
        icon, label, show = _KEYS[key]
        empty = not (new if created else old) and key != "type"
        if (created or deleted) and (empty or show is _changed):
            continue
        if created:
            value = show(new)
        elif deleted:
            value = show(old)
        elif show is _changed:
            value = show(new)
        else:
            value = f"{show(old)} → {show(new)}"
        found.append((icon, label, value))
    return found


def value(changes: list[dict[str, Any]] | None, key: str, *, old: bool = False) -> Any:
    for change in changes or []:
        if change.get("key") == key:
            return change.get("old_value" if old else "new_value")
    return None


def has(changes: list[dict[str, Any]] | None, key: str) -> bool:
    return any(change.get("key") == key for change in changes or [])
