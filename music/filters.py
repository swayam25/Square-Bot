from dataclasses import dataclass
from sonolink.models import Equalizer, Filters, Karaoke, LowPass, Rotation, Timescale, Tremolo, Vibrato


@dataclass(frozen=True, slots=True)
class EqPreset:
    """
    A ready-made `/eq` effect.

    Attributes:
        label (str): The name shown to users.
        slot (str): The Lavalink filter it drives. Two presets on one slot can't stack: sonolink
            blends their values, and equalizer bands would be sent twice.
        filters (:class:`Filters`): The effect itself, combined with the player's other presets.
    """

    label: str
    slot: str
    filters: Filters


EQ_PRESETS: dict[str, EqPreset] = {
    "bassboost": EqPreset(
        "Bass Boost",
        "equalizer",
        Filters(equalizer=[Equalizer(band=band, gain=gain) for band, gain in enumerate((0.2, 0.15, 0.1, 0.05))]),
    ),
    "nightcore": EqPreset("Nightcore", "timescale", Filters(timescale=Timescale(speed=1.25, pitch=1.25, rate=1.0))),
    "vaporwave": EqPreset("Vaporwave", "timescale", Filters(timescale=Timescale(speed=0.85, pitch=0.8, rate=1.0))),
    "8d": EqPreset("8D", "rotation", Filters(rotation=Rotation(rotation_hz=0.2))),
    "karaoke": EqPreset(
        "Karaoke",
        "karaoke",
        Filters(karaoke=Karaoke(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)),
    ),
    "soft": EqPreset("Soft", "low_pass", Filters(low_pass=LowPass(smoothing=20.0))),
    "tremolo": EqPreset("Tremolo", "tremolo", Filters(tremolo=Tremolo(frequency=2.0, depth=0.5))),
    "vibrato": EqPreset("Vibrato", "vibrato", Filters(vibrato=Vibrato(frequency=2.0, depth=0.5))),
}
