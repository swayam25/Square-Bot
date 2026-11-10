import discord
from discord import ui
from square.core.settings import SettingsPage, channel_picker, mention_or_off, modal, pencil, role_picker, row, title
from square.db import cache
from square.settings import general
from square.settings.errors import SettingError
from square.utils.emoji import emoji


class GeneralPage(SettingsPage):
    name = "General"
    emoji = emoji.settings
    description = "Auto role and media-only channel"
    order = 1

    def _autorole(self) -> discord.Role | None:
        role_id = cache.get(self.guild.id).autorole
        return self.guild.get_role(role_id) if role_id else None

    def _media_only(self) -> discord.abc.GuildChannel | None:
        channel_id = cache.get(self.guild.id).media_only_channel_id
        return self.guild.get_channel(channel_id) if channel_id else None

    def summary(self) -> list[str]:
        return [
            f"{emoji.role} **Auto Role**: {mention_or_off(self._autorole())}",
            f"{emoji.img} **Media Only**: {mention_or_off(self._media_only())}",
        ]

    def build(self) -> list[ui.Item]:
        lines = self.summary()
        return [title("General"), row(lines[0], pencil(self._edit_autorole)), row(lines[1], pencil(self._edit_media))]

    async def _edit_autorole(self, interaction: discord.Interaction) -> None:
        picker = role_picker([role] if (role := self._autorole()) else [])

        async def submit(submitted: discord.Interaction) -> None:
            picked = picker.values or []
            role = picked[0] if picked and isinstance(picked[0], discord.Role) else None
            try:
                await general.set_autorole(self.guild, role)
            except SettingError as exc:
                await self.panel.error(submitted, str(exc))
                return
            await self.panel.refresh(submitted)

        label = ui.Label("Role", picker, description="Given to every member who joins. Leave empty to turn it off.")
        await interaction.response.send_modal(modal("Auto role", label, on_submit=submit))

    async def _edit_media(self, interaction: discord.Interaction) -> None:
        picker = channel_picker([discord.ChannelType.text], self._media_only())

        async def submit(submitted: discord.Interaction) -> None:
            picked = picker.values or []
            channel = picked[0] if picked and isinstance(picked[0], discord.TextChannel) else None
            try:
                await general.set_media_only(self.guild, channel)
            except SettingError as exc:
                await self.panel.error(submitted, str(exc))
                return
            await self.panel.refresh(submitted)

        label = ui.Label("Channel", picker, description="Only media and links may be posted here. Empty turns it off.")
        await interaction.response.send_modal(modal("Media-only channel", label, on_submit=submit))

    async def reset(self, interaction: discord.Interaction) -> None:
        await general.reset(self.guild)
