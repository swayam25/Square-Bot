from __future__ import annotations

import discord
from collections.abc import Awaitable, Callable, Sequence
from discord import ui
from square.utils.emoji import Icon, emoji
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from square.cogs.settings import SettingsPanel

Callback = Callable[[discord.Interaction], Awaitable[None]]


class SettingsPage:
    """One page of the `/settings` panel, shipped by the cog it configures through `Cog.settings_pages`."""

    name: str
    emoji: Icon
    description: str  # Shown under the page in the page picker
    order: int = 0

    def __init__(self, panel: SettingsPanel):
        self.panel = panel
        self.guild: discord.Guild = panel.guild

    def summary(self) -> list[str]:
        """Lines for the home page."""
        raise NotImplementedError

    def build(self) -> list[ui.Item]:
        """The page's items, starting with its title."""
        raise NotImplementedError

    async def reset(self, interaction: discord.Interaction) -> None:
        """Clears every setting on this page."""
        raise NotImplementedError


def title(name: str, accessory: ui.Button | None = None) -> ui.Item:
    """A page title. A page's main on/off switch goes beside it instead of on a row of its own."""
    heading = ui.TextDisplay(f"## {name}")
    return ui.Section(heading, accessory=accessory) if accessory else heading


def row(text: str, accessory: ui.Button) -> ui.Section:
    return ui.Section(ui.TextDisplay(text), accessory=accessory)


def button(callback: Callback, **kwargs) -> ui.Button:
    btn = ui.Button(style=kwargs.pop("style", discord.ButtonStyle.grey), **kwargs)
    btn.callback = callback  # py-cord's way to attach a handler
    return btn


def pencil(callback: Callback) -> ui.Button:
    return button(callback, label="Edit", emoji=emoji.edit_white)


def toggle(enabled: bool, callback: Callback) -> ui.Button:
    return button(callback, label="Enabled" if enabled else "Disabled", emoji=emoji.on if enabled else emoji.off)


def channel_picker(types: Sequence[discord.ChannelType], current: discord.abc.GuildChannel | None = None) -> ui.Select:
    """A single channel picker that may be left empty (to turn the setting off)."""
    return ui.Select(
        discord.ComponentType.channel_select,
        channel_types=list(types),
        min_values=0,
        max_values=1,
        required=False,
        default_values=[current] if current else [],
    )


def role_picker(current: Sequence[discord.Role] = (), max_values: int = 1) -> ui.Select:
    """A role picker that may be left empty (to turn the setting off)."""
    return ui.Select(
        discord.ComponentType.role_select,
        min_values=0,
        max_values=max_values,
        required=False,
        default_values=list(current),
    )


def modal(title: str, *labels: ui.Label, on_submit: Callback) -> ui.DesignerModal:
    """A modal of labelled pickers or inputs (up to 5), calling `on_submit` with the submit interaction."""
    form = ui.DesignerModal(*labels, title=title, timeout=600)
    form.callback = on_submit
    return form


def mention_or_off(item: discord.abc.GuildChannel | discord.Role | None) -> str:
    return item.mention if item else str(emoji.off)
