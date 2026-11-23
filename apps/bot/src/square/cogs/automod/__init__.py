import asyncio
import discord
import time
from discord.ext import commands
from square import logs
from square.cogs.automod import rules
from square.cogs.automod.rules import LABELS, NOTICES
from square.cogs.moderation.warnings import warn
from square.core import Client
from square.core.cog import Cog
from square.core.view import error_view
from square.db.funcs import automod as automod_db
from square.db.schema import AutomodRuleTable
from square.utils.helpers import fmt_count, plural

_CHECKED = (discord.MessageType.default, discord.MessageType.reply)
_TEXT_KINDS = (
    "invites",
    "masked_links",
    "new_members",
    "caps",
    "emojis",
    "zalgo",
    "fonts",
    "repeated_chars",
    "lines",
    "invisible",
)
_ORDER = (
    "media",
    "invites",
    "masked_links",
    "new_members",
    "duplicates",
    "flood",
    "mention_flood",
    "file_flood",
    "invisible",
    "zalgo",
    "fonts",
    "repeated_chars",
    "lines",
    "caps",
    "emojis",
)
_SHOWN_PINGS = 5


def _watched(message: discord.Message) -> bool:
    return (
        message.guild is not None
        and isinstance(message.author, discord.Member)
        and not message.author.bot
        and message.webhook_id is None
        and message.type in _CHECKED
        and not message.author.guild_permissions.manage_messages
    )


def _pinged(message: discord.Message) -> list[str]:
    found = [user.mention for user in message.mentions if user.id != message.author.id and not user.bot]
    found += [role.mention for role in message.role_mentions]
    if message.mention_everyone:
        found.append("@everyone" if "@everyone" in message.content else "@here")
    return found


def _joined(minutes: float) -> str:
    if minutes < 1:
        return "Joined under a minute ago"
    whole = int(minutes)
    return f"Joined {whole} {plural(whole, 'minute')} ago"


