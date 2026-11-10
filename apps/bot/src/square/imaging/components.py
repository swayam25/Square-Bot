import re
import unicodedata
import zlib
from functools import lru_cache
from PIL import Image
from square.imaging.layout import Box, Column, Expand, Node, Picture, Progress, Row, Spacer, SplitBar, Text
from square.imaging.theme import AVATAR_FILLS, MIST_950, RGB, WHITE, Theme
from square.imaging.tokens import Radius, TextStyle, Type
from square.utils.emoji import EMOJI_DIR
from typing import Literal

# How a chip is colored. "neutral" and "muted" sit on `white/10`; "on" is a setting that's switched on
# `p-6` inside a 1px border, which CSS's border-box counts as part of the padding box
type ChipTone = Literal["neutral", "muted", "on", "accent", "success", "warning", "danger", "violet"]


@lru_cache(maxsize=128)
def load_icon(name: str, color: RGB | None = None) -> Image.Image:
    """
    One of the bot's emojis from `emojis/` as an icon, so images and messages share one icon set.

    Tinted to `color` through its alpha, so any color variant of an icon works. Pass no color to keep a brand logo's
    own colors.
    """
    with Image.open(EMOJI_DIR / f"{name}.png") as image:
        image = image.convert("RGBA")
    if color is None:
        return image
    tinted = Image.new("RGBA", image.size, (*color, 255))
    tinted.putalpha(image.getchannel("A"))
    return tinted


def acronym(name: str) -> str:
    """A server's initials the way Discord's client makes them, e.g. "My Server" -> "MS"."""
    # Mirrors the client's JS, whose `\w` is ASCII only: other characters (emoji, accents) are kept whole
    words = re.sub(r"\w+", lambda match: match.group()[0], name.replace("'s ", " "), flags=re.ASCII)
    return re.sub(r"\s", "", words)


def initial(name: str) -> str:
    # NFKC folds styled letters like 𝓶 into plain ones, so they can be uppercased
    return next((char for char in unicodedata.normalize("NFKC", name) if char.isalnum()), "?").upper()


