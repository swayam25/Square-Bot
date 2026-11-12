from dataclasses import dataclass
from sonolink.models import Equalizer, Filters, Karaoke, LowPass, Rotation, Timescale, Tremolo, Vibrato


@dataclass(frozen=True, slots=True)
class EqPreset:
    """
    A ready-made `/eq` effect.

    Attributes:
        label (str): The name shown to users.
        description (str): Shown under `/eq` and on the dashboard.
        slot (str): The Lavalink filter it drives. Two presets on one slot can't stack: sonolink
            blends their values, and equalizer bands would be sent twice.
        filters (:class:`Filters`): The effect itself, combined with the player's other presets.
    """

    label: str
    description: str
    slot: str
    filters: Filters


def _bands(*gains: tuple[int, float]) -> Filters:
    return Filters(equalizer=[Equalizer(band=band, gain=gain) for band, gain in gains])


def _speed(speed: float, pitch: float = 1.0) -> Filters:
    return Filters(timescale=Timescale(speed=speed, pitch=pitch, rate=1.0))


EQ_PRESETS: dict[str, EqPreset] = {
    "bassboost": EqPreset(
        "Bass Boost", "Boosts the low end.", "equalizer", _bands((0, 0.2), (1, 0.15), (2, 0.1), (3, 0.05))
    ),
    "treblebass": EqPreset(
        "Treble & Bass",
        "Boosts the low end and the highs.",
        "equalizer",
        _bands((0, 0.25), (1, 0.25), (2, 0.2), (3, 0.1), (10, 0.3), (11, 0.3), (12, 0.35), (13, 0.35)),
    ),
    "nightcore": EqPreset("Nightcore", "Speeds the track up and raises its pitch.", "timescale", _speed(1.25, 1.25)),
    "vaporwave": EqPreset("Vaporwave", "Slows the track down and lowers its pitch.", "timescale", _speed(0.85, 0.8)),
    "daycore": EqPreset("Daycore", "Slows the track down a little and deepens it.", "timescale", _speed(0.9, 0.85)),
    "chipmunk": EqPreset("Chipmunk", "Raises the pitch into a squeaky voice.", "timescale", _speed(1.05, 1.35)),
    "speed": EqPreset("Speed", "Plays faster without changing the pitch.", "timescale", _speed(1.3)),
    "slow": EqPreset("Slow", "Plays slower without changing the pitch.", "timescale", _speed(0.75)),
    "8d": EqPreset(
        "8D",
        "Pans the audio around your head. Best with headphones.",
        "rotation",
        Filters(rotation=Rotation(rotation_hz=0.2)),
    ),
    "karaoke": EqPreset(
        "Karaoke",
        "Strips out the lead vocals.",
        "karaoke",
        Filters(karaoke=Karaoke(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)),
    ),
    "soft": EqPreset(
        "Soft",
        "Mellows out the highs for a muffled, softer sound.",
        "low_pass",
        Filters(low_pass=LowPass(smoothing=20.0)),
    ),
    "tremolo": EqPreset(
        "Tremolo", "Makes the volume pulse.", "tremolo", Filters(tremolo=Tremolo(frequency=2.0, depth=0.5))
    ),
    "vibrato": EqPreset(
        "Vibrato", "Makes the pitch wobble.", "vibrato", Filters(vibrato=Vibrato(frequency=2.0, depth=0.5))
    ),
}
