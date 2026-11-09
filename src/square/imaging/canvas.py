import math
from functools import lru_cache
from io import BytesIO
from PIL import Image, ImageChops, ImageDraw, ImageOps
from square.imaging import fonts
from square.imaging.theme import RGB
from square.imaging.tokens import Shape, TextStyle

SCALE = 2  # Output pixels per dp, so images stay sharp on high-DPI screens
# Pillow's shapes have no antialiasing, so everything is drawn this many times larger and downsampled once
_SUPERSAMPLE = 2
_K = SCALE * _SUPERSAMPLE

_ELLIPSIS = "…"


def _font(name: str, style: TextStyle):
    return fonts.font(name, round(style.size * _K), style.weight)


def _emoji_scale(style: TextStyle) -> float:
    """Emoji are drawn at `fonts.EMOJI_PX` and shrunk by this to match the text's size."""
    return style.size * _K / fonts.EMOJI_PX


def _run_width(name: str, chunk: str, style: TextStyle) -> float:
    if name == fonts.EMOJI:
        return fonts.font(name, fonts.EMOJI_PX).getlength(chunk) * _emoji_scale(style)
    return _font(name, style).getlength(chunk)


@lru_cache(maxsize=256)
def _emoji_tile(chunk: str, scale: float) -> tuple[Image.Image, float]:
    """An emoji run in color, scaled to size, and how far above the baseline its top sits."""
    emoji = fonts.font(fonts.EMOJI, fonts.EMOJI_PX)
    ascent, descent = emoji.getmetrics()
    tile = Image.new("RGBA", (math.ceil(emoji.getlength(chunk)), ascent + descent))
    ImageDraw.Draw(tile).text((0, ascent), chunk, font=emoji, embedded_color=True, anchor="ls")
    size = (max(round(tile.width * scale), 1), max(round(tile.height * scale), 1))
    return tile.resize(size, Image.Resampling.LANCZOS), ascent * scale


def text_width(text: str, style: TextStyle) -> float:
    return sum(_run_width(name, chunk, style) for name, chunk in fonts.runs(text)) / _K


def fit_text(text: str, style: TextStyle, max_width: float) -> str:
    """Cuts text to fit `max_width` dp, ending it with an ellipsis when anything was cut."""
    if text_width(text, style) <= max_width:
        return text
    low, high = 0, len(text)
    while low < high:  # The longest prefix that still fits with the ellipsis
        mid = (low + high + 1) // 2
        if text_width(text[:mid].rstrip() + _ELLIPSIS, style) <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + _ELLIPSIS


def open_image(data: bytes | None) -> Image.Image | None:
    """Decodes image bytes, or returns None if there are none or they're broken."""
    if not data:
        return None
    try:
        with Image.open(BytesIO(data)) as image:
            return image.convert("RGBA")
    except OSError:
        return None


class Canvas:
    """A drawing surface measured in dp, filled edge to edge with its background."""

    def __init__(self, width: float, height: float, background: RGB):
        self.width, self.height = width, height
        self._image = Image.new("RGBA", (math.ceil(width * _K), math.ceil(height * _K)), (*background, 255))
        self._draw = ImageDraw.Draw(self._image)

    @staticmethod
    def _radius(radius: float, w: float, h: float) -> float:
        return min(w, h) / 2 if radius == Shape.FULL else radius

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: RGB | None = None,
        radius: float = 0,
        outline: RGB | None = None,
        outline_width: float = 1,
    ) -> None:
        self._draw.rounded_rectangle(
            (x * _K, y * _K, (x + w) * _K - 1, (y + h) * _K - 1),
            radius=self._radius(radius, w, h) * _K,
            fill=fill,
            outline=outline,
            width=round(outline_width * _K) if outline else 0,
        )

    def stroke(self, points: list[tuple[float, float]], width: float, color: RGB) -> None:
        """
        Draws a smooth line through closely spaced points, with round caps.

        Pillow leaves gaps between the segments of a wide polyline, so the line is filled as one outline polygon. The
        curve has to bend more gently than half the stroke width, or the inner edge folds over itself.
        """
        half = width * _K / 2
        top, bottom = [], []
        for i, (px, py) in enumerate(points):
            (ax, ay), (bx, by) = points[max(i - 1, 0)], points[min(i + 1, len(points) - 1)]
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy) or 1
            nx, ny = -dy / length * half, dx / length * half
            top.append((px * _K + nx, py * _K + ny))
            bottom.append((px * _K - nx, py * _K - ny))
        self._draw.polygon(top + bottom[::-1], fill=color)
        for px, py in (points[0], points[-1]):
            self._draw.ellipse((px * _K - half, py * _K - half, px * _K + half, py * _K + half), fill=color)

    def picture(self, image: Image.Image, x: float, y: float, w: float, h: float, *, radius: float = 0) -> None:
        """Pastes an image cropped to fill the box, with rounded corners when `radius` is set."""
        size = (round(w * _K), round(h * _K))
        fitted = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size[0] - 1, size[1] - 1), radius=self._radius(radius, w, h) * _K, fill=255
        )
        self._image.paste(fitted, (round(x * _K), round(y * _K)), ImageChops.multiply(mask, fitted.getchannel("A")))

    def text(self, x: float, y: float, text: str, style: TextStyle, color: RGB) -> None:
        """Draws one line of text vertically centered in a line box of `style.line_height`, starting at (x, y)."""
        # Every run sits on Roboto's baseline, so fallback fonts with other metrics stay in line
        ascent, descent = _font(fonts.CHAIN[0], style).getmetrics()
        baseline = y * _K + (style.line_height * _K + ascent - descent) / 2
        pen = x * _K
        for name, chunk in fonts.runs(text):
            if name == fonts.EMOJI:
                tile, rise = _emoji_tile(chunk, _emoji_scale(style))
                self._image.alpha_composite(tile, (round(pen), round(baseline - rise)))
            else:
                self._draw.text((pen, baseline), chunk, font=_font(name, style), fill=color, anchor="ls")
            pen += _run_width(name, chunk, style)

    def to_png(self) -> bytes:
        buffer = BytesIO()
        self._image.reduce(_SUPERSAMPLE).save(buffer, "PNG", compress_level=6)
        return buffer.getvalue()
