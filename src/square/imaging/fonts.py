import unicodedata
from fontTools.ttLib import TTFont
from functools import cache
from importlib.resources import files
from PIL import ImageFont
from square.imaging.tokens import Family

_DIR = files(__package__) / "fonts"

# Color bitmaps (CBDT), which Pillow can only load at the size they were drawn at, so callers scale the result.
# From googlefonts/noto-emoji `2D/fonts/NotoColorEmoji.ttf` (v2.057, Emoji 18). Use that CBDT file when updating, not
# `Noto-COLRv1.ttf` or the google/fonts copy: Pillow draws COLRv1 glyphs in plain black.
EMOJI = "NotoColorEmoji.ttf"
EMOJI_PX = 109

# The website's CSS font stacks: each family's own font, then Noto Sans and the rest of Noto, so anything Saira or
# JetBrains Mono lacks (Cyrillic, Devanagari, Discord's math letters like 𝓴𝓪𝓲, symbols, emoji) still draws.
# NOTE: No CJK font yet (~16 MB), so those names render as boxes until one is added to `_NOTO`.
_NOTO = ("NotoSans.ttf", "NotoSansMath.ttf", "NotoSansSymbols.ttf", "NotoSansSymbols2.ttf", EMOJI)
CHAINS: dict[Family, tuple[str, ...]] = {
    "display": ("Saira.ttf", *_NOTO),
    "sans": _NOTO,
    "mono": ("JetBrainsMono.ttf", *_NOTO),
}

_TEXT_STYLE = "\ufe0e"
_EMOJI_STYLE = "\ufe0f"
# Code points below U+1F000 that are emoji by default (Emoji_Presentation=Yes in Unicode 18.0's emoji-data.txt).
# The symbol fonts also have glyphs for these, so without this list ⭐ or ⚡ would come out as plain outlines.
_EMOJI_DEFAULT_BMP = frozenset(
    code
    for first, last in (
        (0x231A, 0x231B),
        (0x23E9, 0x23EC),
        (0x23F0, 0x23F0),
        (0x23F3, 0x23F3),
        (0x25FD, 0x25FE),
        (0x2614, 0x2615),
        (0x2648, 0x2653),
        (0x267F, 0x267F),
        (0x2693, 0x2693),
        (0x26A1, 0x26A1),
        (0x26AA, 0x26AB),
        (0x26BD, 0x26BE),
        (0x26C4, 0x26C5),
        (0x26CE, 0x26CE),
        (0x26D4, 0x26D4),
        (0x26EA, 0x26EA),
        (0x26F2, 0x26F3),
        (0x26F5, 0x26F5),
        (0x26FA, 0x26FA),
        (0x26FD, 0x26FD),
        (0x2705, 0x2705),
        (0x270A, 0x270B),
        (0x2728, 0x2728),
        (0x274C, 0x274C),
        (0x274E, 0x274E),
        (0x2753, 0x2755),
        (0x2757, 0x2757),
        (0x2795, 0x2797),
        (0x27B0, 0x27B0),
        (0x27BF, 0x27BF),
        (0x2B1B, 0x2B1C),
        (0x2B50, 0x2B50),
        (0x2B55, 0x2B55),
    )  # fmt: skip
    for code in range(first, last + 1)
)


@cache
def _coverage(name: str) -> frozenset[int]:
    with TTFont(str(_DIR / name), lazy=True) as font:
        return frozenset(font.getBestCmap())


@cache
def font(name: str, px: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    """
    Loads a bundled font at a pixel size, setting its weight axis when it has one.

    Args:
        name (str): A file name from `CHAINS`.
        px (int): The size in pixels. Must be `EMOJI_PX` for `EMOJI`.
        weight (int): The CSS-style weight, clamped to what the font supports.
    """
    loaded = ImageFont.truetype(str(_DIR / name), px)
    try:
        axes = loaded.get_variation_axes()
    except OSError:  # Static font
        return loaded
    loaded.set_variation_by_axes(
        [
            max(axis["minimum"], min(axis["maximum"], weight)) if axis["name"] == b"Weight" else axis["default"]
            for axis in axes
        ]
    )
    return loaded


def _joins_previous(char: str) -> bool:
    """Marks, variation selectors and joiners must stay in the same run as the character they modify."""
    return unicodedata.category(char) in ("Mn", "Me", "Cf")


def _wants_emoji(char: str, following: str) -> bool:
    """
    Whether a character should draw as a color emoji, following Unicode's presentation rules.

    A trailing U+FE0F asks for emoji (❤️, 1️⃣) and U+FE0E for text. Without one, everything from U+1F000 up and the
    few older symbols in `_EMOJI_DEFAULT_BMP` default to emoji.
    """
    code = ord(char)
    if code not in _coverage(EMOJI) or following == _TEXT_STYLE:
        return False
    return following == _EMOJI_STYLE or code >= 0x1F000 or code in _EMOJI_DEFAULT_BMP


def runs(text: str, family: Family = "sans") -> list[tuple[str, str]]:
    """
    Splits text into `(font name, substring)` runs, each drawn with the first font in the family's chain that covers it.

    Emoji go to `EMOJI` first when Unicode says they default to emoji, see `_wants_emoji`. Characters no font
    covers stay with the family's own font and render as boxes.
    """
    chain = CHAINS[family]
    result: list[tuple[str, str]] = []
    for index, char in enumerate(text):
        if result and _joins_previous(char):
            name, chunk = result[-1]
            result[-1] = (name, chunk + char)
            continue
        if unicodedata.category(char) == "Cc":
            continue
        if _wants_emoji(char, text[index + 1 : index + 2]):
            name = EMOJI
        else:
            name = next((name for name in chain if ord(char) in _coverage(name)), chain[0])
        if result and result[-1][0] == name:
            result[-1] = (name, result[-1][1] + char)
        else:
            result.append((name, char))
    return result
