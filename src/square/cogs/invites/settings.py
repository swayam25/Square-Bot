import discord
from discord import ui
from square.core.settings import SettingsPage, modal, pencil, row, title, toggle
from square.db import cache
from square.db.funcs.invites import reset_invites, set_fake_days, set_tracker
from square.utils import invites
from square.utils.emoji import emoji

MAX_FAKE_DAYS = 365


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
        await set_tracker(self.guild.id, not cache.get(self.guild.id).invite_tracker)
        await invites.refresh(self.guild)  # Starts or stops caching this server's invite uses
        await self.panel.refresh(interaction)

    async def _edit_days(self, interaction: discord.Interaction) -> None:
        days = ui.InputText(value=str(cache.get(self.guild.id).invite_fake_days), min_length=1, max_length=3)

        async def submit(submitted: discord.Interaction) -> None:
            value = (days.value or "").strip()
            if not value.isdigit() or int(value) > MAX_FAKE_DAYS:
                await self.panel.error(submitted, f"Enter a whole number of days from 0 to {MAX_FAKE_DAYS}.")
                return
            await set_fake_days(self.guild.id, int(value))
            await self.panel.refresh(submitted)

        label = ui.Label("Days", days, description="Accounts younger than this when they join count as fake.")
        await interaction.response.send_modal(modal("Fake account age", label, on_submit=submit))

    async def _reset_counts(self, interaction: discord.Interaction) -> None:
        await reset_invites(self.guild.id)
        await self.panel.refresh(interaction)

    async def reset(self, interaction: discord.Interaction) -> None:
        await set_tracker(self.guild.id, False)
        await set_fake_days(self.guild.id, 7)
        await invites.refresh(self.guild)
