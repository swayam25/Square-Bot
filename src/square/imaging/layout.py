import math
from abc import ABC, abstractmethod
from PIL import Image
from square.imaging.canvas import Canvas, fit_text, text_width
from square.imaging.theme import RGB
from square.imaging.tokens import Shape, TextStyle
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
        """The height this node needs at `width` dp."""

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
    """Padding around one child, with an optional rounded background and outline."""

    def __init__(
        self,
        child: Node,
        *,
        padding: Padding = 0,
        fill: RGB | None = None,
        outline: RGB | None = None,
        radius: float = 0,
        width: float | None = None,
        height: float | None = None,
        align: Align | Literal["stretch"] = "center",
    ):
        self.child, self.fill, self.outline, self.radius = child, fill, outline, radius
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
        if self.fill or self.outline:
            canvas.rect(x, y, width, height, fill=self.fill, outline=self.outline, radius=self.radius)
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

    `align` places children shorter than the row, and "stretch" makes them all as tall as the tallest.
    """

    def __init__(self, *children: Node | None, gap: float = 0, align: Align | Literal["stretch"] = "center"):
        self.children = [child for child in children if child is not None]
        self.gap, self.align = gap, align

    def _widths(self, width: float) -> list[float]:
        naturals = [child.natural_width() for child in self.children]
        fixed = sum(w for w in naturals if w is not None) + self.gap * max(len(naturals) - 1, 0)
        flexible = naturals.count(None)
        share = max(width - fixed, 0) / flexible if flexible else 0
        return [share if w is None else w for w in naturals]

    def measure(self, width: float) -> float:
        return max((child.measure(w) for child, w in zip(self.children, self._widths(width), strict=True)), default=0)

    def natural_width(self) -> float | None:
        naturals = [child.natural_width() for child in self.children]
        if not naturals or None in naturals:
            return None
        return sum(w for w in naturals if w is not None) + self.gap * (len(naturals) - 1)

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        for child, child_w in zip(self.children, self._widths(width), strict=True):
            child_h = height if self.align == "stretch" else child.measure(child_w)
            offset = 0 if self.align == "stretch" else _offset(self.align, height - child_h)
            child.draw(canvas, x, y + offset, child_w, child_h)
            x += child_w + self.gap


class Bar(Node):
    """
    A horizontal bar split into rounded segments sized by value, with a gap between them, like a segmented progress bar.

    Every non-zero segment is at least as wide as the bar is tall, so a tiny share still shows as a dot. With nothing to
    show it draws `track` across the full width.
    """

    def __init__(self, segments: list[tuple[float, RGB]], track: RGB, *, height: float = 12, gap: float = 4):
        self.segments = [(value, color) for value, color in segments if value > 0]
        self.track, self.height, self.gap = track, height, gap

    def measure(self, width: float) -> float:
        return self.height

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        top = y + (height - self.height) / 2
        if not self.segments:
            canvas.rect(x, top, width, self.height, fill=self.track, radius=Shape.FULL)
            return
        total = sum(value for value, _ in self.segments)
        spare = width - self.gap * (len(self.segments) - 1) - self.height * len(self.segments)
        for value, color in self.segments:
            w = self.height + max(spare, 0) * value / total
            canvas.rect(x, top, w, self.height, fill=color, radius=Shape.FULL)
            x += w + self.gap


class Progress(Node):
    """
    A linear progress indicator: an active line, a gap, then the track with a stop dot at its end.

    `wavy` draws the active part as a wave, the way a playing track looks. The wave eases in over its
    first wavelength, so a bar that has barely started doesn't jump straight to full height.
    """

    def __init__(
        self,
        value: float,
        active: RGB,
        track: RGB,
        *,
        wavy: bool = False,
        thickness: float = 6,
        amplitude: float = 4,
        wavelength: float = 40,
        gap: float = 6,
    ):
        self.value = min(max(value, 0), 1)
        self.active, self.track, self.wavy = active, track, wavy
        self.thickness, self.amplitude, self.wavelength, self.gap = thickness, amplitude, wavelength, gap

    def measure(self, width: float) -> float:
        return self.thickness + (self.amplitude * 2 if self.wavy else 0)

    def draw(self, canvas: Canvas, x: float, y: float, width: float, height: float) -> None:
        mid, t = y + height / 2, self.thickness
        # Caps are round, so each line's ends sit half a thickness inside the space it covers
        end = x + t / 2 + (width - t) * self.value
        if self.value > 0:
            if self.wavy:
                span = end - x - t / 2
                steps = max(int(span), 1)
                points = []
                for i in range(steps + 1):
                    px = x + t / 2 + span * i / steps
                    ease = min((px - x) / self.wavelength, 1)
                    points.append((px, mid + self.amplitude * ease * math.sin((px - x) * math.tau / self.wavelength)))
                canvas.stroke(points, t, self.active)
            else:
                canvas.rect(x, mid - t / 2, end - x + t / 2, t, fill=self.active, radius=Shape.FULL)
        if self.value >= 1:
            return
        start = end + t / 2 + self.gap if self.value > 0 else x
        if start < x + width - t:
            canvas.rect(start, mid - t / 2, x + width - start, t, fill=self.track, radius=Shape.FULL)
        canvas.rect(x + width - t, mid - t / 2, t, t, fill=self.active, radius=Shape.FULL)


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
