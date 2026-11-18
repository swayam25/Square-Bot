import discord
from discord.ext import commands
from square.cogs.automod import rules
from square.cogs.automod.rules import LABELS, NOTICES
from square.cogs.logging import clip, log_view
from square.cogs.moderation.warnings import warn
from square.core import Client
from square.core.cog import Cog
from square.core.view import error_view
from square.db.funcs import automod as automod_db
from square.db.schema import AutomodRuleTable
from square.utils import config, server_log
from square.utils.emoji import emoji
from square.utils.helpers import plural

_CHECKED = (discord.MessageType.default, discord.MessageType.reply)
_TEXT_KINDS = ("invites", "caps", "emojis")
_ORDER = ("media", "invites", "duplicates", "flood", "caps", "emojis")


def _watched(message: discord.Message) -> bool:
    return (
        message.guild is not None
        and isinstance(message.author, discord.Member)
        and not message.author.bot
        and message.webhook_id is None
        and message.type in _CHECKED
        and not message.author.guild_permissions.manage_messages
    )


class AutoMod(Cog):
    def __init__(self, client: Client):
        self.client = client
        self.recent = rules.Recent()

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
            case "flood":
                if self.recent.flood(sent, rule.amount or 5, rule.seconds or 5):
                    return f"Over {rule.amount} {plural(rule.amount, 'message')} in {rule.seconds}s"
            case "duplicates":
                if self.recent.duplicates(sent, rule.amount or 3, rule.seconds or 60):
                    return f"Same message over {rule.amount} {plural(rule.amount, 'time')} in {rule.seconds}s"
            case _:
                return await rules.content_hit(self.client, message.guild, rule, message.content)
        return None

    async def _check(self, message: discord.Message, kinds: tuple[str, ...]) -> None:
        active = self._active(message, kinds)
        if not active:
            return
        sent = None
        if any(rule.kind in ("flood", "duplicates") for rule in active):
            sent = self.recent.add(message.guild.id, message.author.id, message.content)
        for rule in active:
            if detail := await self._hit(message, rule, sent):
                await self._act(message, rule, detail)
                return

    async def _act(self, message: discord.Message, rule: AutomodRuleTable, detail: str) -> None:
        guild, member = message.guild, message.author
        deleted = False
        if rule.delete_message:
            try:
                await message.delete(reason=f"AutoMod: {LABELS[rule.kind]}")
                deleted = True
            except discord.Forbidden, discord.NotFound:
                pass
        # Flood and duplicates fire on every message of a burst: the rest are only deleted, never warned or logged
        if rule.kind in ("flood", "duplicates") and not self.recent.once(
            guild.id, member.id, rule.kind, rule.seconds or 60
        ):
            return
        warned = await warn(self.client, guild, member, f"AutoMod: {LABELS[rule.kind]}", None) if rule.warn else None
        if rule.notify and (deleted or warned):
            note = f"{member.mention} {NOTICES[rule.kind]}" + (" You got a warning." if warned else "")
            try:
                await message.channel.send(
                    view=error_view(note), allowed_mentions=discord.AllowedMentions(users=[member]), delete_after=10
                )
            except discord.Forbidden, discord.HTTPException:
                pass
        actions = [label for label, done in (("Deleted", deleted), ("Warned", warned)) if done]
        await server_log.send(
            self.client,
            guild,
            server_log.LogType.AUTOMOD,
            log_view(
                "Square Rule Triggered",
                f"{emoji.user_red} **Member**: {member.mention} (`{member.name}`)\n"
                f"{emoji.id_red} **ID**: `{member.id}`\n"
                f"{emoji.mod_red} **Rule**: {LABELS[rule.kind]}\n"
                f"{emoji.description_red} **Why**: {detail}\n"
                f"{emoji.channel_red} **Channel**: {message.channel.mention}\n"
                f"{emoji.bin_red} **Action**: {', '.join(actions) or 'Only logged'}"
                + (f"\n{emoji.description_red} **Content**:\n{clip(message.content, 512)}" if message.content else ""),
                color=config.color.red,
            ),
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if _watched(message):
            await self._check(message, _ORDER)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content and _watched(after):
            await self._check(after, _TEXT_KINDS)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        self.recent.forget(guild.id)


def setup(client: Client):
    client.add_cog(AutoMod(client))
