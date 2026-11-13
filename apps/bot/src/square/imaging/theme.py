from dataclasses import dataclass
from functools import cache
from square.utils import config

type RGB = tuple[int, int, int]


def rgb(value: int) -> RGB:
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF


def blend(color: RGB, alpha: float, base: RGB) -> RGB:
    r, g, b = (round(c * alpha + under * (1 - alpha)) for c, under in zip(color, base, strict=True))
    return r, g, b


WHITE: RGB = rgb(0xFFFFFF)
GRAY_950: RGB = rgb(0x030712)
GRAY_400: RGB = rgb(0x9CA3AF)
GRAY_300: RGB = rgb(0xD1D5DB)
GRAY_100: RGB = rgb(0xF3F4F6)
CYAN_950: RGB = rgb(0x053345)
CYAN_300: RGB = rgb(0x53EAFD)
VIOLET_500: RGB = rgb(0x8E51FF)
VIOLET_300: RGB = rgb(0xC4B4FF)
ORANGE_300: RGB = rgb(0xFFB86A)
EMERALD_400: RGB = rgb(0x00D492)
AMBER_400: RGB = rgb(0xFFB900)
RED_400: RGB = rgb(0xFF6467)
SURFACE_1: RGB = rgb(0x111827)
SURFACE_2: RGB = rgb(0x1F2937)
SURFACE_3: RGB = rgb(0x374151)
AVATAR_FILLS: tuple[RGB, ...] = tuple(
    rgb(value)
    for value in (
        0xFFB900,
        0x8EC5FF,
        0xFFA1AD,
        0xA4F4CF,
        0xDDD6FF,
        0xFFD6A7,
        0xB8E6FE,
        0xFCCEE8,
    )
)


@dataclass(frozen=True, slots=True)
class Theme:
    accent: RGB
    success: RGB = EMERALD_400
    warning: RGB = AMBER_400
    danger: RGB = RED_400
    bg: RGB = GRAY_950
    surface: RGB = SURFACE_1
    surface_2: RGB = SURFACE_2
    surface_3: RGB = SURFACE_3
    text: RGB = GRAY_100
    muted: RGB = GRAY_400
    on_accent: RGB = CYAN_950
    accent_ink: RGB = CYAN_300
    violet: RGB = VIOLET_500
    violet_ink: RGB = VIOLET_300

    @property
    def line(self) -> RGB:
        return blend(WHITE, 0.1, self.surface)

    def tint(self, color: RGB, alpha: float, base: RGB | None = None) -> RGB:
        return blend(color, alpha, base or self.surface)


@cache
def theme(accent: int | None = None) -> Theme:
    return Theme(accent=rgb(config.color.theme if accent is None else accent))