class Kit:
    """
    The card components, bound to one theme so templates never pick raw colors for common pieces.

    Args:
        theme (:class:`Theme`): The colors every component is drawn with.
    """

    def __init__(self, theme: Theme):
        self.theme = theme

    def text(self, text: str, style: TextStyle = Type.SM, color: RGB | None = None, *, align="start") -> Text:
        return Text(text, style, color or self.theme.text, align=align)

    def muted(self, text: str, style: TextStyle = Type.SM, *, align="start") -> Text:
        return Text(text, style, self.theme.muted, align=align)

    def card(self, child: Node) -> Box:
        """The card every image is: a plain `p-6` rectangle on the surface, no corners or border."""
        return Box(child, padding=24, fill=self.theme.surface, align="stretch")

    def tile(self, *children: Node | None, padding: float | tuple[float, float] = 16, gap: float = 8) -> Box:
        """A `surface-2` tile inside a card, `rounded-2xl`."""
        return Box(Column(*children, gap=gap), padding=padding, fill=self.theme.surface_2, radius=Radius.XL2)

    def _chip_colors(self, tone: ChipTone) -> tuple[RGB, RGB]:
        """A chip's (fill, ink). Status tones fill at 10% of their color, switched-on settings at 20%."""
        t = self.theme
        match tone:
            case "neutral":
                return t.tint(WHITE, 0.1), t.text
            case "muted":
                return t.tint(WHITE, 0.1), t.muted
            case "on":
                return t.tint(t.accent, 0.2), t.accent_ink
            case "violet":
                return t.tint(t.violet, 0.2), t.violet_ink
            case status:
                color = getattr(t, status)
                return t.tint(color, 0.1), color

    def chip(
        self,
        label: str,
        tone: ChipTone = "neutral",
        *,
        icon: str | None = None,
        tint: bool = True,
        dot: bool = False,
        style: TextStyle = Type.XS_MEDIUM,
    ) -> Box:
        """
        A pill chip, `h-8 text-xs`, filled by its tone.

        `icon` names a leading icon from `emojis/`, tinted to the label's color unless `tint` is off (brand
        logos). `dot` leads with an 8px status dot instead. Chips with a lead use `px-3` on both sides, text-only
        chips `px-4`.
        """
        fill, ink = self._chip_colors(tone)
        if icon:
            lead: Node | None = self.icon(icon, 16, ink if tint else None)
        elif dot:
            lead = self.dot(ink)
        else:
            lead = None
        return Box(
            Row(lead, Text(label, style, ink), gap=8),
            padding=(12, 0) if lead else (16, 0),
            fill=fill,
            radius=Radius.FULL,
            height=32,
        )

    def icon(self, name: str, size: float = 16, color: RGB | None = None) -> Picture:
        """One of the bot's emojis as an icon, see `load_icon`. Pass no color to keep a brand logo's own colors."""
        return Picture(load_icon(name, color), size)

    def dot(self, color: RGB, size: float = 8) -> Box:
        return Box(Spacer(size), fill=color, radius=Radius.FULL, width=size, height=size)

    def avatar(self, image: Image.Image | None, name: str, size: float = 40, style: TextStyle | None = None) -> Node:
        """A picture, or the name's initial on a pastel circle picked from the name, so it stays the same."""
        if image is not None:
            return Picture(image, size, radius=Radius.FULL)
        fill = AVATAR_FILLS[zlib.crc32(name.encode()) % len(AVATAR_FILLS)]
        style = style or (Type.XS_SEMIBOLD if size <= 32 else Type.XL_SEMIBOLD)
        return Box(
            Text(initial(name), style, MIST_950, align="center"),
            fill=fill,
            radius=Radius.FULL,
            width=size,
            height=size,
        )

    def guild_icon(self, image: Image.Image | None, name: str, size: float = 40, *, radius: float = Radius.XL) -> Node:
        """A server's icon, or its acronym on a `surface-2` tile when it has none, like Discord does."""
        if image is not None:
            return Picture(image, size, radius=radius)
        letters = acronym(name) or "?"
        # Long acronyms shrink, like in Discord
        scale = 0.38 if len(letters) <= 2 else 0.3 if len(letters) <= 4 else 0.22
        return Box(
            Text(letters, TextStyle(size * scale, size, 500), self.theme.text, align="center"),
            padding=(size * 0.08, 0),
            fill=self.theme.surface_2,
            radius=radius,
            width=size,
            height=size,
        )

    def header(self, title: str, subtitle: Node, *, leading: Node, trailing: Node | None = None) -> Row:
        """A card's title block: a picture, a Saira title over a subtitle row, and something on the right."""
        return Row(leading, Expand(Column(self.text(title, Type.DISPLAY_XL), subtitle, gap=2)), trailing, gap=16)

    def stat(self, label: str, value: str, color: RGB) -> Box:
        """A tile with a legend dot and label over a big mono number."""
        return self.tile(
            Row(self.dot(color), self.muted(label), gap=8),
            self.text(value, Type.MONO_2XL),
        )

    def split_bar(self, *segments: tuple[float, RGB], label: str | None = None) -> SplitBar:
        """A breakdown bar over a `surface-2` track. `label` goes inside the first part, in `on-accent` mono."""
        text = Text(label, Type.MONO_XS_SEMIBOLD, self.theme.on_accent) if label else None
        return SplitBar(list(segments), self.theme.surface_2, label=text)

    def progress(self, value: float, *, wavy: bool = False) -> Progress:
        """Track progress in the accent over a `surface-3` track. `value` runs from 0 to 1."""
        return Progress(value, self.theme.accent, self.theme.surface_3, wavy=wavy)

    def eyebrow(self, text: str) -> Text:
        """A small uppercase mono label, like "UP NEXT"."""
        return Text(text.upper(), Type.MONO_EYEBROW, self.theme.muted)
