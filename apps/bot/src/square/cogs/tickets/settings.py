import discord
from discord import ui
from square.cogs.tickets import cards
from square.core.settings import (
    SettingsPage,
    button,
    channel_picker,
    mention_or_off,
    modal,
    pencil,
    role_picker,
    title,
    toggle,
)
from square.core.view import show_loading
from square.db import cache
from square.settings import tickets
from square.settings.errors import SettingError
from square.utils.emoji import emoji


class TicketsPage(SettingsPage):
    name = "Tickets"
    emoji = emoji.ticket
    description = "Category, support roles, limits and the panel"
    order = 4

    def summary(self) -> list[str]:
        settings = cache.get(self.guild.id)
        roles = ", ".join(role.mention for role in cards.support_roles(self.guild)) or emoji.off
        return [
            f"{emoji.ticket} **Ticket Commands**: {emoji.on if settings.ticket_cmds else emoji.off}",
            f"{emoji.support} **Support Roles**: {roles}",
            f"{emoji.channel} **Panel**: {mention_or_off(tickets.panel_channel(self.guild))}",
        ]

    def build(self) -> list[ui.Item]:
        settings = cache.get(self.guild.id)
        roles = ", ".join(role.mention for role in cards.support_roles(self.guild)) or emoji.off
        category = tickets.category(self.guild)
        setup = "\n".join(
            [
                f"{emoji.category} **Category**: {category.mention if category else 'Created on the first ticket'}",
                f"{emoji.support} **Support Roles**: {roles}",
                f"{emoji.user} **Open Per Member**: {settings.ticket_max_open}",
                f"{emoji.lock} **Confirm Before Closing**: {emoji.on if settings.ticket_confirm_close else emoji.off}",
            ]
        )
        if tickets.panel_channel(self.guild):
            panel_btn = self.panel.confirm_button("ticket-panel", "Remove", self._remove_panel)
        else:
            panel_btn = button(self._create_panel, label="Create", emoji=emoji.add_white)
        return [
            title("Tickets", toggle(settings.ticket_cmds, self._toggle)),
            ui.Section(ui.TextDisplay(setup), accessory=pencil(self._edit_setup)),
            ui.Section(
                ui.TextDisplay(f"{emoji.channel} **Panel**: {mention_or_off(tickets.panel_channel(self.guild))}"),
                accessory=panel_btn,
            ),
        ]

    async def _toggle(self, interaction: discord.Interaction) -> None:
        await tickets.set_enabled(self.guild, not cache.get(self.guild.id).ticket_cmds)
        await self.panel.refresh(interaction)

    async def _edit_setup(self, interaction: discord.Interaction) -> None:
        settings = cache.get(self.guild.id)
        category = tickets.category(self.guild)
        category_picker = channel_picker([discord.ChannelType.category], category)
        roles_picker = role_picker(cards.support_roles(self.guild), max_values=tickets.MAX_SUPPORT_ROLES)
        limit = ui.RadioGroup(
            options=[
                discord.RadioGroupOption(label=str(n), value=str(n), default=n == settings.ticket_max_open)
                for n in tickets.OPEN_LIMITS
            ]
        )
        confirm = ui.Checkbox(default=settings.ticket_confirm_close)

        async def submit(submitted: discord.Interaction) -> None:
            picked = category_picker.values or []
            try:
                await tickets.set_setup(
                    self.guild,
                    category=picked[0] if picked and isinstance(picked[0], discord.CategoryChannel) else None,
                    support_roles=[role for role in roles_picker.values or [] if isinstance(role, discord.Role)],
                    max_open=int(limit.value or settings.ticket_max_open),
                    confirm_close=bool(confirm.value),
                )
            except SettingError as exc:
                await self.panel.error(submitted, str(exc))
                return
            await self.panel.refresh(submitted)

        await interaction.response.send_modal(
            modal(
                "Ticket setup",
                ui.Label("Category", category_picker, description="Empty: I create a Tickets category on first use."),
                ui.Label("Support roles", roles_picker, description="They see, claim and manage every ticket."),
                ui.Label("Open tickets per member", limit),
                ui.Label("Ask before closing a ticket", confirm),
                on_submit=submit,
            )
        )

    async def _create_panel(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self.panel, interaction, "Creating..."):
            return
        try:
            await tickets.create_panel(self.guild)
        except SettingError as exc:
            await self.panel.error(interaction, str(exc))
        await self.panel.refresh(interaction)

    async def _remove_panel(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if note := await tickets.remove_panel(self.guild, self.panel.author):
            await self.panel.error(interaction, note)
        await self.panel.refresh(interaction)

    async def reset(self, interaction: discord.Interaction) -> None:
        if note := await tickets.reset(self.guild, self.panel.author):
            await self.panel.error(interaction, note)
