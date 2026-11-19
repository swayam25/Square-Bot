import asyncio
import datetime
import discord
import io
from discord.ext import commands
from square.cogs.logs import audit
from square.core import Client
from square.core.cog import Cog
from square.db import cache
from square.logs import Entry, Log, clip, emit, memory, person, person_id, when
from square.logs import sender as log_sender
from square.modules import Module
from square.utils import invites, webhook
from square.utils.helpers import fmt_count, plural

# Time for Discord's audit log entry to arrive, so the log can say who deleted or moved something
AUDIT_WAIT = 1.5
_SHOWN_FILES = 10


def _files(names: tuple[str, ...]) -> str | None:
    if not names:
        return None
    shown = ", ".join(f"`{name}`" for name in names[:_SHOWN_FILES])
    return shown + (f" and {len(names) - _SHOWN_FILES} more" if len(names) > _SHOWN_FILES else "")


def _author(guild: discord.Guild, saved: memory.Saved) -> tuple[str, discord.Member | None]:
    member = guild.get_member(saved.author_id)
    return f"<@{saved.author_id}> (`{saved.author_name}`)", member


def _transcript(saved: list[memory.Saved]) -> discord.File:
    lines = []
    for message in saved:
        stamp = message.sent_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        extras = [f"files: {', '.join(message.files)}"] if message.files else []
        extras += [f"stickers: {', '.join(message.stickers)}"] if message.stickers else []
        tail = f" [{'; '.join(extras)}]" if extras else ""
        lines.append(f"[{stamp}] {message.author_name} ({message.author_id}): {message.content}{tail}")
    return discord.File(io.BytesIO("\n".join(lines).encode()), filename="messages.txt")


