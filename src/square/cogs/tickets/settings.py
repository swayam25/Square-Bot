import discord
from discord import ui
from square.cogs.tickets import cards
from square.cogs.tickets.panel import post as post_panel
from square.cogs.tickets.panel import unbind as unbind_panel
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
from square.db.funcs.guild import set_ticket_cmds
from square.db.funcs.tickets import reset_ticket_settings, set_ticket_setup
from square.music.utils import delete_quietly
from square.utils.emoji import emoji

OPEN_LIMITS = (1, 2, 3, 5)
MAX_SUPPORT_ROLES = 10


class TicketsPage(SettingsPage):
    name = "Tickets"
    emoji = emoji.ticket
    description = "Category, support roles, limits and the panel"
    order = 4

    def _category(self) -> discord.abc.GuildChannel | None:
        category_id = cache.get(self.guild.id).ticket_category_id
        return self.guild.get_channel(category_id) if category_id else None

    def _panel_channel(self) -> discord.abc.GuildChannel | None:
        channel_id = cache.get(self.guild.id).ticket_panel_channel_id
        return self.guild.get_channel(channel_id) if channel_id else None

    def summary(self) -> list[str]:
        settings = cache.get(self.guild.id)
        roles = ", ".join(role.mention for role in cards.support_roles(self.guild)) or emoji.off
        return [
            f"{emoji.ticket} **Ticket Commands**: {emoji.on if settings.ticket_cmds else emoji.off}",
            f"{emoji.support} **Support Roles**: {roles}",
            f"{emoji.channel} **Panel**: {mention_or_off(self._panel_channel())}",
        ]

    def build(self) -> list[ui.Item]:
        settings = cache.get(self.guild.id)
        roles = ", ".join(role.mention for role in cards.support_roles(self.guild)) or emoji.off
        category = self._category()
        setup = "\n".join(
            [
                f"{emoji.category} **Category**: {category.mention if category else 'Created on the first ticket'}",
                f"{emoji.support} **Support Roles**: {roles}",
                f"{emoji.user} **Open Per Member**: {settings.ticket_max_open}",
                f"{emoji.lock} **Confirm Before Closing**: {emoji.on if settings.ticket_confirm_close else emoji.off}",
            ]
        )
        if self._panel_channel():
            panel_btn = self.panel.confirm_button("ticket-panel", "Remove", self._remove_panel)
        else:
            panel_btn = button(self._create_panel, label="Create", emoji=emoji.add_white)
        return [
            title("Tickets", toggle(settings.ticket_cmds, self._toggle)),
            ui.Section(ui.TextDisplay(setup), accessory=pencil(self._edit_setup)),
            ui.Section(
                ui.TextDisplay(f"{emoji.channel} **Panel**: {mention_or_off(self._panel_channel())}"),
                accessory=panel_btn,
            ),
        ]

    async def _toggle(self, interaction: discord.Interaction) -> None:
        await set_ticket_cmds(self.guild.id, not cache.get(self.guild.id).ticket_cmds)
        await self.panel.refresh(interaction)

    async def _edit_setup(self, interaction: discord.Interaction) -> None:
        settings = cache.get(self.guild.id)
        category = self._category()
        category_picker = channel_picker([discord.ChannelType.category], category)
        roles_picker = role_picker(cards.support_roles(self.guild), max_values=MAX_SUPPORT_ROLES)
        limit = ui.RadioGroup(
            options=[
                discord.RadioGroupOption(label=str(n), value=str(n), default=n == settings.ticket_max_open)
                for n in OPEN_LIMITS
            ]
        )
        confirm = ui.Checkbox(default=settings.ticket_confirm_close)

        async def submit(submitted: discord.Interaction) -> None:
            picked = category_picker.values or []
            await set_ticket_setup(
                self.guild.id,
                category_id=picked[0].id if picked and isinstance(picked[0], discord.CategoryChannel) else None,
                support_role_ids=[role.id for role in roles_picker.values or [] if isinstance(role, discord.Role)],
                max_open=int(limit.value or settings.ticket_max_open),
                confirm_close=bool(confirm.value),
            )
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
        """Creates a read-only channel holding the "Open a ticket" panel, kept up to date like the music card."""
        if not self.guild.me.guild_permissions.manage_channels:
            await self.panel.error(interaction, "I need the `Manage Channels` permission to create the channel.")
            return
        if not await show_loading(self.panel, interaction, "Creating..."):
            return
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                read_message_history=True,
                send_messages=False,
                add_reactions=False,
                create_public_threads=False,
                create_private_threads=False,
            ),
            self.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                read_message_history=True,
                send_messages=True,
                manage_messages=True,
                embed_links=True,
            ),
        }
        try:
            channel = await self.guild.create_text_channel(
                "tickets", overwrites=overwrites, topic="Press the button to open a private ticket with staff."
            )
            await post_panel(channel)
        except discord.HTTPException as exc:
            await self.panel.error(interaction, f"I couldn't create the ticket channel: {exc.text or exc}")
            await self.panel.refresh(interaction)
            return
        await self.panel.refresh(interaction)

    async def _remove_panel(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if note := await self._clear_panel():
            await self.panel.error(interaction, note)
        await self.panel.refresh(interaction)

    async def _clear_panel(self) -> str | None:
        """
        Unbinds the panel and deletes its channel. Returns a note when the channel had to be left behind.

        Panels posted before the bot made its own channel sit in channels people chat in, so a channel is only deleted
        when the panel is all it holds. Otherwise just the panel goes.
        """
        settings = cache.get(self.guild.id)
        channel, message_id = self._panel_channel(), settings.ticket_panel_message_id
        # Unbind first, so the deletes below don't look like someone removing the panel
        await unbind_panel(self.guild.id)
        if not isinstance(channel, discord.TextChannel):
            return None
        try:
            only_panel = [message.id async for message in channel.history(limit=2)] in ([message_id], [])
        except discord.HTTPException:
            only_panel = False
        if only_panel:
            try:
                await channel.delete(reason=f"Ticket panel removed by {self.panel.author}")
                return None
            except discord.HTTPException:
                return f"I couldn't delete {channel.mention}, so it's yours to remove."
        if message_id:
            await delete_quietly(channel.get_partial_message(message_id))
        return f"I removed the panel but kept {channel.mention}, since it has other messages."

    async def reset(self, interaction: discord.Interaction) -> None:
        await self._clear_panel()
        await set_ticket_cmds(self.guild.id, False)
        await reset_ticket_settings(self.guild.id)
