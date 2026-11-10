import discord
from discord import ui
from square.core.settings import SettingsPage, modal, pencil, row, title, toggle
from square.db import cache
from square.settings import invites
from square.settings.errors import SettingError
from square.utils.emoji import emoji


class InvitesPage(SettingsPage):
    name = "Invites"
    emoji = emoji.invite
    description = "Invite tracker and fake accounts"
    order = 5

    def summary(self) -> list[str]:
        settings = cache.get(self.guild.id)
        return [
            f"{emoji.invite} **Invite Tracker**: {emoji.on if settings.invite_tracker else emoji.off}",
            f"{emoji.fake} **Fake Account Age**: {settings.invite_fake_days} days",
        ]

    def build(self) -> list[ui.Item]:
        settings = cache.get(self.guild.id)
        return [
            title("Invites", toggle(settings.invite_tracker, self._toggle)),
            row(f"{emoji.fake} **Fake Account Age**: {settings.invite_fake_days} days", pencil(self._edit_days)),
            ui.ActionRow(self.panel.confirm_button("invites-counts", "Reset counts", self._reset_counts)),
        ]

    async def _toggle(self, interaction: discord.Interaction) -> None:
        await invites.set_tracker(self.guild, not cache.get(self.guild.id).invite_tracker)
        await self.panel.refresh(interaction)

    async def _edit_days(self, interaction: discord.Interaction) -> None:
        days = ui.InputText(value=str(cache.get(self.guild.id).invite_fake_days), min_length=1, max_length=3)

        async def submit(submitted: discord.Interaction) -> None:
            value = (days.value or "").strip()
            try:
                # A non-number goes through as -1 so it gets the same "0 to N days" message
                await invites.set_fake_days(self.guild, int(value) if value.isdigit() else -1)
            except SettingError as exc:
                await self.panel.error(submitted, str(exc))
                return
            await self.panel.refresh(submitted)

        label = ui.Label("Days", days, description="Accounts younger than this when they join count as fake.")
        await interaction.response.send_modal(modal("Fake account age", label, on_submit=submit))

    async def _reset_counts(self, interaction: discord.Interaction) -> None:
        await invites.reset_counts(self.guild)
        await self.panel.refresh(interaction)

    async def reset(self, interaction: discord.Interaction) -> None:
        await invites.reset(self.guild)