class Logs(Cog):
    def __init__(self, client: Client):
        self.client = client
        self._automod: dict[tuple, tuple[Entry, list[str]]] = {}
        self._rule_names: dict[int, str] = {}
        log_sender.bind(client)

    async def _waited_actor(self, guild: discord.Guild, key: tuple) -> str | None:
        if not guild.me.guild_permissions.view_audit_log:
            return None
        await asyncio.sleep(AUDIT_WAIT)
        return audit.recent(key)

    @commands.Cog.listener()
    async def on_raw_audit_log_entry(self, payload: discord.RawAuditLogEntryEvent):
        guild = self.client.get_guild(payload.guild_id)
        if guild is not None and (entry := audit.entry_for(self.client, guild, payload)):
            emit(guild, entry)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if cache.log_channel(member.guild.id, Log.MEMBERS) is None:
            return
        used = await invites.used_invite(member)
        if used and used.inviter_id:
            inviter = self.client.get_user(used.inviter_id)
            invited_by = person(inviter) if inviter else person_id(used.inviter_id)
        else:
            invited_by = "Unknown" if not member.bot else None
        entry = Entry("joins", "Member Joined", "green", thumbnail=member.display_avatar.url, member=member)
        entry.add("user", "Member", person(member)).add("id", "ID", f"`{member.id}`")
        entry.add("date", "Account Created", when(member.created_at))
        entry.add("owner", "Invited By", invited_by).add("invite", "Code", f"`{used.code}`" if used else None)
        fake_days = cache.get(member.guild.id).invite_fake_days
        if used and cache.enabled(member.guild.id, Module.INVITES) and fake_days:
            if discord.utils.utcnow() - member.created_at < datetime.timedelta(days=fake_days):
                entry.add("warning", "Fake", f"The account is newer than {fake_days} {plural(fake_days, 'day')}")
        entry.add("members", "Member Count", fmt_count(member.guild.member_count or 0))
        emit(member.guild, entry)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        roles = [role.mention for role in reversed(member.roles) if role != member.guild.default_role]
        entry = Entry("leaves", "Member Left", "red", thumbnail=member.display_avatar.url, member=member)
        entry.add("user", "Member", person(member)).add("id", "ID", f"`{member.id}`")
        entry.add("date", "Joined", when(member.joined_at) if member.joined_at else None)
        entry.add("role", "Roles", clip(", ".join(roles), 512) if roles else None)
        emit(member.guild, entry)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        rows = []
        if before.name != after.name:
            rows.append(("mention", "Username", f"`{before.name}` → `{after.name}`"))
        if before.global_name != after.global_name:
            old, new = before.global_name or before.name, after.global_name or after.name
            rows.append(("label", "Display Name", f"`{old}` → `{new}`"))
        if before.avatar != after.avatar:
            rows.append(("img", "Avatar", "Changed"))
        if not rows:
            return
        for guild in after.mutual_guilds:
            member = guild.get_member(after.id)
            entry = Entry("profiles", "Profile Updated", thumbnail=after.display_avatar.url, member=member)
            entry.add("user", "Member", person(after)).add("id", "ID", f"`{after.id}`")
            entry.rows += rows
            emit(guild, entry)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild and not message.is_system():
            memory.remember(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        guild = self.client.get_guild(payload.guild_id) if payload.guild_id else None
        content = payload.data.get("content")
        if guild is None or content is None:
            return
        if before := memory.edited(guild.id, payload.channel_id, payload.message_id, content):
            shown, member = _author(guild, before)
            old, bot = (f"\n{clip(before.content)}" if before.content else "Empty"), before.bot
        elif (
            content
            and memory.unknown(guild, payload.channel_id, payload.message_id)
            and (author := payload.data.get("author"))
        ):
            member = guild.get_member(int(author["id"]))
            shown = f"<@{author['id']}> (`{author.get('username', author['id'])}`)"
            old, bot = "Not remembered, it's older than what Square keeps", bool(author.get("bot"))
        else:
            return
        entry = Entry("edits", "Message Edited", channel_id=payload.channel_id, member=member, bot=bot)
        entry.add("owner", "Author", shown).add("channel", "Channel", f"<#{payload.channel_id}>")
        entry.add("note_red", "Before", old)
        entry.add("note", "After", f"\n{clip(content)}" if content else "Empty")
        entry.link = (
            "Jump to message",
            f"https://discord.com/channels/{guild.id}/{payload.channel_id}/{payload.message_id}",
        )
        emit(guild, entry)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        guild = self.client.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None:
            return
        snipe = memory.deleted(guild.id, payload.channel_id, payload.message_id)
        if snipe is None:
            if memory.unknown(guild, payload.channel_id, payload.message_id):
                entry = Entry("deletes", "Message Deleted", "red", channel_id=payload.channel_id)
                entry.add("channel", "Channel", f"<#{payload.channel_id}>")
                entry.add("date", "Sent", when(discord.utils.snowflake_time(payload.message_id)))
                emit(guild, entry.add("note", "Message", "Not remembered, it's older than what Square keeps"))
            return
        saved = snipe.message
        snipe.deleted_by = await self._waited_actor(guild, ("delete", guild.id, payload.channel_id, saved.author_id))
        shown, member = _author(guild, saved)
        entry = Entry("deletes", "Message Deleted", "red", channel_id=payload.channel_id, member=member, bot=saved.bot)
        entry.add("owner", "Author", shown).add("channel", "Channel", f"<#{payload.channel_id}>")
        entry.add("date", "Sent", when(saved.sent_at)).add("user", "Deleted By", snipe.deleted_by)
        entry.add("img", "Files", _files(saved.files)).add("star", "Stickers", _files(saved.stickers))
        entry.add("note", "Message", f"\n{clip(saved.content)}" if saved.content else None)
        emit(guild, entry)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        guild = self.client.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None or cache.log_channel(guild.id, Log.MESSAGES) is None:
            return
        saved = memory.deleted_many(guild.id, payload.channel_id, payload.message_ids)
        by = await self._waited_actor(guild, ("purge", guild.id, payload.channel_id))
        count = len(payload.message_ids)
        entry = Entry("purges", "Messages Purged", "red", channel_id=payload.channel_id)
        entry.add("channel", "Channel", f"<#{payload.channel_id}>")
        entry.add("bin", "Messages", fmt_count(count)).add("user", "Purged By", by)
        if saved:
            entry.file = _transcript(saved)
            if len(saved) < count:
                entry.add("note", "Saved", f"Square only remembered {fmt_count(len(saved))} of them")
        emit(guild, entry)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if before.channel == after.channel:
            return
        guild = member.guild
        if cache.log_channel(guild.id, Log.VOICE) is None:
            return
        by = None
        if before.channel and after.channel:
            by = await self._waited_actor(guild, ("move", guild.id, after.channel.id))
        elif before.channel:
            by = await self._waited_actor(guild, ("disconnect", guild.id))
        place = (after.channel or before.channel).id
        if by:
            title = "Moved" if after.channel else "Disconnected"
            entry = Entry("voice_moderation", f"Member {title}", "orange", channel_id=place, member=member)
        elif after.channel and not before.channel:
            entry = Entry("voice_activity", "Voice Joined", "green", channel_id=place, member=member, bot=member.bot)
        elif before.channel and not after.channel:
            entry = Entry("voice_activity", "Voice Left", "red", channel_id=place, member=member, bot=member.bot)
        else:
            entry = Entry("voice_activity", "Voice Switched", channel_id=place, member=member, bot=member.bot)
        entry.add("user", "Member", person(member))
        if before.channel and after.channel:
            entry.add("voice_red", "From", before.channel.mention).add("voice", "To", after.channel.mention)
        else:
            entry.add("voice", "Channel", (after.channel or before.channel).mention)
        emit(guild, entry.add("owner", "Moderator", by))

    @commands.Cog.listener()
    async def on_auto_moderation_action_execution(self, payload: discord.AutoModActionExecutionEvent):
        """Discord sends one event per action of a rule, so the actions of one hit are gathered into one log."""
        guild = payload.guild or self.client.get_guild(payload.guild_id)
        if guild is None:
            return
        key = (guild.id, payload.user_id, payload.rule_id, payload.content)
        action = payload.action.type.name.replace("_", " ").capitalize()
        if key in self._automod:
            self._automod[key][1].append(action)
            return
        user = payload.member or self.client.get_user(payload.user_id)
        rule = await self._rule_name(guild, payload.rule_id)
        entry = Entry("discord_rules", "Discord Rule Triggered", "red", channel_id=payload.channel_id)
        entry.add("user", "Member", person(user) if user else person_id(payload.user_id))
        entry.add("id", "ID", f"`{payload.user_id}`").add("mod", "Rule", rule)
        entry.add("channel", "Channel", f"<#{payload.channel_id}>" if payload.channel_id else None)
        entry.add("keyboard", "Matched", f"`{payload.matched_keyword}`" if payload.matched_keyword else None)
        self._automod[key] = (entry, [action])
        await asyncio.sleep(1)
        entry, actions = self._automod.pop(key)
        entry.add("bin", "Action", ", ".join(dict.fromkeys(actions)))
        entry.add("note", "Content", f"\n{clip(payload.content, 512)}" if payload.content else None)
        emit(guild, entry)

    async def _rule_name(self, guild: discord.Guild, rule_id: int) -> str:
        if name := self._rule_names.get(rule_id):
            return name
        try:
            rule = await guild.fetch_auto_moderation_rule(rule_id)
        except discord.HTTPException:
            return f"`{rule_id}`"
        if len(self._rule_names) > 1000:
            self._rule_names.clear()
        self._rule_names[rule_id] = rule.name
        return rule.name

    @commands.Cog.listener()
    async def on_auto_moderation_rule_update(self, rule: discord.AutoModRule):
        self._rule_names.pop(rule.id, None)

    @commands.Cog.listener()
    async def on_auto_moderation_rule_delete(self, rule: discord.AutoModRule):
        self._rule_names.pop(rule.id, None)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        webhook.invalidate(channel.id)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        webhook.invalidate(thread.id)

    @commands.Cog.listener()
    async def on_log_channels_update(self, guild_id: int):
        if guild := self.client.get_guild(guild_id):
            memory.prune(guild)


def setup(client: Client):
    client.add_cog(Logs(client))
