import discord
from collections.abc import Awaitable, Callable
from discord import SlashCommandGroup
from discord.commands import option
from square.core import Client
from square.music import controls
from square.music.core import (
    get_player,
)
from square.music.filters import EQ_PRESETS, EqPreset


class Equalizer:
    """The `/eq` command group. Preset subcommands are added from `EQ_PRESETS` below."""

    client: Client
    _control: Callable[[discord.ApplicationContext, Awaitable[str]], Awaitable[None]]  # From the Music cog

    # Equalizer slash cmd group
    eq = SlashCommandGroup(name="eq", description="Equalizer commands.")

    @eq.command(name="reset")
    async def reset(self, ctx: discord.ApplicationContext):
        """Resets the equalizer to default."""
        await self._control(ctx, controls.reset_eq(ctx.guild, ctx.author))

    async def filter_autocomplete(self, ctx: discord.AutocompleteContext):
        """Offers the active presets by name."""
        player = get_player(self.client, ctx.interaction.guild_id)
        if not player:
            return []
        needle = ctx.value.lower()
        return [
            discord.OptionChoice(name=EQ_PRESETS[n].label, value=n)
            for n in player.presets
            if needle in EQ_PRESETS[n].label.lower()
        ]

    @eq.command(name="remove")
    @option("name", description="Name of the equalizer to remove.", autocomplete=filter_autocomplete)
    async def remove_eq(self, ctx: discord.ApplicationContext, name: str):
        """Removes an equalizer by name."""
        await self._control(ctx, controls.set_eq(ctx.guild, ctx.author, name, False))


def _add_preset_command(name: str, preset: EqPreset) -> None:
    async def apply(self, ctx: discord.ApplicationContext):
        await self._control(ctx, controls.set_eq(ctx.guild, ctx.author, name, True))

    Equalizer.eq.command(name=name, description=preset.description)(apply)


for _name, _preset in EQ_PRESETS.items():
    _add_preset_command(_name, _preset)
