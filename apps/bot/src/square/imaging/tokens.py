from dataclasses import dataclass
from typing import Literal

type Family = Literal["display", "sans", "mono"]


@dataclass(frozen=True, slots=True)
class TextStyle:
    size: float
    line_height: float
    weight: int = 400
    family: Family = "sans"
    tracking: float = 0


class Type:
    DISPLAY_2XL = TextStyle(24, 32, 600, "display", -0.025)
    DISPLAY_XL = TextStyle(20, 28, 600, "display")
    DISPLAY_PLACE = TextStyle(36, 40, 700, "display")
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
    MD = 6
    LG = 8
    XL = 12
    XL2 = 16
    XL4 = 32
    FULL = -1
