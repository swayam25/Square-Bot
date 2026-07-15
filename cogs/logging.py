import discord
from core import Client
from core.view import DesignerView
from db.funcs.logs import fetch_log_channel, remove_log_channel
from discord import ui
from discord.ext import commands
from utils import config, logger, webhook
from utils.emoji import emoji
from utils.helpers import create_dc_msgs_file


def clip(text: str, limit: int = 1024) -> str:
    """Clips text to the given length so log containers stay within limits."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def log_view(
    title: str,
    body: str,
    *,
    color: int | None = None,
    thumbnail: str | None = None,
    extra: list[ui.Item] | None = None,
    buttons: list[ui.Button] | None = None,
) -> DesignerView:
    """
    Builds a simple log view: a container with a title & body, optionally
    with a thumbnail, extra items & an action row of buttons.
    """
    header: list[ui.Item] = [ui.TextDisplay(f"## {title}"), ui.TextDisplay(body)]
    items: list[ui.Item] = [ui.Section(*header, accessory=ui.Thumbnail(thumbnail))] if thumbnail else header
    if extra:
        items += extra
    view = DesignerView(ui.Container(*items, color=color))
    if buttons:
        view.add_item(ui.ActionRow(*buttons))
    return view


class Logging(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    async def send_log(
        self,
        guild: discord.Guild,
        log_type: logger.LogType,
        view: DesignerView,
        *,
        file: discord.File | None = None,
    ) -> None:
        """Sends a log view to the guild's configured channel for the log type, if set."""
        channel_id = await fetch_log_channel(guild.id, log_type.key)
        if channel_id is None:
            return
        channel = guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await guild.fetch_channel(channel_id)
            except discord.HTTPException:
                await remove_log_channel(guild.id, log_type.key)  # Channel is gone, drop the setting
                return
        await logger.log(self.client, channel, log_type, view, file=file)

    # ── Members ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        view = log_view(
            "Member Joined",
            f"{emoji.user} **Name**: {member.mention} (`{member.name}`)\n"
            f"{emoji.duration} **Account Created**: {discord.utils.format_dt(member.created_at, 'R')}\n"
            f"{emoji.members} **Member Count**: {member.guild.member_count}",
            thumbnail=member.display_avatar.url,
        )
        await self.send_log(member.guild, logger.LogType.MEMBERS, view)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        roles = [role.mention for role in member.roles if role != member.guild.default_role]
        view = log_view(
            "Member Left",
            f"{emoji.user_red} **Name**: {member.mention} (`{member.name}`)\n"
            f"{emoji.duration_red} **Account Created**: {discord.utils.format_dt(member.created_at, 'R')}\n"
            + (
                f"{emoji.add_red} **Server Joined**: {discord.utils.format_dt(member.joined_at, 'R')}\n"
                if member.joined_at
                else ""
            )
            + (f"{emoji.role_red} **Roles**: {clip(', '.join(roles), 512)}" if roles else ""),
            color=config.color.red,
            thumbnail=member.display_avatar.url,
        )
        await self.send_log(member.guild, logger.LogType.MEMBERS, view)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Nickname
        if before.nick != after.nick:
            view = log_view(
                "Nickname Changed",
                f"{emoji.user} **Name**: {after.mention} (`{after.name}`)\n"
                f"{emoji.description_red} **Before**: `{before.nick or before.name}`\n"
                f"{emoji.description} **After**: `{after.nick or after.name}`",
                thumbnail=after.display_avatar.url,
            )
            await self.send_log(after.guild, logger.LogType.MEMBERS, view)

        # Roles
        if before.roles != after.roles:
            added = [role.mention for role in after.roles if role not in before.roles]
            removed = [role.mention for role in before.roles if role not in after.roles]
            view = log_view(
                "Member Roles Updated",
                f"{emoji.user} **Name**: {after.mention} (`{after.name}`)\n"
                + (f"{emoji.add} **Added**: {clip(', '.join(added), 512)}\n" if added else "")
                + (f"{emoji.remove} **Removed**: {clip(', '.join(removed), 512)}" if removed else ""),
                thumbnail=after.display_avatar.url,
            )
            await self.send_log(after.guild, logger.LogType.MEMBERS, view)

        # Timeout
        if before.communication_disabled_until != after.communication_disabled_until:
            if after.communication_disabled_until is not None:
                view = log_view(
                    "Member Timed Out",
                    f"{emoji.user_red} **Name**: {after.mention} (`{after.name}`)\n"
                    f"{emoji.duration_red} **Until**: {discord.utils.format_dt(after.communication_disabled_until, 'R')}",
                    color=config.color.red,
                    thumbnail=after.display_avatar.url,
                )
            else:
                view = log_view(
                    "Timeout Removed",
                    f"{emoji.user} **Name**: {after.mention} (`{after.name}`)",
                    thumbnail=after.display_avatar.url,
                )
            await self.send_log(after.guild, logger.LogType.MODERATION, view)

    # ── Moderation ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member):
        joined_at = getattr(user, "joined_at", None)
        view = log_view(
            "Member Banned",
            f"{emoji.user_red} **Name**: {user.mention} (`{user.name}`)\n"
            f"{emoji.duration_red} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}"
            + (f"\n{emoji.add_red} **Server Joined**: {discord.utils.format_dt(joined_at, 'R')}" if joined_at else ""),
            color=config.color.red,
            thumbnail=user.display_avatar.url,
        )
        await self.send_log(guild, logger.LogType.MODERATION, view)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        view = log_view(
            "Member Unbanned",
            f"{emoji.user} **Name**: {user.mention} (`{user.name}`)\n"
            f"{emoji.duration} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}",
            thumbnail=user.display_avatar.url,
        )
        await self.send_log(guild, logger.LogType.MODERATION, view)

    # ── Messages ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        extra: list[ui.Item] = []
        if before.attachments and not after.attachments:
            extra.append(
                ui.TextDisplay(
                    f"### Removed Attachment{'s' if len(before.attachments) > 1 else ''} [`{len(before.attachments)}`]"
                )
            )
            extra.append(ui.MediaGallery(*[discord.MediaGalleryItem(url=media.url) for media in before.attachments]))
        view = log_view(
            "Message Edited",
            f"{emoji.owner} **Author**: {before.author.mention}\n"
            f"{emoji.channel} **Channel**: {before.channel.mention}\n"
            f"{emoji.description_red} **Before**:\n{clip(before.content)}\n"
            f"{emoji.description} **After**:\n{clip(after.content)}",
            extra=extra,
            buttons=[ui.Button(label="Jump to Message", url=after.jump_url, style=discord.ButtonStyle.link)],
        )
        await self.send_log(before.guild, logger.LogType.MESSAGES, view)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.guild_id is None:
            return
        guild = self.client.get_guild(payload.guild_id)
        if guild is None:
            return
        msg = payload.cached_message
        if msg is None:  # Uncached: only IDs are known, content is unrecoverable
            view = log_view(
                "Message Deleted",
                f"{emoji.channel_red} **Channel**: <#{payload.channel_id}>\n"
                f"{emoji.duration_red} **Sent**: "
                f"{discord.utils.format_dt(discord.utils.snowflake_time(payload.message_id), 'R')}\n"
                f"{emoji.description_red} **Message**: "
                f"[`{payload.message_id}`](https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id})"
                f" (*unknown content*)",
                color=config.color.red,
            )
            await self.send_log(guild, logger.LogType.MESSAGES, view)
            return
        if msg.author.bot:
            return
        extra: list[ui.Item] = []
        if msg.stickers:
            extra.append(
                ui.TextDisplay(f"### Deleted Sticker{'s' if len(msg.stickers) > 1 else ''} [`{len(msg.stickers)}`]")
            )
            extra.append(ui.MediaGallery(*[discord.MediaGalleryItem(url=sticker.url) for sticker in msg.stickers]))
        if msg.attachments:
            extra.append(
                ui.TextDisplay(
                    f"### Deleted Attachment{'s' if len(msg.attachments) > 1 else ''} [`{len(msg.attachments)}`]"
                )
            )
            extra.append(ui.MediaGallery(*[discord.MediaGalleryItem(url=media.url) for media in msg.attachments]))
        view = log_view(
            "Message Deleted",
            f"{emoji.owner_red} **Author**: {msg.author.mention}\n"
            f"{emoji.channel_red} **Channel**: {msg.channel.mention} (`{msg.channel.name}`)\n"
            f"{emoji.duration_red} **Sent**: {discord.utils.format_dt(msg.created_at, 'R')}"
            + (f"\n{emoji.description_red} **Message**:\n{clip(msg.content)}" if msg.content else ""),
            color=config.color.red,
            extra=extra,
        )
        await self.send_log(guild, logger.LogType.MESSAGES, view)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if payload.guild_id is None:
            return
        guild = self.client.get_guild(payload.guild_id)
        if guild is None:
            return
        # Only cached messages still carry their content, the rest are logged by ID
        msgs = list(payload.cached_messages)
        uncached_ids = set(payload.message_ids) - {msg.id for msg in msgs}
        view = log_view(
            "Bulk Message Deleted",
            f"{emoji.channel_red} **Channel**: <#{payload.channel_id}>\n"
            f"{emoji.description_red} **Messages Deleted**: {len(payload.message_ids)}",
            color=config.color.red,
        )
        await self.send_log(
            guild,
            logger.LogType.MESSAGES,
            view,
            file=create_dc_msgs_file(msgs, uncached_ids, guild_id=payload.guild_id, channel_id=payload.channel_id),
        )

    # ── Channel & Threads ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        view = log_view(
            "Channel Created",
            f"{emoji.channel} **Channel**: {channel.mention} (`{channel.name}`)\n"
            + (f"{emoji.category} **Category**: {channel.category.name}\n" if channel.category else "")
            + f"{emoji.description} **Type**: {str(channel.type).replace('_', ' ').title()}",
        )
        await self.send_log(channel.guild, logger.LogType.CHANNELS, view)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        webhook.invalidate(channel.id)  # Drop the cached webhook of the deleted channel
        view = log_view(
            "Channel Deleted",
            f"{emoji.channel_red} **Channel**: `{channel.name}`\n"
            + (f"{emoji.category_red} **Category**: {channel.category.name}\n" if channel.category else "")
            + f"{emoji.description_red} **Type**: {str(channel.type).replace('_', ' ').title()}",
            color=config.color.red,
        )
        await self.send_log(channel.guild, logger.LogType.CHANNELS, view)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if before.name == after.name:  # Only renames are logged to avoid permission sync noise
            return
        view = log_view(
            "Channel Renamed",
            f"{emoji.channel} **Channel**: {after.mention}\n"
            f"{emoji.description_red} **Before**: `{before.name}`\n"
            f"{emoji.description} **After**: `{after.name}`",
        )
        await self.send_log(after.guild, logger.LogType.CHANNELS, view)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        view = log_view(
            "Thread Created",
            f"{emoji.channel} **Thread**: {thread.mention} (`{thread.name}`)\n"
            f"{emoji.channel} **Parent**: {thread.parent.mention if thread.parent else 'Unknown'}\n"
            f"{emoji.owner} **Owner**: <@{thread.owner_id}>",
        )
        await self.send_log(thread.guild, logger.LogType.CHANNELS, view)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        webhook.invalidate(thread.id)
        view = log_view(
            "Thread Deleted",
            f"{emoji.channel_red} **Thread**: `{thread.name}`\n"
            f"{emoji.channel_red} **Parent**: {thread.parent.mention if thread.parent else 'Unknown'}",
            color=config.color.red,
        )
        await self.send_log(thread.guild, logger.LogType.CHANNELS, view)

    # ── Roles ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        view = log_view(
            "Role Created",
            f"{emoji.role} **Role**: {role.mention} (`{role.name}`)",
        )
        await self.send_log(role.guild, logger.LogType.ROLES, view)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        view = log_view(
            "Role Deleted",
            f"{emoji.role_red} **Role**: `{role.name}`\n{emoji.members_red} **Members**: {len(role.members)}",
            color=config.color.red,
        )
        await self.send_log(role.guild, logger.LogType.ROLES, view)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        lines = []
        if before.name != after.name:
            lines.append(f"{emoji.description} **Name**: `{before.name}` → `{after.name}`")
        if before.colors.primary != after.colors.primary:
            lines.append(f"{emoji.img} **Color**: `{before.color}` → `{after.color}`")
        if before.permissions != after.permissions:
            lines.append(f"{emoji.perms} **Permissions**: Updated")
        if not lines:  # Skips position moves & other noise
            return
        view = log_view("Role Updated", f"{emoji.role} **Role**: {after.mention}\n" + "\n".join(lines))
        await self.send_log(after.guild, logger.LogType.ROLES, view)

    # ── Guild ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        lines = []
        if before.name != after.name:
            lines.append(f"{emoji.description} **Name**: `{before.name}` → `{after.name}`")
        if before.owner_id != after.owner_id:
            lines.append(f"{emoji.crown} **Owner**: <@{before.owner_id}> → <@{after.owner_id}>")
        if before.icon != after.icon:
            lines.append(f"{emoji.img} **Icon**: Updated")
        if not lines:
            return
        view = log_view("Server Updated", "\n".join(lines), thumbnail=after.icon.url if after.icon else None)
        await self.send_log(after, logger.LogType.SERVER, view)

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self, guild: discord.Guild, before: list[discord.Emoji], after: list[discord.Emoji]
    ):
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]
        lines = []
        if added:
            lines.append(f"{emoji.add} **Added**: {' '.join(str(e) for e in added)}")
        if removed:
            lines.append(f"{emoji.remove} **Removed**: {', '.join(f'`{e.name}`' for e in removed)}")
        if not lines:
            return
        view = log_view("Emojis Updated", clip("\n".join(lines)))
        await self.send_log(guild, logger.LogType.SERVER, view)

    @commands.Cog.listener()
    async def on_guild_stickers_update(
        self, guild: discord.Guild, before: list[discord.GuildSticker], after: list[discord.GuildSticker]
    ):
        added = [s for s in after if s not in before]
        removed = [s for s in before if s not in after]
        lines = []
        if added:
            lines.append(f"{emoji.add} **Added**: {', '.join(f'`{s.name}`' for s in added)}")
        if removed:
            lines.append(f"{emoji.remove} **Removed**: {', '.join(f'`{s.name}`' for s in removed)}")
        if not lines:
            return
        view = log_view("Stickers Updated", clip("\n".join(lines)))
        await self.send_log(guild, logger.LogType.SERVER, view)

    # ── Voice ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if before.channel == after.channel:  # Mute / deafen & other state changes are skipped
            return
        if before.channel is None:
            view = log_view(
                "Voice Joined",
                f"{emoji.user} **Name**: {member.mention}\n{emoji.voice} **Channel**: {after.channel.mention}",
            )
        elif after.channel is None:
            view = log_view(
                "Voice Left",
                f"{emoji.user_red} **Name**: {member.mention}\n{emoji.voice_red} **Channel**: {before.channel.mention}",
                color=config.color.red,
            )
        else:
            view = log_view(
                "Voice Moved",
                f"{emoji.user} **Name**: {member.mention}\n"
                f"{emoji.voice_red} **From**: {before.channel.mention}\n"
                f"{emoji.voice} **To**: {after.channel.mention}",
            )
        await self.send_log(member.guild, logger.LogType.VOICE, view)

    # ── Invites ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if invite.guild is None:
            return
        guild = self.client.get_guild(invite.guild.id)
        if guild is None:
            return
        view = log_view(
            "Invite Created",
            f"{emoji.invite} **Code**: `{invite.code}`\n"
            f"{emoji.user} **Created By**: {invite.inviter.mention if invite.inviter else 'Unknown'}\n"
            f"{emoji.channel} **Channel**: <#{invite.channel.id}>\n"
            f"{emoji.members} **Max Uses**: {invite.max_uses or 'Unlimited'}\n"
            f"{emoji.duration} **Expires**: "
            + (discord.utils.format_dt(invite.expires_at, "R") if invite.expires_at else "Never"),
        )
        await self.send_log(guild, logger.LogType.INVITES, view)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if invite.guild is None:
            return
        guild = self.client.get_guild(invite.guild.id)
        if guild is None:
            return
        view = log_view(
            "Invite Deleted",
            f"{emoji.invite_red} **Code**: `{invite.code}`\n{emoji.channel_red} **Channel**: <#{invite.channel.id}>",
            color=config.color.red,
        )
        await self.send_log(guild, logger.LogType.INVITES, view)

    # ── Automod ──────────────────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_auto_moderation_action_execution(self, payload: discord.AutoModActionExecutionEvent):
        guild = payload.guild or self.client.get_guild(payload.guild_id)
        if guild is None:
            return
        view = log_view(
            "AutoMod Action",
            f"{emoji.user_red} **Member**: <@{payload.user_id}>\n"
            f"{emoji.verification} **Action**: {str(payload.action.type.name).replace('_', ' ').title()}\n"
            f"{emoji.description_red} **Trigger**: {str(payload.rule_trigger_type.name).replace('_', ' ').title()}\n"
            + (f"{emoji.channel_red} **Channel**: <#{payload.channel_id}>\n" if payload.channel_id else "")
            + (f"{emoji.keyboard_red} **Matched**: `{payload.matched_keyword}`\n" if payload.matched_keyword else "")
            + (
                f"{emoji.description_red} **Content**:\n```\n{clip(payload.content, 512)}\n```"
                if payload.content
                else ""
            ),
            color=config.color.red,
        )
        await self.send_log(guild, logger.LogType.AUTOMOD, view)


def setup(client: Client):
    client.add_cog(Logging(client))
