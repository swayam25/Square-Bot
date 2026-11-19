import datetime
import discord
import time
from babel.dates import format_timedelta
from square.core import Client
from square.logs import Entry, acted_for, person, person_id
from square.logs import changes as diff
from square.logs.card import Tone
from typing import Any

A = discord.AuditLogAction

# Discord sends the audit log entry and the event it explains separately, in either order
RECENT_SECONDS = 10

_recent: dict[tuple, tuple[str, float]] = {}


def note(key: tuple, actor: str) -> None:
    now = time.monotonic()
    _recent[key] = (actor, now)
    if len(_recent) > 1000:
        for stale in [key for key, (_, at) in _recent.items() if now - at > RECENT_SECONDS]:
            del _recent[stale]


def recent(key: tuple) -> str | None:
    found = _recent.pop(key, None)
    return found[0] if found and time.monotonic() - found[1] <= RECENT_SECONDS else None


def _actor(client: Client, payload: discord.RawAuditLogEntryEvent) -> str:
    if payload.user_id is None:
        return "Unknown"
    if client.user and payload.user_id == client.user.id:
        target = payload.target_id or 0
        return acted_for(payload.guild_id, payload.action_type, target) or person(client.user)
    user = client.get_user(payload.user_id)
    return person(user) if user else person_id(payload.user_id)


def _member(guild: discord.Guild, client: Client, user_id: int | None) -> tuple[str, discord.abc.User | None]:
    if user_id is None:
        return "Unknown", None
    user = guild.get_member(user_id) or client.get_user(user_id)
    return (person(user) if user else person_id(user_id)), user


def _mod_entry(event: Any, title: str, tone: Tone, guild: discord.Guild, client: Client, payload, actor: str) -> Entry:
    shown, user = _member(guild, client, payload.target_id)
    entry = Entry(event, title, tone, thumbnail=user.display_avatar.url if user else None)
    entry.add("user", "Member", shown).add("id", "ID", f"`{payload.target_id}`")
    entry.add("owner", "Moderator", actor).add("note", "Reason", payload.reason or "No reason given")
    return entry


def _roles_text(values: list[dict] | None) -> str | None:
    return ", ".join(f"<@&{role['id']}>" for role in values) if values else None


def _until(value: str | None) -> datetime.datetime | None:
    return datetime.datetime.fromisoformat(value) if value else None


def _target_channel(guild: discord.Guild, channel_id: int | None, name: str | None) -> str:
    if channel_id and guild.get_channel_or_thread(channel_id):
        return f"<#{channel_id}>"
    return f"`{name}`" if name else f"`{channel_id}`"


