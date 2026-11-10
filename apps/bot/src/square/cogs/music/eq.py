import discord
from discord import SlashCommandGroup
from discord.commands import option
from square.core import Client
from square.music.core import (
    get_player,
)
from square.music.filters import EQ_PRESETS
from square.music.player import (
    slash_log,
)
from square.music.utils import reply
from square.utils import config
from square.utils.emoji import emoji


class Equalizer:
    """The `/eq` command group for audio filter presets."""

    client: Client

    # Equalizer slash cmd group
    eq = SlashCommandGroup(name="eq", description="Equalizer commands.")

    async def _apply_preset(self, ctx: discord.ApplicationContext, name: str):
        """Turns a preset on, swapping out whichever active one drives the same filter."""
        player = await self.ensure_voice(ctx)
        if not player:
            return
        preset = EQ_PRESETS[name]
        replaced = [n for n in player.presets if n != name and EQ_PRESETS[n].slot == preset.slot]
        for n in replaced:
            del player.presets[n]
        player.presets[name] = preset.filters
        await player.apply_presets()
        swap = f", replacing **{EQ_PRESETS[replaced[0]].label}**" if replaced else ""
        await slash_log(ctx, f"{emoji.equalizer} Applied **{preset.label}** equalizer{swap}.")

    @eq.command(name="reset")
    async def reset(self, ctx: discord.ApplicationContext):
        """Resets the equalizer to default."""
        player = await self.ensure_voice(ctx)
        if player:
            player.presets.clear()
            await player.apply_presets()
            await slash_log(ctx, f"{emoji.equalizer} Reset equalizer to default settings.")

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
        player = await self.ensure_voice(ctx)
        if player:
            if name in player.presets:
                del player.presets[name]
                await player.apply_presets()
                await slash_log(ctx, f"{emoji.equalizer} Removed **{EQ_PRESETS[name].label}** equalizer.")
            else:
                await reply(ctx, f"{emoji.error} **{name}** equalizer not found.", color=config.color.red)

    @eq.command(name="bassboost")
    async def eq_bassboost(self, ctx: discord.ApplicationContext):
        """Boosts the low end."""
        await self._apply_preset(ctx, "bassboost")

    @eq.command(name="nightcore")
    async def eq_nightcore(self, ctx: discord.ApplicationContext):
        """Speeds the track up and raises its pitch."""
        await self._apply_preset(ctx, "nightcore")

    @eq.command(name="vaporwave")
    async def eq_vaporwave(self, ctx: discord.ApplicationContext):
        """Slows the track down and lowers its pitch."""
        await self._apply_preset(ctx, "vaporwave")

    @eq.command(name="8d")
    async def eq_8d(self, ctx: discord.ApplicationContext):
        """Pans the audio around your head. Best with headphones."""
        await self._apply_preset(ctx, "8d")

    @eq.command(name="karaoke")
    async def eq_karaoke(self, ctx: discord.ApplicationContext):
        """Strips out the lead vocals."""
        await self._apply_preset(ctx, "karaoke")

    @eq.command(name="soft")
    async def eq_soft(self, ctx: discord.ApplicationContext):
        """Mellows out the highs for a muffled, softer sound."""
        await self._apply_preset(ctx, "soft")

    @eq.command(name="tremolo")
    async def eq_tremolo(self, ctx: discord.ApplicationContext):
        """Makes the volume pulse."""
        await self._apply_preset(ctx, "tremolo")

    @eq.command(name="vibrato")
    async def eq_vibrato(self, ctx: discord.ApplicationContext):
        """Makes the pitch wobble."""
        await self._apply_preset(ctx, "vibrato")
