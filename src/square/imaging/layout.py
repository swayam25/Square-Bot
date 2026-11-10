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
    """
    One piece of an image. A parent decides each child's width, the child reports the height it needs.

    Nodes with a natural width (text, avatars, fixed boxes) report it from `natural_width`, so rows can size them
    before sharing what's left between the flexible ones.
    """

    @abstractmethod
    def measure(self, width: float) -> float:
        """The height this node needs at `width` px."""

    @abstractmethod
    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        """Draws into the box. `height` is at least what `measure` returned, more when a parent stretches it."""

    def natural_width(self) -> float | None:
        """The width this node wants, or None to take whatever space it's given."""
        return None


class Text(Node):
    """A single line of text, cut with an ellipsis when it doesn't fit."""

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
    """An image cropped to a fixed size."""

    def __init__(self, image: Image.Image, width: float, height: float | None = None, *, radius: float = 0):
        self.image, self.width, self.height, self.radius = image, width, height or width, radius

    def measure(self, width: float) -> float:
        return self.height

    def natural_width(self) -> float:
        return self.width

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        canvas.picture(self.image, x, y + (height - self.height) / 2, self.width, self.height, radius=self.radius)


class Stack(Node):
    """
    A node with others drawn over it, each at an offset from its top-left corner, like a badge on an avatar.

    Takes the base's size, so the layers can hang outside it without moving anything around it.
    """

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
    """Empty space. With no width it pushes its row siblings apart."""

    def __init__(self, height: float = 0, width: float | None = None):
        self.height, self.width = height, width

    def measure(self, width: float) -> float:
        return self.height

    def natural_width(self) -> float | None:
        return self.width

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        pass


class Box(Node):
    """Padding around one child, with an optional rounded background."""

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
    """Children stacked top to bottom. `align` places children narrower than the column."""

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
            if isinstance(child, Fill):  # No gap of its own, so a column with nothing to fill looks unchanged
                y += spare
                continue
            child_w = self._width_of(child, width)
            child_h = child.measure(child_w)
            offset = 0 if self.align == "stretch" else _offset(self.align, width - child_w)
            child.draw(canvas, x + offset, y, child_w, child_h)
            y += child_h + self.gap


class Row(Node):
    """
    Children left to right. Ones with a natural width get it, the rest split the remaining space evenly.

    `align` places children shorter than the row, "stretch" makes them all as tall as the tallest, and "baseline"
    lines up the text children's baselines like CSS `items-baseline`.
    """

    def __init__(
        self, *children: Node | None, gap: float = 0, align: Align | Literal["stretch", "baseline"] = "center"
    ):
        self.children = [child for child in children if child is not None]
        self.gap, self.align = gap, align

    def _widths(self, width: float) -> list[float]:
        naturals = [child.natural_width() for child in self.children]
        fixed = sum(w for w in naturals if w is not None) + self.gap * max(len(naturals) - 1, 0)
        flexible = naturals.count(None)
        share = max(width - fixed, 0) / flexible if flexible else 0
        return [share if w is None else w for w in naturals]

    def _drops(self) -> list[float]:
        """For "baseline": how far each child moves down so every baseline meets the lowest one."""
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
    """
    A thick pill split into parts sized by value, like a stats breakdown: `h-10 p-1` with `gap-1` between parts.

    Parts keep a minimum width so a tiny share still shows. The outer ends are fully round and the inner corners
    `rounded-lg`, so neighbouring parts read as one bar. `label` is written inside the first part when it fits.
    """

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
        """Shares of `width` by value, like CSS flex-grow with a min-width: clamped parts drop out and the rest re-split."""
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
    """
    A track's progress: the played part, a gap, the rest of the track, and a dot marking the end.

    `wavy` draws the played part as a wave, the way a playing track looks, and a flat line when paused. At `value` 1
    (a live stream) the wave runs the full width with no track. The geometry matches the website's SVG: a stroke of
    `thickness`, a wave of quadratic arcs `wavelength` long and `amplitude` high.
    """

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

    def _wave(self, start: float, end: float, mid: float) -> list[tuple[float, float]]:
        """Alternating quadratic arcs from `start` to `end`, first bending up, cut off mid-arc at `end`."""
        half = self.wavelength / 2
        points: list[tuple[float, float]] = []
        sign, x0 = -1, start
        while x0 < end:
            span = min(half, end - x0)
            steps = max(int(span), 1)
            for i in range(steps + 1):
                t = span / half * i / steps
                # The control point sits mid-arc, so x runs straight and y is a parabola peaking at `amplitude`
                points.append((x0 + half * t, mid + sign * 2 * self.amplitude * 2 * t * (1 - t)))
            sign, x0 = -sign, x0 + half
        return points

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        mid, t = y + height / 2, self.thickness
        start = x + t / 2 + 0.5
        played = max(x + width * self.value, start) if self.value < 1 else x + width - t / 2 - 0.5
        if self.value > 0:
            if self.wavy:
                canvas.stroke(self._wave(start, played, mid), t, self.active)
            else:
                canvas.rect(start - t / 2, mid - t / 2, played - start + t, t, fill=self.active, radius=Radius.FULL)
        if self.value >= 1:
            return
        track_end = x + width - self.gap
        track_start = played + self.gap if self.value > 0 else start
        if track_start < track_end:
            canvas.rect(
                track_start - t / 2, mid - t / 2, track_end - track_start + t, t, fill=self.track, radius=Radius.FULL
            )
        canvas.rect(x + width - 4 - t / 2, mid - t / 2, t, t, fill=self.active, radius=Radius.FULL)


class Fill(Node):
    """Empty space that takes whatever height its column has left over, so content after it sits at the bottom."""

    def measure(self, width: float) -> float:
        return 0

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        pass


class Expand(Node):
    """Drops a child's natural width so a row gives it a share of the free space. Equal-width columns use this."""

    def __init__(self, child: Node):
        self.child = child

    def measure(self, width: float) -> float:
        return self.child.measure(width)

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        self.child.draw(canvas, x, y, width, height)
