import math
from io import BytesIO
from PIL import Image, ImageChops, ImageDraw, ImageOps
from square.imaging import fonts
from square.imaging.theme import RGB
from square.imaging.tokens import CORNER_SHAPE, Radius, TextStyle
from typing import Literal

SCALE = 2  # Output pixels per px, so images stay sharp on high-DPI screens
# Pillow's shapes have no antialiasing, so everything is drawn this many times larger and downsampled once
_SUPERSAMPLE = 2
_K = SCALE * _SUPERSAMPLE
_SHAPE_AA = 4

_ELLIPSIS = "…"

type Corners = float | tuple[float, float, float, float]


def _font(name: str, style: TextStyle):
    return fonts.font(name, round(style.size * _K), style.weight)


def _run_width(name: str, chunk: str, style: TextStyle) -> float:
    spacing = style.tracking * style.size * _K * len(chunk)
    return _font(name, style).getlength(chunk) + spacing


def text_width(text: str, style: TextStyle) -> float:
    return sum(_run_width(name, chunk, style) for name, chunk in fonts.runs(text, style.family)) / _K


def fit_text(text: str, style: TextStyle, max_width: float) -> str:
    if text_width(text, style) <= max_width:
        return text
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if text_width(text[:mid].rstrip() + _ELLIPSIS, style) <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + _ELLIPSIS


def baseline(style: TextStyle) -> float:
    ascent, descent = _font(fonts.CHAINS[style.family][0], style).getmetrics()
    return (style.line_height * _K + ascent - descent) / 2 / _K


def open_image(data: bytes | None) -> Image.Image | None:
    if not data:
        return None
    try:
        with Image.open(BytesIO(data)) as image:
            return image.convert("RGBA")
    except OSError, Image.DecompressionBombError:
        return None


def _corners(radius: Corners, w: float, h: float) -> tuple[tuple[float, ...], tuple[float, ...]]:
    # CSS superellipse(K) is the curve |x|^n + |y|^n = 1 with n = 2^K. Radius.FULL corners stay circles (n = 2)
    full = min(w, h) / 2
    raw = (radius,) * 4 if isinstance(radius, int | float) else radius
    radii = tuple(full if r == Radius.FULL else min(r, full) for r in raw)
    exponents = tuple(2.0 if r == Radius.FULL else 2.0**CORNER_SHAPE for r in raw)
    return radii, exponents


def _outline(
    x0: float, y0: float, x1: float, y1: float, radii: tuple[float, ...], exponents: tuple[float, ...]
) -> list[tuple[float, float]]:
    tl, tr, br, bl = radii
    etl, etr, ebr, ebl = exponents
    points: list[tuple[float, float]] = []
    for cx, cy, r, n, start in (
        (x1 - tr, y0 + tr, tr, etr, -90),
        (x1 - br, y1 - br, br, ebr, 0),
        (x0 + bl, y1 - bl, bl, ebl, 90),
        (x0 + tl, y0 + tl, tl, etl, 180),
    ):
        steps = max(int(r / 2), 1) if r else 1
        for i in range(steps + 1):
            angle = math.radians(start + 90 * i / steps)
            dx, dy = math.cos(angle), math.sin(angle)
            points.append(
                (cx + r * math.copysign(abs(dx) ** (2 / n), dx), cy + r * math.copysign(abs(dy) ** (2 / n), dy))
            )
    return points


def _mask(size: tuple[int, int], radii: tuple[float, ...], exponents: tuple[float, ...]) -> Image.Image:
    w, h = size
    big = Image.new("L", (w * _SHAPE_AA, h * _SHAPE_AA), 0)
    outline = _outline(0, 0, w * _SHAPE_AA - 1, h * _SHAPE_AA - 1, tuple(r * _SHAPE_AA for r in radii), exponents)
    ImageDraw.Draw(big).polygon(outline, fill=255)
    return big.resize(size, Image.Resampling.BOX)


def _fade(size: tuple[int, int], side: Literal["left", "right"], share: float = 0.6) -> Image.Image:
    """An alpha ramp that eases the picture out over the `share` of its width nearest `side`."""
    w, h = size
    start = w * (1 - share)
    ramp = []
    for i in range(w):
        t = min(max((i - start) / (w - start), 0), 1)
        ramp.append(round(255 * (1 - t * t * (3 - 2 * t))))
    if side == "left":
        ramp.reverse()
    strip = Image.new("L", (w, 1))
    strip.putdata(ramp)
    return strip.resize((w, h), Image.Resampling.NEAREST)


