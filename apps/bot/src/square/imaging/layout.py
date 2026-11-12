import math
from abc import ABC, abstractmethod
from PIL import Image
from square.imaging.canvas import Canvas, Corners, baseline, fit_text, text_width
from square.imaging.theme import RGB
from square.imaging.tokens import Radius, TextStyle
from typing import Literal

type Align = Literal["start", "center", "end"]
type Padding = float | tuple[float, float] | tuple[float, float, float, float]


def _offset(align: Align, free: float) -> float:
    return {"start": 0, "center": free / 2, "end": free}[align]


class Node(ABC):
    @abstractmethod
    def measure(self, width: float) -> float: ...

    @abstractmethod
    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None: ...

    def natural_width(self) -> float | None:
        return None


class Text(Node):
    def __init__(self, text: str, style: TextStyle, color: RGB, *, align: Align = "start"):
        self.text, self.style, self.color, self.align = text, style, color, align

    def measure(self, width: float) -> float:
        return self.style.line_height

    def natural_width(self) -> float:
        return text_width(self.text, self.style)

    def baseline(self) -> float:
        return baseline(self.style)

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        text = fit_text(self.text, self.style, width)
        free = width - text_width(text, self.style)
        canvas.text(
            x + _offset(self.align, free), y + (height - self.style.line_height) / 2, text, self.style, self.color
        )


class Picture(Node):
    def __init__(self, image: Image.Image, width: float, height: float | None = None, *, radius: float = 0):
        self.image, self.width, self.height, self.radius = image, width, height or width, radius

    def measure(self, width: float) -> float:
        return self.height

    def natural_width(self) -> float:
        return self.width

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        canvas.picture(self.image, x, y + (height - self.height) / 2, self.width, self.height, radius=self.radius)


class Stack(Node):
    def __init__(self, base: Node, *layers: tuple[Node, float, float]):
        self.base, self.layers = base, layers

    def measure(self, width: float) -> float:
        return self.base.measure(width)

    def natural_width(self) -> float | None:
        return self.base.natural_width()

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        base_w = self.base.natural_width() or width
        base_h = self.base.measure(base_w)
        top = y + (height - base_h) / 2
        self.base.draw(canvas, x, top, base_w, base_h)
        for layer, dx, dy in self.layers:
            layer_w = layer.natural_width() or base_w
            layer.draw(canvas, x + dx, top + dy, layer_w, layer.measure(layer_w))


class Spacer(Node):
    def __init__(self, height: float = 0, width: float | None = None):
        self.height, self.width = height, width

    def measure(self, width: float) -> float:
        return self.height

    def natural_width(self) -> float | None:
        return self.width

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        pass


class Box(Node):
    def __init__(
        self,
        child: Node,
        *,
        padding: Padding = 0,
        fill: RGB | None = None,
        radius: Corners = 0,
        width: float | None = None,
        height: float | None = None,
        align: Align | Literal["stretch"] = "center",
    ):
        self.child, self.fill, self.radius = child, fill, radius
        self.width, self.height, self.align = width, height, align
        match padding:
            case int() | float():
                self.pad = (padding,) * 4
            case (px, py):
                self.pad = (py, px, py, px)
            case (top, right, bottom, left):
                self.pad = (top, right, bottom, left)

    def _inner(self, width: float) -> float:
        return (self.width or width) - self.pad[1] - self.pad[3]

    def measure(self, width: float) -> float:
        return self.height or self.pad[0] + self.child.measure(self._inner(width)) + self.pad[2]

    def natural_width(self) -> float | None:
        if self.width is not None:
            return self.width
        child = self.child.natural_width()
        return None if child is None else child + self.pad[1] + self.pad[3]

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        if self.fill:
            canvas.rect(x, y, width, height, fill=self.fill, radius=self.radius)
        inner_w = width - self.pad[1] - self.pad[3]
        inner_h = height - self.pad[0] - self.pad[2]
        if self.align == "stretch":
            self.child.draw(canvas, x + self.pad[3], y + self.pad[0], inner_w, inner_h)
            return
        child_h = self.child.measure(inner_w)
        top = y + self.pad[0] + _offset(self.align, inner_h - child_h)
        self.child.draw(canvas, x + self.pad[3], top, inner_w, child_h)


class Column(Node):
    def __init__(self, *children: Node | None, gap: float = 0, align: Align | Literal["stretch"] = "stretch"):
        self.children = [child for child in children if child is not None]
        self.gap, self.align = gap, align

    def _width_of(self, child: Node, width: float) -> float:
        natural = child.natural_width()
        return width if self.align == "stretch" or natural is None else min(natural, width)

    def measure(self, width: float) -> float:
        heights = [
            child.measure(self._width_of(child, width)) for child in self.children if not isinstance(child, Fill)
        ]
        return sum(heights) + self.gap * max(len(heights) - 1, 0)

    def natural_width(self) -> float | None:
        widths = [child.natural_width() for child in self.children]
        return None if not widths or None in widths else max(w for w in widths if w is not None)

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        fills = sum(isinstance(child, Fill) for child in self.children)
        spare = max(height - self.measure(width), 0) / fills if fills else 0
        for child in self.children:
            if isinstance(child, Fill):
                y += spare
                continue
            child_w = self._width_of(child, width)
            child_h = child.measure(child_w)
            offset = 0 if self.align == "stretch" else _offset(self.align, width - child_w)
            child.draw(canvas, x + offset, y, child_w, child_h)
            y += child_h + self.gap


