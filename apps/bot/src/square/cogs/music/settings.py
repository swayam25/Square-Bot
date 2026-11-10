import discord
from discord import ui
from square.core.settings import (
    SettingsPage,
    button,
    channel_picker,
    mention_or_off,
    modal,
    pencil,
    role_picker,
    row,
    title,
    toggle,
)
from square.core.view import show_loading
from square.db import cache
from square.db.funcs.dj import remove_dj, set_dj_mode, set_dj_roles
from square.music import request, stay
from square.music.core import can_play_in, get_player
from square.music.dj import MAX_ROLES
from square.music.player import release_guild, render_player, stop_player
from square.utils.emoji import emoji


class MusicPage(SettingsPage):
    name = "Music"
    emoji = emoji.music
    description = "Request channel, 24/7 and DJ mode"
    order = 3

    def _request_channel(self) -> discord.abc.GuildChannel | None:
        channel_id = request.channel_id(self.guild.id)
        return self.guild.get_channel(channel_id) if channel_id else None

    def _stay_channel(self) -> discord.abc.GuildChannel | None:
        channel_id = stay.channel_id(self.guild.id)
        return self.guild.get_channel(channel_id) if channel_id else None

    def _dj_roles(self) -> list[discord.Role]:
        # Resolved against live roles, so a deleted role's leftover row never shows up
        return [role for role_id in cache.get(self.guild.id).dj_roles if (role := self.guild.get_role(role_id))]

    def summary(self) -> list[str]:
        dj_mode = cache.get(self.guild.id).dj_mode
        return [
            f"{emoji.music} **Request Channel**: {mention_or_off(self._request_channel())}",
            f"{emoji.voice} **24/7 Channel**: {mention_or_off(self._stay_channel())}",
            f"{emoji.dj} **DJ Mode**: {emoji.on if dj_mode else emoji.off}",
        ]

    def build(self) -> list[ui.Item]:
        settings = cache.get(self.guild.id)
        lines = self.summary()
        if self._request_channel():
            request_btn = self.panel.confirm_button("music-request", "Remove", self._remove_request)
        else:
            request_btn = button(self._create_request, label="Create", emoji=emoji.add_white)
        roles = ", ".join(role.mention for role in self._dj_roles()) or emoji.off
        return [
            title("Music"),
            row(lines[0], request_btn),
            row(lines[1], pencil(self._edit_stay)),
            row(f"{emoji.dj} **DJ Mode**", toggle(settings.dj_mode, self._toggle_dj)),
            row(f"{emoji.role} **DJ Roles**: {roles}", pencil(self._edit_dj_roles)),
        ]

    async def _create_request(self, interaction: discord.Interaction) -> None:
        """Creates a channel where anything typed is queued, with the player pinned."""
        if not self.guild.me.guild_permissions.manage_channels:
            await self.panel.error(interaction, "I need the `Manage Channels` permission to create the channel.")
            return
        if not await show_loading(self.panel, interaction, "Creating..."):
            return
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                add_reactions=False,
                attach_files=False,
                embed_links=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False,
            ),
            self.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True,
                embed_links=True,
                attach_files=True,
                add_reactions=True,
            ),
        }
        try:
            channel = await self.guild.create_text_channel(
                "music-requests", overwrites=overwrites, topic="Send a track name or a link here to queue it."
            )
        except discord.HTTPException as exc:
            await self.panel.error(interaction, f"I couldn't create the music channel: {exc.text or exc}")
            await self.panel.refresh(interaction)
            return
        await request.bind(self.guild.id, channel.id)
        request.prime(self.panel.bot, self.guild.id)
        await render_player(self.panel.bot, self.guild.id, wait=True)
        await self.panel.refresh(interaction)

    async def _remove_request(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if note := await self._clear_request_channel():
            await self.panel.error(interaction, note)
        await self.panel.refresh(interaction)

    async def _clear_request_channel(self) -> str | None:
        """
        Unbinds the request channel and deletes it, card and all.

        The bot created the channel, so it's throwing away its own: everything in there is either the card or a
        request the bot already cleared. Returns a note when the channel had to be left behind.
        """
        channel_id = request.channel_id(self.guild.id)
        if channel_id is None:
            return None
        # Unbind first, so deleting the channel doesn't race the listener that watches for it
        await request.unbind(self.guild.id)
        note = None
        if (channel := self.guild.get_channel(channel_id)) is not None:
            try:
                await channel.delete(reason=f"Music channel removed by {self.panel.author}")
            except discord.HTTPException:
                note = f"I couldn't delete {channel.mention}, so it's yours to remove."
        await release_guild(self.panel.bot, self.guild.id)
        return note

    async def _edit_stay(self, interaction: discord.Interaction) -> None:
        picker = channel_picker([discord.ChannelType.voice, discord.ChannelType.stage_voice], self._stay_channel())
        pressed = (interaction.data or {}).get("custom_id")

        async def submit(submitted: discord.Interaction) -> None:
            picked = picker.values or []
            channel = (
                picked[0] if picked and isinstance(picked[0], discord.VoiceChannel | discord.StageChannel) else None
            )
            if channel is not None and not can_play_in(channel):
                await self.panel.error(submitted, f"I need the `Connect` and `Speak` permissions in {channel.mention}.")
                return
            if not await show_loading(self.panel, submitted, "Saving...", custom_id=pressed):
                return
            if channel is None:
                await self._clear_stay_channel()
            else:
                await stay.bind(self.guild.id, channel.id)
                try:
                    await stay.join(self.panel.bot, self.guild.id)
                except Exception:
                    stay.schedule_rejoin(self.panel.bot, self.guild.id)  # Keeps trying in the background
            await self.panel.refresh(submitted)

        label = ui.Label("Voice channel", picker, description="I stay here around the clock. Empty turns 24/7 off.")
        await interaction.response.send_modal(modal("24/7 channel", label, on_submit=submit))

    async def _clear_stay_channel(self) -> None:
        """
        Drops the 24/7 channel, so the bot leaves once it is no longer needed there.

        A session still playing is left to finish and is then torn down like any other.
        An idle bot was only there because of 24/7, so it leaves right away.
        """
        if stay.channel_id(self.guild.id) is None:
            return
        await stay.unbind(self.guild.id)
        if (player := get_player(self.panel.bot, self.guild.id)) is None:
            return
        if player.current:
            # Re-arms sonolink's disconnect timer, which 24/7 was holding off
            player.cancel_empty_timer()
            player._check_inactivity()
        else:
            await stop_player(player, self.guild, force=True)

    async def _toggle_dj(self, interaction: discord.Interaction) -> None:
        await set_dj_mode(self.guild.id, not cache.get(self.guild.id).dj_mode)
        await self.panel.refresh(interaction)

    async def _edit_dj_roles(self, interaction: discord.Interaction) -> None:
        picker = role_picker(self._dj_roles(), max_values=MAX_ROLES)

        async def submit(submitted: discord.Interaction) -> None:
            role_ids = [role.id for role in picker.values or [] if isinstance(role, discord.Role)]
            await set_dj_roles(self.guild.id, role_ids)
            # Picking the first role is the whole point, so don't make enabling DJ mode a second step
            if role_ids and not cache.get(self.guild.id).dj_mode:
                await set_dj_mode(self.guild.id, True)
            await self.panel.refresh(submitted)

        label = ui.Label("Roles", picker, description=f"Up to {MAX_ROLES}. Members with Manage Server are always DJs.")
        await interaction.response.send_modal(modal("DJ roles", label, on_submit=submit))

    async def reset(self, interaction: discord.Interaction) -> None:
        if note := await self._clear_request_channel():
            await self.panel.error(interaction, note)
        await self._clear_stay_channel()
        await remove_dj(self.guild.id)
