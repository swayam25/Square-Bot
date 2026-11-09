import math
import re
import unicodedata
from functools import lru_cache
from PIL import Image
from square.imaging.layout import Bar, Box, Column, Expand, Node, Picture, Progress, Row, Spacer, Stack, Text
from square.imaging.theme import RGB, Scheme
from square.imaging.tokens import Shape, TextStyle, Type
from square.utils.emoji import EMOJI_DIR
from typing import Literal

type Tone = Literal["primary", "secondary", "tertiary", "success", "warning", "error"]
type CardVariant = Literal["filled", "elevated", "outlined"] | Tone


@lru_cache(maxsize=128)
def load_icon(name: str, color: RGB | None = None) -> Image.Image:
    """
    One of the bot's emojis from `assets/emojis` as an icon, so images and messages share one icon set.

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


# Discord's own fallback for a server with no icon, sampled from its dark theme, so it looks the same as in the app
_ACRONYM_TILE: RGB = (0x22, 0x22, 0x25)
_ACRONYM_TEXT: RGB = (0xEF, 0xEF, 0xF1)


def acronym(name: str) -> str:
    """A server's initials the way Discord's client makes them, e.g. "My Server" -> "MS"."""
    # Mirrors the client's JS, whose `\w` is ASCII only: other characters (emoji, accents) are kept whole
    words = re.sub(r"\w+", lambda match: match.group()[0], name.replace("'s ", " "), flags=re.ASCII)
    return re.sub(r"\s", "", words)


class Kit:
    """
    Components bound to one color scheme, so templates never pick raw colors for common pieces.

    Args:
        scheme (:class:`Scheme`): The colors every component is drawn with.
    """

    def __init__(self, scheme: Scheme):
        self.scheme = scheme

    def container(self, tone: Tone) -> tuple[RGB, RGB]:
        """The `(container, on_container)` color pair for a tone."""
        s = self.scheme
        return getattr(s, f"{tone}_container"), getattr(s, f"on_{tone}_container")

    def text(self, text: str, style: TextStyle = Type.BODY_MEDIUM, color: RGB | None = None, *, align="start") -> Text:
        return Text(text, style, color or self.scheme.on_surface, align=align)

    def card(
        self,
        *children: Node | None,
        variant: CardVariant = "filled",
        padding: float | tuple[float, float] = 16,
        gap: float = 8,
        radius: float = Shape.LARGE,
        align: Literal["start", "center", "end", "stretch"] = "stretch",
    ) -> Box:
        """
        A card holding children in a column.

        Filled, elevated and outlined follow the usual card styles. A tone fills it with that tone's container color, so
        its text should use the matching `on_*_container` color from `container`.
        """
        s = self.scheme
        match variant:
            case "filled":
                fill, outline = s.surface_container_highest, None
            case "elevated":
                fill, outline = s.surface_container_low, None
            case "outlined":
                fill, outline = s.surface, s.outline_variant
            case tone:
                fill, outline = self.container(tone)[0], None
        return Box(Column(*children, gap=gap, align=align), padding=padding, fill=fill, outline=outline, radius=radius)

    def guild_icon(
        self, image: Image.Image | None, name: str, size: float = 48, *, radius: float = Shape.MEDIUM
    ) -> Node:
        """A server's icon, or Discord's fallback when it has none: the name's acronym on a dark rounded tile."""
        if image is not None:
            return Picture(image, size, radius=radius)
        letters = acronym(name) or "?"
        # Long acronyms shrink, like in Discord
        scale = 0.38 if len(letters) <= 2 else 0.3 if len(letters) <= 4 else 0.22
        return Box(
            Text(letters, TextStyle(size * scale, size, 500), _ACRONYM_TEXT, align="center"),
            padding=(size * 0.08, 0),
            fill=_ACRONYM_TILE,
            radius=radius,
            width=size,
            height=size,
        )

    def avatar(
        self,
        image: Image.Image | None,
        name: str,
        size: float = 40,
        *,
        tone: Tone = "primary",
        inverted: bool = False,
        radius: float = Shape.FULL,
    ) -> Node:
        """
        A picture, or the name's first letter on a tonal circle when there isn't one.

        Set `inverted` when it sits on a card of the same tone, so the fallback circle doesn't blend into the card.
        """
        if image is not None:
            return Picture(image, size, radius=radius)
        fill, color = self.container(tone)
        if inverted:
            fill, color = color, fill
        style = TextStyle(size * 0.4, size, 500)
        # NFKC folds styled letters like 𝓶 into plain ones, so they can be uppercased
        initial = next((char for char in unicodedata.normalize("NFKC", name) if char.isalnum()), "?").upper()
        return Box(Text(initial, style, color, align="center"), fill=fill, radius=radius, width=size, height=size)

    def crowned(self, avatar: Node, size: float, *, tilt: float = 35) -> Stack:
        """An avatar wearing the crown emoji on its top-left, tilted like a worn crown. `size` is the avatar's."""
        icon = load_icon("crown")
        crown = icon.crop(icon.getbbox())
        width = size * 0.5
        height = width * crown.height / crown.width
        # On the rim where the tilt points, sunk in slightly so it looks worn
        reach = size / 2 + height / 2 - size * 0.06
        cx = size / 2 - reach * math.sin(math.radians(tilt))
        cy = size / 2 - reach * math.cos(math.radians(tilt))
        tilted = crown.rotate(tilt, Image.Resampling.BICUBIC, expand=True)
        # `expand` grows the image, so the box is sized from the crown's own scale
        box_w, box_h = tilted.width * width / crown.width, tilted.height * width / crown.width
        return Stack(avatar, (Picture(tilted, box_w, box_h), cx - box_w / 2, cy - box_h / 2))

    def chip(self, label: str, tone: Tone | None = None, *, icon: str | None = None, tint: bool = True) -> Box:
        """
        An assist chip. Outlined by default, filled with a tone's container color when given one.

        `icon` names a leading icon from `assets/emojis`, tinted to the label's color unless `tint` is off (brand logos).
        """
        if tone is None:
            fill, color, outline = None, self.scheme.on_surface_variant, self.scheme.outline_variant
        else:
            (fill, color), outline = self.container(tone), None
        text = Text(label, Type.LABEL_MEDIUM, color)
        return Box(
            Row(self.icon(icon, 16, color if tint else None), text, gap=6) if icon else text,
            padding=(4, 10, 4, 6) if icon else (10, 4),
            fill=fill,
            outline=outline,
            radius=Shape.SMALL,
        )

    def icon(self, name: str, size: float = 24, color: RGB | None = None) -> Picture:
        """One of the bot's emojis as an icon, see `load_icon`. Pass no color to keep a brand logo's own colors."""
        return Picture(load_icon(name, color), size)

    def dot(self, color: RGB, size: float = 10) -> Box:
        return Box(Spacer(size), fill=color, radius=Shape.FULL, width=size, height=size)

    def segmented_bar(self, *segments: tuple[float, RGB], height: float = 12) -> Bar:
        """A segmented progress bar: one rounded segment per value, over a `secondary_container` track."""
        return Bar(list(segments), self.scheme.secondary_container, height=height)

    def progress(self, value: float, *, wavy: bool = False) -> Progress:
        """A linear progress indicator, `primary` over a `secondary_container` track. `value` runs from 0 to 1."""
        return Progress(value, self.scheme.primary, self.scheme.secondary_container, wavy=wavy)

    def stat(self, label: str, value: str, color: RGB | None = None, *, icon: str | None = None) -> Box:
        """
        A filled tile with a label over a big number.

        When it's keyed to a color, the label leads with `icon` in that color, or a legend dot without one.
        """
        s = self.scheme
        if icon:
            key = self.icon(icon, 18, color or s.on_surface_variant)
        else:
            key = self.dot(color) if color else None
        return self.card(
            Row(key, self.text(label, Type.LABEL_LARGE, s.on_surface_variant), gap=8),
            self.text(value, Type.HEADLINE_SMALL),
            variant="filled",
            padding=(16, 12),
            gap=4,
        )

    def chips(self, *chips: Box | None, gap: float = 6) -> Row:
        return Row(*chips, gap=gap)

    def list_item(
        self,
        title: str,
        *,
        leading: Node | None = None,
        supporting: Node | None = None,
        trailing: Node | None = None,
        fill: RGB | None = None,
    ) -> Box:
        """A list item on its own rounded tile: leading, a title over supporting content, trailing."""
        body = Column(self.text(title, Type.TITLE_MEDIUM), supporting, gap=4)
        return Box(
            Row(leading, Expand(body), trailing, gap=16),
            padding=(16, 10),
            fill=fill or self.scheme.surface_container,
            radius=Shape.LARGE,
        )

    def header(
        self,
        title: str,
        subtitle: str | Node | None = None,
        *,
        leading: Node | None = None,
        trailing: Node | None = None,
    ) -> Row:
        """A title block for the top of an image. The subtitle can be a ready-made row, e.g. text with an icon."""
        s = self.scheme
        if isinstance(subtitle, str):
            subtitle = self.text(subtitle, Type.BODY_MEDIUM, s.on_surface_variant)
        return Row(leading, Expand(Column(self.text(title, Type.HEADLINE_SMALL), subtitle)), trailing, gap=16)