class Row(Node):
    def __init__(
        self, *children: Node | None, gap: float = 0, align: Align | Literal["stretch", "baseline"] = "center"
    ):
        self.children = [child for child in children if child is not None]
        self.gap, self.align = gap, align

    def _widths(self, width: float) -> list[float]:
        naturals = [child.natural_width() for child in self.children]
        fixed = sum(w for w in naturals if w is not None) + self.gap * max(len(naturals) - 1, 0)
        if fixed > width and any(w is not None for w in naturals):
            widest = max((i for i, w in enumerate(naturals) if w is not None), key=lambda i: naturals[i])
            naturals[widest] = max(naturals[widest] - (fixed - width), 0)
            fixed = width
        flexible = naturals.count(None)
        share = max(width - fixed, 0) / flexible if flexible else 0
        return [share if w is None else w for w in naturals]

    def _drops(self) -> list[float]:
        lines = [child.baseline() if isinstance(child, Text) else 0 for child in self.children]
        return [max(lines, default=0) - line for line in lines]

    def measure(self, width: float) -> float:
        heights = [child.measure(w) for child, w in zip(self.children, self._widths(width), strict=True)]
        if self.align == "baseline":
            heights = [h + drop for h, drop in zip(heights, self._drops(), strict=True)]
        return max(heights, default=0)

    def natural_width(self) -> float | None:
        naturals = [child.natural_width() for child in self.children]
        if not naturals or None in naturals:
            return None
        return sum(w for w in naturals if w is not None) + self.gap * (len(naturals) - 1)

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        drops = self._drops() if self.align == "baseline" else [0.0] * len(self.children)
        for child, child_w, drop in zip(self.children, self._widths(width), drops, strict=True):
            child_h = height if self.align == "stretch" else child.measure(child_w)
            if self.align in ("stretch", "baseline"):
                offset = drop
            else:
                offset = _offset(self.align, height - child_h)
            child.draw(canvas, x, y + offset, child_w, child_h)
            x += child_w + self.gap


class SplitBar(Node):
    def __init__(
        self,
        segments: list[tuple[float, RGB]],
        track: RGB,
        *,
        label: Text | None = None,
        height: float = 40,
        padding: float = 4,
        gap: float = 4,
        min_width: float = 24,
        inner_radius: float = Radius.LG,
    ):
        self.segments = [(value, color) for value, color in segments if value > 0]
        self.track, self.label, self.height, self.padding, self.gap = track, label, height, padding, gap
        self.min_width, self.inner_radius = min_width, inner_radius

    def measure(self, width: float) -> float:
        return self.height

    def _widths(self, width: float) -> list[float]:
        values = [value for value, _ in self.segments]
        widths = [0.0] * len(values)
        clamped: set[int] = set()
        while True:
            free = width - self.min_width * len(clamped)
            total = sum(v for i, v in enumerate(values) if i not in clamped)
            for i, value in enumerate(values):
                widths[i] = self.min_width if i in clamped else free * value / total
            small = {i for i, w in enumerate(widths) if w < self.min_width and i not in clamped}
            if not small:
                return widths
            clamped |= small

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        top = y + (height - self.height) / 2
        canvas.rect(x, top, width, self.height, fill=self.track, radius=Radius.FULL)
        if not self.segments:
            return
        inner_h = self.height - self.padding * 2
        outer = inner_h / 2
        last = len(self.segments) - 1
        pen = x + self.padding
        widths = self._widths(width - self.padding * 2 - self.gap * last)
        for i, ((_, color), w) in enumerate(zip(self.segments, widths, strict=True)):
            left = outer if i == 0 else self.inner_radius
            right = outer if i == last else self.inner_radius
            canvas.rect(pen, top + self.padding, w, inner_h, fill=color, radius=(left, right, right, left))
            if i == 0 and self.label is not None and self.label.natural_width() + outer * 2 <= w:
                self.label.draw(canvas, pen + outer, top + self.padding, w - outer * 2, inner_h)
            pen += w + self.gap


class Progress(Node):
    def __init__(
        self,
        value: float,
        active: RGB,
        track: RGB,
        *,
        wavy: bool = False,
        thickness: float = 5,
        amplitude: float = 3,
        wavelength: float = 32,
        gap: float = 12,
        height: float = 16,
    ):
        self.value = min(max(value, 0), 1)
        self.active, self.track, self.wavy = active, track, wavy
        self.thickness, self.amplitude, self.wavelength = thickness, amplitude, wavelength
        self.gap, self.height = gap, height

    def measure(self, width: float) -> float:
        return self.height

    def _wave(self, origin: float, start: float, end: float, mid: float) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        at = start
        while at < end + 2:
            point = min(at, end)
            points.append((point, mid - self.amplitude * math.sin((point - origin) / self.wavelength * 2 * math.pi)))
            at += 2
        return points

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        mid, t = y + height / 2, self.thickness
        start = x + 3
        played = start + self.value * (width - 6)
        if self.wavy and played > start:
            canvas.stroke(self._wave(x, start, played, mid), t, self.active)
        else:
            canvas.rect(start - t / 2, mid - t / 2, played - start + t, t, fill=self.active, radius=Radius.FULL)
        if self.value >= 1:
            return
        track_end = x + width - self.gap
        track_start = played + self.gap
        if track_start < track_end:
            canvas.rect(
                track_start - t / 2, mid - t / 2, track_end - track_start + t, t, fill=self.track, radius=Radius.FULL
            )
        canvas.rect(x + width - 3 - t / 2, mid - t / 2, t, t, fill=self.active, radius=Radius.FULL)


class Fill(Node):
    def measure(self, width: float) -> float:
        return 0

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        pass


class Expand(Node):
    def __init__(self, child: Node):
        self.child = child

    def measure(self, width: float) -> float:
        return self.child.measure(width)

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        self.child.draw(canvas, x, y, width, height)
