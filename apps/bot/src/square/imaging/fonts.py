import unicodedata
from fontTools.ttLib import TTFont
from functools import cache
from importlib.resources import files
from PIL import ImageFont
from square.imaging.tokens import Family

_DIR = files(__package__) / "fonts"

# Built as COLRv0 on purpose: FreeType draws COLRv1 layers plain black.
EMOJI = "Twemoji.ttf"

# Mirrors the website's font stacks, so keep both in sync.
# NOTE: No CJK font yet (~16 MB), so CJK renders as boxes until one is added here.
_FALLBACK = ("Geist.ttf", "NotoSans.ttf", "NotoSansMath.ttf", "NotoSansSymbols.ttf", "NotoSansSymbols2.ttf", EMOJI)
CHAINS: dict[Family, tuple[str, ...]] = {
    "display": ("Saira.ttf", *_FALLBACK),
    "sans": _FALLBACK,
    "mono": ("JetBrainsMono.ttf", *_FALLBACK),
}

_TEXT_STYLE = "︎"
_EMOJI_STYLE = "️"
# People type these as text (™ ‼ ↔ ↩), so they need a U+FE0F to draw as emoji. The website's `unicode-range` skips them too.
_TEXT_FIRST = frozenset({0x203C, 0x2049, 0x2122, 0x2139, *range(0x2194, 0x219A), 0x21A9, 0x21AA})


@cache
def _coverage(name: str) -> frozenset[int]:
    with TTFont(str(_DIR / name), lazy=True) as font:
        return frozenset(font.getBestCmap())


@cache
def font(name: str, px: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    """Loads a bundled font, clamping `weight` to the font's weight axis when it has one."""
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
    return unicodedata.category(char) in ("Mn", "Me", "Cf")


def _wants_emoji(char: str, following: str) -> bool:
    """Above Latin-1 Twemoji wins even where Geist has a glyph (❤ ★), like on Discord. Below it, only U+FE0F asks."""
    code = ord(char)
    if code not in _coverage(EMOJI) or following == _TEXT_STYLE:
        return False
    return (code > 0xFF and code not in _TEXT_FIRST) or following == _EMOJI_STYLE


def runs(text: str, family: Family = "sans") -> list[tuple[str, str]]:
    """Splits text into `(font name, substring)` runs using the first font in the chain that covers each character."""
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
