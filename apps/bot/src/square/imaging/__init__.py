import asyncio
import discord
from collections.abc import Callable
from io import BytesIO
from square.imaging import theme
from square.imaging.canvas import Canvas
from square.imaging.components import Kit
from square.imaging.layout import Box, Node

type Template[T] = Callable[[Kit, T], Node]

WIDTH = 720
# One render at a time, since the cached FreeType faces aren't thread-safe. Kept across `importlib.reload` so a
# render already running still holds it.
_renders: asyncio.Semaphore = globals().get("_renders") or asyncio.Semaphore(1)


def _root[T](template: Template[T], data: T, accent: int | None, bare: bool = False) -> Box:
    ui = Kit(theme.theme(accent))
    node = template(ui, data)
    return Box(node, fill=ui.theme.bg, align="stretch") if bare else ui.card(node)


def measure[T](template: Template[T], data: T, *, width: float = WIDTH) -> float:
    return _root(template, data, None).measure(width)


async def tallest[T](template: Template[T], datas: list[T], *, width: float = WIDTH) -> float:

    def measure_all() -> float:
        return max((measure(template, data, width=width) for data in datas), default=0)

    async with _renders:  # Measuring reads the shared fonts too
        return await asyncio.to_thread(measure_all)


def _draw[T](template: Template[T], data: T, *, width: float, height: float, accent: int | None, bare: bool) -> Canvas:
    root = _root(template, data, accent, bare)
    height = max(root.measure(width), height)
    canvas = Canvas(width, height)
    root.draw(canvas, 0, 0, width, height)
    return canvas


def render_png[T](
    template: Template[T],
    data: T,
    *,
    width: float = WIDTH,
    height: float = 0,
    accent: int | None = None,
    bare: bool = False,
) -> bytes:
    """`bare` skips the card's padding, for templates that run to the edges."""
    return _draw(template, data, width=width, height=height, accent=accent, bare=bare).to_png()


async def render[T](
    template: Template[T], data: T, *, filename: str, width: float = WIDTH, height: float = 0, bare: bool = False
) -> discord.File:
    async with _renders:
        png = await asyncio.to_thread(render_png, template, data, width=width, height=height, bare=bare)
    return discord.File(BytesIO(png), filename=filename)
