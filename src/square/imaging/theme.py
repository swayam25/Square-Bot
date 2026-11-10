from dataclasses import dataclass
from functools import cache
from square.utils import config

type RGB = tuple[int, int, int]


def rgb(value: int) -> RGB:
    """`0x1FCEEC` -> `(31, 206, 236)`."""
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF


def blend(color: RGB, alpha: float, base: RGB) -> RGB:
    """
    `color` at `alpha` opacity over `base`, the way a browser paints Tailwind's `bg-red-400/10`.

    Cards are drawn opaque, so translucent fills are flattened onto the surface they sit on here.
    """
    r, g, b = (round(c * alpha + under * (1 - alpha)) for c, under in zip(color, base, strict=True))
    return r, g, b


# Tailwind v4 colors, converted from the oklch values in `tailwindcss/theme.css`
WHITE: RGB = rgb(0xFFFFFF)
MIST_950: RGB = rgb(0x090B0C)
MIST_900: RGB = rgb(0x161B1D)
MIST_800: RGB = rgb(0x22292B)
MIST_700: RGB = rgb(0x394447)
MIST_400: RGB = rgb(0x9CA8AB)
MIST_300: RGB = rgb(0xD0D6D8)
MIST_100: RGB = rgb(0xF1F3F3)
CYAN_950: RGB = rgb(0x053345)
CYAN_300: RGB = rgb(0x53EAFD)
VIOLET_500: RGB = rgb(0x8E51FF)
VIOLET_300: RGB = rgb(0xC4B4FF)
ORANGE_300: RGB = rgb(0xFFB86A)
EMERALD_400: RGB = rgb(0x00D492)
AMBER_400: RGB = rgb(0xFFB900)
RED_400: RGB = rgb(0xFF6467)
# Fallback avatar circles, picked per name so a member keeps one color
AVATAR_FILLS: tuple[RGB, ...] = tuple(
    rgb(value)
    for value in (
        0xFFB900,  # amber-400
        0x8EC5FF,  # blue-300
        0xFFA1AD,  # rose-300
        0xA4F4CF,  # emerald-200
        0xDDD6FF,  # violet-200
        0xFFD6A7,  # orange-200
        0xB8E6FE,  # sky-200
        0xFCCEE8,  # pink-200
    )
)


@dataclass(frozen=True, slots=True)
class Theme:
    """
    The colors every image is drawn with, by role.

    Everything is Tailwind except the accent, which comes from `config.toml`. The status colors are Tailwind's too,
    not the Discord ones in `config.toml`, since embeds and emojis sit next to Discord's UI but images don't.
    """

    accent: RGB
    success: RGB = EMERALD_400
    warning: RGB = AMBER_400
    danger: RGB = RED_400
    bg: RGB = MIST_950
    surface: RGB = MIST_900
    surface_2: RGB = MIST_800
    surface_3: RGB = MIST_700
    text: RGB = MIST_100
    muted: RGB = MIST_400
    on_accent: RGB = CYAN_950
    accent_ink: RGB = CYAN_300
    violet: RGB = VIOLET_500
    violet_ink: RGB = VIOLET_300

    @property
    def line(self) -> RGB:
        """`white/10` on the surface: row dividers."""
        return blend(WHITE, 0.1, self.surface)

    def tint(self, color: RGB, alpha: float, base: RGB | None = None) -> RGB:
        """`color` at `alpha` over `base`, the surface by default."""
        return blend(color, alpha, base or self.surface)


@cache
def theme(accent: int | None = None) -> Theme:
    """
    The theme from `config.toml`.

    Args:
        accent (int | None): An RGB color like `0x1FCEEC` to preview instead of `colors.theme`.
    """
    return Theme(accent=rgb(config.color.theme if accent is None else accent))
