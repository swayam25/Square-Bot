import re
import unicodedata
import zlib
from functools import lru_cache
from PIL import Image
from square.imaging.layout import Box, Column, Expand, Node, Picture, Progress, Row, Spacer, SplitBar, Text
from square.imaging.theme import AVATAR_FILLS, GRAY_950, RGB, WHITE, Theme
from square.imaging.tokens import Radius, TextStyle, Type
from square.utils.emoji import EMOJI_DIR
from typing import Literal

type ChipTone = Literal["neutral", "muted", "on", "accent", "success", "warning", "danger", "violet"]


@lru_cache(maxsize=128)
def load_icon(name: str, color: RGB | None = None) -> Image.Image:
    with Image.open(EMOJI_DIR / f"{name}.png") as image:
        image = image.convert("RGBA")
    if color is None:
        return image
    tinted = Image.new("RGBA", image.size, (*color, 255))
    tinted.putalpha(image.getchannel("A"))
    return tinted


def acronym(name: str) -> str:
    # Mirrors the client's JS, whose `\w` is ASCII only: other characters (emoji, accents) are kept whole
    words = re.sub(r"\w+", lambda match: match.group()[0], name.replace("'s ", " "), flags=re.ASCII)
    return re.sub(r"\s", "", words)


def initial(name: str) -> str:
    return next((char for char in unicodedata.normalize("NFKC", name) if char.isalnum()), "?").upper()


class Kit:
    def __init__(self, theme: Theme):
        self.theme = theme

    def text(self, text: str, style: TextStyle = Type.SM, color: RGB | None = None, *, align="start") -> Text:
        return Text(text, style, color or self.theme.text, align=align)

    def muted(self, text: str, style: TextStyle = Type.SM, *, align="start") -> Text:
        return Text(text, style, self.theme.muted, align=align)

    def card(self, child: Node) -> Box:
        return Box(child, padding=24, fill=self.theme.bg, align="stretch")

    def tile(self, *children: Node | None, padding: float | tuple[float, float] = 16, gap: float = 8) -> Box:
        return Box(Column(*children, gap=gap), padding=padding, fill=self.theme.surface, radius=Radius.XL2)

    def _chip_colors(self, tone: ChipTone) -> tuple[RGB, RGB]:
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
        return Picture(load_icon(name, color), size)

    def dot(self, color: RGB, size: float = 8) -> Box:
        return Box(Spacer(size), fill=color, radius=Radius.FULL, width=size, height=size)

    def avatar(self, image: Image.Image | None, name: str, size: float = 40, style: TextStyle | None = None) -> Node:
        if image is not None:
            return Picture(image, size, radius=Radius.FULL)
        fill = AVATAR_FILLS[zlib.crc32(name.encode()) % len(AVATAR_FILLS)]
        style = style or (Type.XS_SEMIBOLD if size <= 32 else Type.XL_SEMIBOLD)
        return Box(
            Text(initial(name), style, GRAY_950, align="center"),
            fill=fill,
            radius=Radius.FULL,
            width=size,
            height=size,
        )

    def guild_icon(self, image: Image.Image | None, name: str, size: float = 40, *, radius: float = Radius.XL) -> Node:
        if image is not None:
            return Picture(image, size, radius=radius)
        letters = acronym(name) or "?"
        scale = 0.38 if len(letters) <= 2 else 0.3 if len(letters) <= 4 else 0.22
        return Box(
            Text(letters, TextStyle(size * scale, size, 500), self.theme.text, align="center"),
            padding=(size * 0.08, 0),
            fill=self.theme.surface,
            radius=radius,
            width=size,
            height=size,
        )

    def header(self, title: str, subtitle: Node, *, leading: Node, trailing: Node | None = None) -> Row:
        return Row(leading, Expand(Column(self.text(title, Type.DISPLAY_XL), subtitle, gap=2)), trailing, gap=16)

    def stat(self, label: str, value: str, color: RGB) -> Box:
        return self.tile(
            Row(self.dot(color), self.muted(label), gap=8),
            self.text(value, Type.MONO_2XL),
        )

    def split_bar(self, *segments: tuple[float, RGB], label: str | None = None) -> SplitBar:
        text = Text(label, Type.MONO_XS_SEMIBOLD, self.theme.on_accent) if label else None
        return SplitBar(list(segments), self.theme.surface, label=text)

    def progress(self, value: float, *, wavy: bool = False) -> Progress:
        return Progress(value, self.theme.accent, self.theme.line, wavy=wavy)

    def eyebrow(self, text: str) -> Text:
        return Text(text.upper(), Type.MONO_EYEBROW, self.theme.muted)