class Canvas:
    def __init__(self, width: float, height: float, background: RGB | None = None):
        self.width, self.height = width, height
        fill = (*background, 255) if background else (0, 0, 0, 0)
        self._image = Image.new("RGBA", (math.ceil(width * _K), math.ceil(height * _K)), fill)
        self._draw = ImageDraw.Draw(self._image)

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: RGB | None = None,
        radius: Corners = 0,
    ) -> None:
        if not fill:
            return
        radii, exponents = _corners(radius, w, h)
        x0, y0 = round(x * _K), round(y * _K)
        size = (round((x + w) * _K) - x0, round((y + h) * _K) - y0)
        if size[0] <= 0 or size[1] <= 0:
            return
        if not any(radii):
            self._draw.rectangle((x0, y0, x0 + size[0] - 1, y0 + size[1] - 1), fill=fill)
            return
        mask = _mask(size, tuple(r * _K for r in radii), exponents)
        self._image.paste((*fill, 255), (x0, y0, x0 + size[0], y0 + size[1]), mask)

    def stroke(self, points: list[tuple[float, float]], width: float, color: RGB) -> None:
        """
        Draws a smooth line through closely spaced points, with round caps.

        Pillow leaves gaps between the segments of a wide polyline, so the line is filled as one outline polygon. The
        curve has to bend more gently than half the stroke width, or the inner edge folds over itself.
        """
        a = _K * _SHAPE_AA
        half = width * a / 2
        x0 = math.floor(min(px for px, _ in points) * _K - width * _K)
        y0 = math.floor(min(py for _, py in points) * _K - width * _K)
        x1 = math.ceil(max(px for px, _ in points) * _K + width * _K)
        y1 = math.ceil(max(py for _, py in points) * _K + width * _K)
        big = Image.new("L", ((x1 - x0) * _SHAPE_AA, (y1 - y0) * _SHAPE_AA), 0)
        draw = ImageDraw.Draw(big)
        local = [(px * a - x0 * _SHAPE_AA, py * a - y0 * _SHAPE_AA) for px, py in points]
        top, bottom = [], []
        for i, (px, py) in enumerate(local):
            (ax, ay), (bx, by) = local[max(i - 1, 0)], local[min(i + 1, len(local) - 1)]
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy) or 1
            nx, ny = -dy / length * half, dx / length * half
            top.append((px + nx, py + ny))
            bottom.append((px - nx, py - ny))
        draw.polygon(top + bottom[::-1], fill=255)
        for px, py in (local[0], local[-1]):
            draw.ellipse((px - half, py - half, px + half, py + half), fill=255)
        mask = big.resize((x1 - x0, y1 - y0), Image.Resampling.BOX)
        self._image.paste((*color, 255), (x0, y0, x1, y1), mask)

    def picture(
        self,
        image: Image.Image,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        radius: float = 0,
        fade: Literal["left", "right"] | None = None,
    ) -> None:
        size = (round(w * _K), round(h * _K))
        fitted = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        radii, exponents = _corners(radius, w, h)
        mask = _mask(size, tuple(r * _K for r in radii), exponents)
        if fade:
            mask = ImageChops.multiply(mask, _fade(size, fade))
        self._image.alpha_composite(
            Image.composite(fitted, Image.new("RGBA", size), ImageChops.multiply(mask, fitted.getchannel("A"))),
            (round(x * _K), round(y * _K)),
        )

    def text(self, x: float, y: float, text: str, style: TextStyle, color: RGB) -> None:
        line = (y + baseline(style)) * _K
        spacing = style.tracking * style.size * _K
        pen = x * _K
        for name, chunk in fonts.runs(text, style.family):
            if name == fonts.EMOJI:
                # Whole run at once, so the font's ligatures can join flags and ZWJ sequences
                self._draw.text((pen, line), chunk, font=_font(name, style), embedded_color=True, anchor="ls")
                pen += _run_width(name, chunk, style)
            elif spacing:
                for char in chunk:
                    self._draw.text((pen, line), char, font=_font(name, style), fill=color, anchor="ls")
                    pen += _run_width(name, char, style)
            else:
                self._draw.text((pen, line), chunk, font=_font(name, style), fill=color, anchor="ls")
                pen += _run_width(name, chunk, style)

    def to_png(self) -> bytes:
        buffer = BytesIO()
        self._image.reduce(_SUPERSAMPLE).save(buffer, "PNG", compress_level=6)
        return buffer.getvalue()
