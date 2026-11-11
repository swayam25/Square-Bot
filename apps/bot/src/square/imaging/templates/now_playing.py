import msgspec
from PIL import Image
from square.imaging.canvas import open_image
from square.imaging.components import Kit
from square.imaging.layout import Box, Column, Expand, Fill, Node, Picture, Row, Spacer
from square.imaging.tokens import Radius, Type

_ARTWORK = 160
_COVER = 32
_FILTERS_SHOWN = 2
# Lavalink source names with a brand logo in `emojis/`. Others get a music note
_LOGOS = {"youtube", "spotify", "soundcloud"}
_LABELS = {
    "youtube": "YouTube",
    "spotify": "Spotify",
    "soundcloud": "SoundCloud",
    "http": "Link",
    "local": "Local file",
    "twitch": "Twitch",
}


def source_label(source: str) -> str:
    """How a Lavalink source name reads, e.g. "youtube" -> "YouTube"."""
    return _LABELS.get(source, source.title() or "Music")


class NowPlaying(msgspec.Struct, frozen=True):
    title: str
    author: str
    source: str
    artwork: bytes | None
    requester: str | None
    requester_avatar: bytes | None
    progress: float
    elapsed: str
    duration: str
    stream: bool
    paused: bool
    volume: int
    loop: str
    shuffle: bool
    autoplay: bool
    filters: list[str]
    up_next: str | None
    up_next_artwork: bytes | None
    queued: int


def _trim_letterbox(image: Image.Image) -> Image.Image:
    """Cuts the black bars YouTube bakes into 4:3 thumbnails of 16:9 videos, so they don't end up in the square crop."""
    dark = image.convert("L").point(lambda value: 255 if value > 16 else 0)
    if not (box := dark.getbbox()):
        return image
    left, top, right, bottom = box
    # Only full-width bars at the top and bottom count, so dark artwork with a bright center keeps its edges
    if left > 2 or right < image.width - 2 or top > image.height // 4 or image.height - bottom > image.height // 4:
        return image
    return image.crop((0, top, image.width, bottom))


def _artwork(ui: Kit, data: bytes | None, size: float, radius: float) -> Node:
    if image := open_image(data):
        return Picture(_trim_letterbox(image), size, radius=radius)
    t = ui.theme
    return Box(ui.icon("music", size * 0.4, t.accent), fill=t.surface_2, radius=radius, width=size, height=size)


def _up_next(ui: Kit, data: NowPlaying) -> Box:
    """The next track on a `surface-2` tile, `h-12 rounded-2xl`, under a mono eyebrow."""
    eyebrow = f"Up next · {data.queued} queued" if data.queued else "Up next"
    title = ui.text(data.up_next, Type.SM_MEDIUM) if data.up_next else ui.muted("Nothing queued", Type.SM_MEDIUM)
    cover = _artwork(ui, data.up_next_artwork, _COVER, Radius.LG) if data.up_next else None
    return Box(
        Row(cover, Column(ui.eyebrow(eyebrow), title), gap=8),
        padding=(0, 16, 0, 8 if cover else 16),
        fill=ui.theme.surface_2,
        radius=Radius.XL2,
        height=48,
    )


def build(ui: Kit, data: NowPlaying) -> Node:
    """The current track: artwork, title and requester, a wavy progress bar, the player's settings and what's next."""
    if data.stream:
        state = ui.chip("Live", "danger", icon="live")
    elif data.paused:
        state = ui.chip("Paused", "warning", icon="play")
    else:
        state = ui.chip("Playing", "accent", icon="pause")
    if data.source in _LOGOS:
        source = ui.chip(source_label(data.source), icon=data.source, tint=False)
    else:
        source = ui.chip(source_label(data.source), icon="music")
    requester = (
        Row(
            ui.avatar(open_image(data.requester_avatar), data.requester, 24),
            Expand(ui.muted(f"Requested by {data.requester}")),
            gap=8,
        )
        if data.requester
        else None
    )
    track = Row(
        _artwork(ui, data.artwork, _ARTWORK, Radius.XL2),
        Expand(
            Column(
                Row(state, source, gap=8),
                Spacer(16),
                ui.text(data.title, Type.DISPLAY_2XL),
                Spacer(2),
                ui.muted(data.author, Type.BASE),
                Fill(),
                requester,
            )
        ),
        gap=24,
        align="stretch",
    )
    times = Row(
        ui.muted(data.elapsed, Type.MONO_XS),
        Spacer(),
        ui.muted("Live" if data.stream else data.duration, Type.MONO_XS),
    )
    # A paused track lies flat
    progress = Column(ui.progress(1 if data.stream else data.progress, wavy=not data.paused), times, gap=8)

    looping = data.loop != "Disabled"
    filters = " · ".join(data.filters[:_FILTERS_SHOWN])
    if (hidden := len(data.filters) - _FILTERS_SHOWN) > 0:
        filters += f" +{hidden}"
    settings = [
        ui.chip(f"{data.volume}%", icon="voice", style=Type.MONO_XS_MEDIUM),
        ui.chip("Shuffle", "on" if data.shuffle else "muted", icon="shuffle"),
        ui.chip(
            f"Loop {data.loop.lower()}" if looping else "Loop off",
            "on" if looping else "muted",
            icon="loop_one" if data.loop == "Track" else "loop",
        ),
        ui.chip("Autoplay", "on" if data.autoplay else "muted", icon="autoplay"),
        ui.chip(filters, "violet", icon="equalizer") if filters else None,
    ]
    return Column(track, progress, Column(Row(*settings, gap=8), _up_next(ui, data), gap=16), gap=24)
