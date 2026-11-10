from dataclasses import dataclass
from typing import Literal

type Family = Literal["display", "sans", "mono"]


@dataclass(frozen=True, slots=True)
class TextStyle:
    """A Tailwind text style. `tracking` is letter spacing in em, like `tracking-tight` (-0.025)."""

    size: float
    line_height: float
    weight: int = 400
    family: Family = "sans"
    tracking: float = 0


class Type:
    """The text styles the cards use, in px. Named after their Tailwind classes, e.g. `SM` is `text-sm`."""

    # Saira, for titles and podium places
    DISPLAY_2XL = TextStyle(24, 32, 600, "display", -0.025)
    DISPLAY_XL = TextStyle(20, 28, 600, "display")
    DISPLAY_PLACE = TextStyle(36, 40, 700, "display")
    # Noto Sans, for everything people read
    BASE = TextStyle(16, 24)
    BASE_MEDIUM = TextStyle(16, 24, 500)
    BASE_SEMIBOLD = TextStyle(16, 24, 600)
    SM = TextStyle(14, 20)
    SM_MEDIUM = TextStyle(14, 20, 500)
    XS = TextStyle(12, 16)
    XS_MEDIUM = TextStyle(12, 16, 500)
    XS_SEMIBOLD = TextStyle(12, 16, 600)
    XL_SEMIBOLD = TextStyle(20, 28, 600)
    XL2_SEMIBOLD = TextStyle(24, 32, 600)
    # JetBrains Mono, for numbers, durations, handles and eyebrow labels
    MONO_5XL = TextStyle(48, 48, 500, "mono", -0.025)
    MONO_2XL = TextStyle(24, 32, 500, "mono")
    MONO_BASE = TextStyle(16, 24, 500, "mono")
    MONO_SM = TextStyle(14, 20, 400, "mono")
    MONO_SM_MEDIUM = TextStyle(14, 20, 500, "mono")
    MONO_XS = TextStyle(12, 16, 400, "mono")
    MONO_XS_MEDIUM = TextStyle(12, 16, 500, "mono")
    MONO_XS_LABEL = TextStyle(12, 16, 600, "mono", 0.1)
    MONO_XS_SEMIBOLD = TextStyle(12, 16, 600, "mono")
    MONO_EYEBROW = TextStyle(10, 12, 600, "mono", 0.05)


class Radius:
    """Tailwind corner radii in px. `FULL` rounds the shorter side into a pill or circle."""

    MD = 6  # rounded-md
    LG = 8  # rounded-lg
    XL = 12  # rounded-xl
    XL2 = 16  # rounded-2xl
    XL3 = 24  # rounded-3xl
    FULL = -1  # rounded-full