class AutoMod(Cog):
    def __init__(self, client: Client):
        self.client = client
        self.recent = rules.Recent()
        self._removed: dict[int, None] = {}
        self._audit_counts: dict[int, int] = {}

    def _active(self, message: discord.Message, kinds: tuple[str, ...]) -> list[AutomodRuleTable]:
        found = automod_db.rules(message.guild.id)
        return [
            rule
            for kind in kinds
            if (rule := found.get(kind)) and rule.enabled and not rules.exempt(rule, message.author, message.channel)
        ]

    async def _hit(self, message: discord.Message, rule: AutomodRuleTable, sent) -> str | None:
        match rule.kind:
            case "media":
                if message.channel.id in rule.channel_ids and not rules.has_media(message):
                    return "No file or link"
            case "new_members":
                joined = message.author.joined_at
                if joined and (message.attachments or rules.has_link(message.content)):
                    minutes = (discord.utils.utcnow() - joined).total_seconds() / 60
                    if minutes < (rule.amount or 0):
                        return _joined(minutes)
            case kind if kind in rules.WINDOW_KINDS:
                return rules.window_hit(rule, sent)
            case _:
                return await rules.content_hit(self.client, message.guild, rule, message.content)
        return None

    async def _check(self, message: discord.Message, kinds: tuple[str, ...]) -> None:
        active = self._active(message, kinds)
        if not active:
            return
        sent = None
        if windowed := frozenset(rule.kind for rule in active if rule.kind in rules.WINDOW_KINDS):
            entry = rules.Sent(
                at=time.monotonic(),
                text=rules.same_text(message.content),
                mentions=rules.mention_count(message.content) + message.mention_everyone,
                files=len(message.attachments) + len(message.stickers),
                kinds=windowed,
            )
            sent = self.recent.add(message.guild.id, message.author.id, entry)
        for rule in active:
            if detail := await self._hit(message, rule, sent):
                await self._act(message, rule, detail)
                return

    def _remember_removed(self, message_id: int) -> None:
        self._removed[message_id] = None
        if len(self._removed) > 1000:
            del self._removed[next(iter(self._removed))]

    async def _removed_by_someone(self, message: discord.Message) -> bool:
        """
        Whether a moderator, another bot or Square deleted it rather than the author.

        Discord only logs deletes done by someone other than the author. It folds repeat deletes of one member's
        messages into an older entry and raises its count, so counts are remembered between checks.
        """
        if message.id in self._removed:
            return True
        guild = message.guild
        if not guild.me.guild_permissions.view_audit_log:
            return False
        await asyncio.sleep(1)
        found = False
        try:
            async for entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.message_delete):
                channel = getattr(entry.extra, "channel", None)
                if not (entry.target and entry.target.id == message.author.id and channel):
                    continue
                if channel.id != message.channel.id:
                    continue
                count = getattr(entry.extra, "count", 1)
                seen = self._audit_counts.get(entry.id)
                fresh = (discord.utils.utcnow() - entry.created_at).total_seconds() < 15
                if (seen is None and fresh) or (seen is not None and count > seen):
                    found = True
                self._audit_counts[entry.id] = count
        except discord.HTTPException:
            return False
        if len(self._audit_counts) > 1000:
            self._audit_counts.clear()
        return found

    async def _act(
        self, message: discord.Message, rule: AutomodRuleTable, detail: str, pinged: list[str] | None = None
    ) -> None:
        guild, member = message.guild, message.author
        deleted = False
        if rule.delete_message and rule.kind != "ghost_pings":
            try:
                self._remember_removed(message.id)
                logs.acting(guild.id, discord.AuditLogAction.message_delete, member.id, "AutoMod")
                await message.delete(reason=f"AutoMod: {LABELS[rule.kind]}")
                deleted = True
            except discord.Forbidden, discord.NotFound:
                pass
        # Window rules fire on every message of a burst: the rest are only deleted, never warned or logged
        if rule.kind in rules.WINDOW_KINDS and not self.recent.once(guild.id, member.id, rule.kind, rule.seconds or 60):
            return
        warned = await warn(self.client, guild, member, f"AutoMod: {LABELS[rule.kind]}", None) if rule.warn else None
        ghost = rule.kind == "ghost_pings"
        if rule.notify and (deleted or warned or ghost):
            notice = NOTICES[rule.kind].format(pinged=", ".join(pinged or []))
            note = f"{member.mention} {notice}" + (" You got a warning." if warned else "")
            try:
                # The ghost ping notice stays so the people pinged can still see who it was
                await message.channel.send(
                    view=error_view(note),
                    allowed_mentions=discord.AllowedMentions(users=[member]),
                    delete_after=None if ghost else 10,
                )
            except discord.Forbidden, discord.HTTPException:
                pass
        notified = ghost and rule.notify
        actions = [label for label, done in (("Deleted", deleted), ("Warned", warned), ("Posted", notified)) if done]
        entry = logs.Entry("square_rules", "Square Rule Triggered", "red", channel_id=message.channel.id, member=member)
        entry.add("user", "Member", logs.person(member)).add("id", "ID", f"`{member.id}`")
        entry.add("mod", "Rule", LABELS[rule.kind]).add("warning", "Why", detail)
        entry.add("channel", "Channel", message.channel.mention).add("members", "Pinged", ", ".join(pinged or []))
        entry.add("bin", "Action", ", ".join(actions) or "Only logged")
        entry.add("note", "Content", f"\n{logs.clip(message.content, 512)}" if message.content else None)
        logs.emit(guild, entry)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if _watched(message):
            await self._check(message, _ORDER)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content and _watched(after):
            await self._check(after, _TEXT_KINDS)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not _watched(message):
            self._removed.pop(message.id, None)
            return
        active = self._active(message, ("ghost_pings",))
        pinged = _pinged(message)
        if not active or not pinged:
            self._removed.pop(message.id, None)
            return
        rule = active[0]
        seconds = (discord.utils.utcnow() - message.created_at).total_seconds()
        if seconds > (rule.seconds or 60) or await self._removed_by_someone(message):
            self._removed.pop(message.id, None)
            return
        shown = pinged[:_SHOWN_PINGS] + (
            [f"{fmt_count(len(pinged) - _SHOWN_PINGS)} more"] if len(pinged) > _SHOWN_PINGS else []
        )
        await self._act(message, rule, f"Deleted {max(1, round(seconds))}s after sending", shown)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        self.recent.forget(guild.id)


def setup(client: Client):
    client.add_cog(AutoMod(client))
