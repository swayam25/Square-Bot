import math
from io import BytesIO
from PIL import Image, ImageChops, ImageDraw, ImageOps
from square.imaging import fonts
from square.imaging.theme import RGB
from square.imaging.tokens import Radius, TextStyle

SCALE = 2  # Output pixels per px, so images stay sharp on high-DPI screens
# Pillow's shapes have no antialiasing, so everything is drawn this many times larger and downsampled once
_SUPERSAMPLE = 2
_K = SCALE * _SUPERSAMPLE

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


def _corner_radii(radius: Corners, w: float, h: float) -> tuple[float, float, float, float]:
    full = min(w, h) / 2
    tl, tr, br, bl = (
        full if r == Radius.FULL else min(r, full)
        for r in ((radius,) * 4 if isinstance(radius, int | float) else radius)
    )
    return tl, tr, br, bl


def _rounded_outline(x0: float, y0: float, x1: float, y1: float, radii: tuple[float, ...]) -> list[tuple[float, float]]:
    tl, tr, br, bl = radii
    points: list[tuple[float, float]] = []
    for cx, cy, r, start in (
        (x1 - tr, y0 + tr, tr, -90),
        (x1 - br, y1 - br, br, 0),
        (x0 + bl, y1 - bl, bl, 90),
        (x0 + tl, y0 + tl, tl, 180),
    ):
        steps = max(int(r / 2), 1) if r else 1
        for i in range(steps + 1):
            angle = math.radians(start + 90 * i / steps)
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


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
        radii = _corner_radii(radius, w, h)
        box = (x * _K, y * _K, (x + w) * _K - 1, (y + h) * _K - 1)
        if len(set(radii)) == 1:
            self._draw.rounded_rectangle(box, radius=radii[0] * _K, fill=fill)
            return
        if fill:
            self._draw.polygon(_rounded_outline(*box, tuple(r * _K for r in radii)), fill=fill)

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
        size = (round(w * _K), round(h * _K))
        fitted = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size[0] - 1, size[1] - 1), radius=_corner_radii(radius, w, h)[0] * _K, fill=255
        )
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