def entry_for(client: Client, guild: discord.Guild, payload: discord.RawAuditLogEntryEvent) -> Entry | None:
    action, changes, extra = payload.action_type, payload.changes, payload.extra or {}
    actor = _actor(client, payload)
    reason = payload.reason

    match action:
        case A.ban:
            return _mod_entry("bans", "Member Banned", "red", guild, client, payload, actor)
        case A.unban:
            return _mod_entry("bans", "Member Unbanned", "green", guild, client, payload, actor)
        case A.kick:
            return _mod_entry("kicks", "Member Kicked", "red", guild, client, payload, actor)

        case A.member_update:
            if diff.has(changes, "communication_disabled_until"):
                until = _until(diff.value(changes, "communication_disabled_until"))
                if until and until > discord.utils.utcnow():
                    entry = _mod_entry("timeouts", "Member Timed Out", "orange", guild, client, payload, actor)
                    length = until - discord.utils.snowflake_time(payload.id)
                    return entry.add("duration", "Duration", format_timedelta(length, locale="en"))
                return _mod_entry("timeouts", "Timeout Removed", "green", guild, client, payload, actor)
            if diff.has(changes, "nick"):
                shown, user = _member(guild, client, payload.target_id)
                entry = Entry(
                    "nicknames", "Nickname Changed", member=user if isinstance(user, discord.Member) else None
                )
                entry.thumbnail = user.display_avatar.url if user else None
                old, new = diff.value(changes, "nick", old=True), diff.value(changes, "nick")
                entry.add("user", "Member", shown).add("id", "ID", f"`{payload.target_id}`")
                entry.add("note_red", "Before", f"`{old}`" if old else "No nickname")
                entry.add("note", "After", f"`{new}`" if new else "No nickname")
                if payload.user_id != payload.target_id:
                    entry.add("owner", "Changed By", actor)
                return entry
            for key, on, off in (
                ("mute", "Server Muted", "Server Unmuted"),
                ("deaf", "Server Deafened", "Server Undeafened"),
            ):
                if diff.has(changes, key):
                    shown, user = _member(guild, client, payload.target_id)
                    entry = Entry("voice_moderation", on if diff.value(changes, key) else off, "orange")
                    entry.member = user if isinstance(user, discord.Member) else None
                    entry.add("user", "Member", shown).add("owner", "Moderator", actor)
                    return entry.add("note", "Reason", reason)
            return None

        case A.member_role_update:
            shown, user = _member(guild, client, payload.target_id)
            added = _roles_text(diff.value(changes, "$add"))
            removed = _roles_text(diff.value(changes, "$remove"))
            if not (added or removed):
                return None
            entry = Entry("member_roles", "Roles Changed", member=user if isinstance(user, discord.Member) else None)
            entry.thumbnail = user.display_avatar.url if user else None
            entry.add("user", "Member", shown).add("id", "ID", f"`{payload.target_id}`")
            entry.add("add", "Added", added).add("remove", "Removed", removed)
            return entry.add("owner", "Changed By", actor).add("note", "Reason", reason)

        case A.member_move:
            note(("move", guild.id, int(extra.get("channel_id", 0))), actor)
            return None
        case A.member_disconnect:
            note(("disconnect", guild.id), actor)
            return None
        case A.message_delete:
            note(("delete", guild.id, int(extra.get("channel_id", 0)), payload.target_id), actor)
            return None
        case A.message_bulk_delete:
            note(("purge", guild.id, payload.target_id), actor)
            return None

        case A.message_pin | A.message_unpin:
            channel_id, message_id = int(extra.get("channel_id", 0)), int(extra.get("message_id", 0))
            pinned = action is A.message_pin
            entry = Entry("pins", "Message Pinned" if pinned else "Message Unpinned", channel_id=channel_id)
            entry.add("owner", "Author", _member(guild, client, payload.target_id)[0])
            entry.add("channel", "Channel", f"<#{channel_id}>").add(
                "user", "Pinned By" if pinned else "Unpinned By", actor
            )
            entry.jump = f"https://discord.com/channels/{guild.id}/{channel_id}/{message_id}"
            return entry

        case (
            A.channel_create | A.channel_update | A.channel_delete | A.thread_create | A.thread_update | A.thread_delete
        ):
            thread = action in (A.thread_create, A.thread_update, A.thread_delete)
            created, deleted = (
                action in (A.channel_create, A.thread_create),
                action in (A.channel_delete, A.thread_delete),
            )
            kind = "Thread" if thread else "Channel"
            verb, tone = ("Created", "green") if created else ("Deleted", "red") if deleted else ("Updated", "theme")
            rows = diff.rows(changes, created=created, deleted=deleted)
            if not (created or deleted) and not rows:
                return None
            name = diff.value(changes, "name", old=deleted)
            entry = Entry("channels", f"{kind} {verb}", tone, channel_id=payload.target_id)
            entry.add("channel", kind, _target_channel(guild, None if deleted else payload.target_id, name))
            entry.rows += [row for row in rows if not (row[1] == "Name" and (created or deleted))]
            return entry.add("owner", f"{verb} By", actor).add("note", "Reason", reason)

        case A.overwrite_create | A.overwrite_update | A.overwrite_delete:
            target_id = int(extra.get("id", 0))
            who = f"<@&{target_id}>" if str(extra.get("type")) in ("0", "role") else person_id(target_id)
            if target_id == guild.id:
                who = "@everyone"
            if action is A.overwrite_delete:
                rows = [("reset", "Reset", "Every permission")]
            else:
                rows = diff.overwrite_rows(changes)
            if not rows:
                return None
            entry = Entry("channels", "Channel Permissions Changed", channel_id=payload.target_id)
            entry.add("channel", "Channel", f"<#{payload.target_id}>").add("perms", "For", who)
            entry.rows += rows
            return entry.add("owner", "Changed By", actor).add("note", "Reason", reason)

        case A.role_create | A.role_update | A.role_delete:
            created, deleted = action is A.role_create, action is A.role_delete
            verb, tone = ("Created", "green") if created else ("Deleted", "red") if deleted else ("Updated", "theme")
            rows = diff.rows(changes, created=created, deleted=deleted)
            if not (created or deleted) and not rows:
                return None
            name = diff.value(changes, "name", old=deleted)
            shown = f"`{name}`" if deleted or not guild.get_role(payload.target_id or 0) else f"<@&{payload.target_id}>"
            entry = Entry("roles", f"Role {verb}", tone)
            # The role's color as the thumbnail when it's created, deleted or recolored. The default color has none
            if (color := diff.value(changes, "color", old=deleted)) and (created or diff.has(changes, "color")):
                entry.swatch = int(color)
            entry.add("role", "Role", shown)
            entry.rows += [row for row in rows if not (row[1] == "Name" and (created or deleted))]
            return entry.add("owner", f"{verb} By", actor).add("note", "Reason", reason)

        case A.guild_update:
            if not (rows := diff.rows(changes)):
                return None
            entry = Entry("server_profile", "Server Updated", thumbnail=guild.icon.url if guild.icon else None)
            entry.rows += rows
            return entry.add("owner", "Updated By", actor).add("note", "Reason", reason)

        case A.emoji_create | A.emoji_update | A.emoji_delete | A.sticker_create | A.sticker_update | A.sticker_delete:
            sticker = action in (A.sticker_create, A.sticker_update, A.sticker_delete)
            created = action in (A.emoji_create, A.sticker_create)
            deleted = action in (A.emoji_delete, A.sticker_delete)
            verb, tone = ("Added", "green") if created else ("Deleted", "red") if deleted else ("Updated", "theme")
            name = diff.value(changes, "name", old=deleted)
            found = None if sticker else guild.get_emoji(payload.target_id or 0)
            entry = Entry("emojis", f"{'Sticker' if sticker else 'Emoji'} {verb}", tone)
            entry.add("img", "Sticker" if sticker else "Emoji", f"{found} `{name}`" if found else f"`{name}`")
            if not (created or deleted):
                entry.rows += diff.rows(changes)
            return entry.add("owner", f"{verb} By", actor)

        case A.invite_create | A.invite_delete:
            created = action is A.invite_create
            entry = Entry("invites", "Invite Created" if created else "Invite Deleted", "green" if created else "red")
            entry.rows += diff.rows(changes, created=created, deleted=not created)
            return entry.add("owner", "Created By" if created else "Deleted By", actor)

        case A.webhook_create | A.webhook_update | A.webhook_delete:
            created, deleted = action is A.webhook_create, action is A.webhook_delete
            verb, tone = ("Created", "green") if created else ("Deleted", "red") if deleted else ("Updated", "theme")
            rows = diff.rows(changes, created=created, deleted=deleted, skip=frozenset({"type"}))
            if not (created or deleted) and not rows:
                return None
            entry = Entry("webhooks", f"Webhook {verb}", tone)
            entry.rows += rows
            return entry.add("owner", f"{verb} By", actor)

        case A.bot_add:
            shown, user = _member(guild, client, payload.target_id)
            entry = Entry("bots", "Bot Added", "green", thumbnail=user.display_avatar.url if user else None)
            return (
                entry.add("bot", "Bot", shown).add("id", "ID", f"`{payload.target_id}`").add("owner", "Added By", actor)
            )

        case A.auto_moderation_rule_create | A.auto_moderation_rule_update | A.auto_moderation_rule_delete:
            created, deleted = action is A.auto_moderation_rule_create, action is A.auto_moderation_rule_delete
            verb, tone = ("Created", "green") if created else ("Deleted", "red") if deleted else ("Updated", "theme")
            name = diff.value(changes, "name", old=deleted) or diff.value(changes, "name", old=True)
            entry = Entry("automod_rules", f"AutoMod Rule {verb}", tone)
            entry.add("mod", "Rule", f"`{name}`" if name else None)
            if not (created or deleted):
                labels = sorted({str(change.get("key", "")).replace("_", " ") for change in changes or []})
                entry.add("note", "Changed", ", ".join(labels).capitalize() if labels else None)
            return entry.add("owner", f"{verb} By", actor)

    return None
