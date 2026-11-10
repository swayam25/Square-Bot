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
from square.music.dj import MAX_ROLES
from square.settings import music
from square.settings.errors import SettingError
from square.utils.emoji import emoji


class MusicPage(SettingsPage):
    name = "Music"
    emoji = emoji.music
    description = "Request channel, 24/7 and DJ mode"
    order = 3

    def summary(self) -> list[str]:
        dj_mode = cache.get(self.guild.id).dj_mode
        return [
            f"{emoji.music} **Request Channel**: {mention_or_off(music.request_channel(self.guild))}",
            f"{emoji.voice} **24/7 Channel**: {mention_or_off(music.stay_channel(self.guild))}",
            f"{emoji.dj} **DJ Mode**: {emoji.on if dj_mode else emoji.off}",
        ]

    def build(self) -> list[ui.Item]:
        settings = cache.get(self.guild.id)
        lines = self.summary()
        if music.request_channel(self.guild):
            request_btn = self.panel.confirm_button("music-request", "Remove", self._remove_request)
        else:
            request_btn = button(self._create_request, label="Create", emoji=emoji.add_white)
        roles = ", ".join(role.mention for role in music.dj_roles(self.guild)) or emoji.off
        return [
            title("Music"),
            row(lines[0], request_btn),
            row(lines[1], pencil(self._edit_stay)),
            row(f"{emoji.dj} **DJ Mode**", toggle(settings.dj_mode, self._toggle_dj)),
            row(f"{emoji.role} **DJ Roles**: {roles}", pencil(self._edit_dj_roles)),
        ]

    async def _create_request(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self.panel, interaction, "Creating..."):
            return
        try:
            await music.create_request_channel(self.panel.bot, self.guild)
        except SettingError as exc:
            await self.panel.error(interaction, str(exc))
        await self.panel.refresh(interaction)

    async def _remove_request(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if note := await music.remove_request_channel(self.panel.bot, self.guild, self.panel.author):
            await self.panel.error(interaction, note)
        await self.panel.refresh(interaction)

    async def _edit_stay(self, interaction: discord.Interaction) -> None:
        picker = channel_picker(
            [discord.ChannelType.voice, discord.ChannelType.stage_voice], music.stay_channel(self.guild)
        )
        pressed = (interaction.data or {}).get("custom_id")

        async def submit(submitted: discord.Interaction) -> None:
            picked = picker.values or []
            channel = (
                picked[0] if picked and isinstance(picked[0], discord.VoiceChannel | discord.StageChannel) else None
            )
            if not await show_loading(self.panel, submitted, "Saving...", custom_id=pressed):
                return
            try:
                await music.set_stay_channel(self.panel.bot, self.guild, channel)
            except SettingError as exc:
                await self.panel.error(submitted, str(exc))
            await self.panel.refresh(submitted)

        label = ui.Label("Voice channel", picker, description="I stay here around the clock. Empty turns 24/7 off.")
        await interaction.response.send_modal(modal("24/7 channel", label, on_submit=submit))

    async def _toggle_dj(self, interaction: discord.Interaction) -> None:
        await music.set_dj_mode(self.guild, not cache.get(self.guild.id).dj_mode)
        await self.panel.refresh(interaction)

    async def _edit_dj_roles(self, interaction: discord.Interaction) -> None:
        picker = role_picker(music.dj_roles(self.guild), max_values=MAX_ROLES)

        async def submit(submitted: discord.Interaction) -> None:
            roles = [role for role in picker.values or [] if isinstance(role, discord.Role)]
            try:
                await music.set_dj_roles(self.guild, roles)
            except SettingError as exc:
                await self.panel.error(submitted, str(exc))
                return
            await self.panel.refresh(submitted)

        label = ui.Label("Roles", picker, description=f"Up to {MAX_ROLES}. Members with Manage Server are always DJs.")
        await interaction.response.send_modal(modal("DJ roles", label, on_submit=submit))

    async def reset(self, interaction: discord.Interaction) -> None:
        if note := await music.reset(self.panel.bot, self.guild, self.panel.author):
            await self.panel.error(interaction, note)
