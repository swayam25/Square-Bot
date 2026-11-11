"""
Card images in the same design as Square's website.

Tailwind's `mist` greys and type scale, the accent and status colors from `config.toml`, Saira, Geist and JetBrains
Mono, with Twemoji for emoji.

A template is a function `(Kit, data) -> Node` that builds a layout tree from plain data. Async work (avatars, DB)
happens before rendering, so templates stay pure and can be previewed with fake data, see `python -m square.imaging`.

Adding a template: write its `build` in `templates/`, then add its sample data and a `PREVIEWS` entry in
`templates/__init__.py`.
"""

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


def _root[T](template: Template[T], data: T, accent: int | None) -> Box:
    ui = Kit(theme.theme(accent))
    # The card stretches its content, so a `layout.Fill` in the template can take the extra height of a taller canvas
    return ui.card(template(ui, data))


def measure[T](template: Template[T], data: T, *, width: float = WIDTH) -> float:
    """
    How tall a template renders with this data, in px, without drawing it.

    Pages of one image can measure their fullest page and render every page at that `height`, so the image keeps
    its size as people flip through it.
    """
    return _root(template, data, None).measure(width)


async def tallest[T](template: Template[T], datas: list[T], *, width: float = WIDTH) -> float:
    """The height of the tallest of several layouts, measured off the event loop. Pass it to `render` as `height`."""

    def measure_all() -> float:
        return max((measure(template, data, width=width) for data in datas), default=0)

    async with _renders:  # Measuring reads the shared fonts too
        return await asyncio.to_thread(measure_all)


def render_png[T](
    template: Template[T], data: T, *, width: float = WIDTH, height: float = 0, accent: int | None = None
) -> bytes:
    """
    Renders a template to PNG bytes. Blocking, so call `render` from async code.

    Args:
        template (:class:`Template`): Builds the layout from `data`.
        data (T): Whatever the template takes.
        width (float): The image width in px. The output is `canvas.SCALE` times wider in pixels.
        height (float): The minimum image height in px. Taller content still grows the image.
        accent (int | None): An accent color to preview instead of the one in `config.toml`.
    """
    root = _root(template, data, accent)
    height = max(root.measure(width), height)
    canvas = Canvas(width, height)
    root.draw(canvas, 0, 0, width, height)
    return canvas.to_png()


async def render[T](
    template: Template[T], data: T, *, filename: str, width: float = WIDTH, height: float = 0
) -> discord.File:
    """
    Renders a template off the event loop, ready to attach with `attachment://<filename>`.

    Args:
        template (:class:`Template`): Builds the layout from `data`.
        data (T): Whatever the template takes.
        filename (str): The attachment's name, ending in `.png`.
        width (float): The image width in px.
        height (float): The minimum image height in px, see `measure`.
    """
    async with _renders:
        png = await asyncio.to_thread(render_png, template, data, width=width, height=height)
    return discord.File(BytesIO(png), filename=filename)
