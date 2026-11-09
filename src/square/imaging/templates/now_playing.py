import msgspec
from PIL import Image
from square.imaging.canvas import open_image
from square.imaging.components import Kit
from square.imaging.layout import Box, Column, Expand, Fill, Node, Picture, Row, Spacer
from square.imaging.tokens import Shape, Type

_ARTWORK = 168
_COVER = 40
_FILTERS_SHOWN = 2
# Lavalink source names with a brand logo in `assets/emojis`. Others get a music note
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
    fill, color = ui.container("secondary")
    return Box(ui.icon("music", size * 0.5, color), fill=fill, radius=radius, width=size, height=size)


def build(ui: Kit, data: NowPlaying) -> Node:
    """The current track: artwork, title and requester, a wavy progress bar, the player's settings and what's next."""
    s = ui.scheme
    if data.stream:
        state = ui.chip("Live", "error")
    elif data.paused:
        state = ui.chip("Paused", "warning")
    else:
        state = ui.chip("Playing", "primary")
    if data.source in _LOGOS:
        source = ui.chip(source_label(data.source), icon=data.source, tint=False)
    else:
        source = ui.chip(source_label(data.source), icon="music")
    requester = (
        Row(
            ui.avatar(open_image(data.requester_avatar), data.requester, 24),
            Expand(ui.text(f"Requested by {data.requester}", Type.BODY_MEDIUM, s.on_surface_variant)),
            gap=8,
        )
        if data.requester
        else None
    )
    track = Row(
        _artwork(ui, data.artwork, _ARTWORK, Shape.LARGE),
        Expand(
            Column(
                ui.chips(state, source),
                Spacer(8),
                ui.text(data.title, Type.HEADLINE_SMALL),
                ui.text(data.author, Type.TITLE_MEDIUM, s.on_surface_variant),
                Fill(),
                requester,
                gap=4,
            )
        ),
        gap=20,
        align="stretch",
    )
    times = Row(
        ui.text(data.elapsed, Type.LABEL_LARGE, s.on_surface_variant),
        Spacer(),
        ui.text("Live" if data.stream else data.duration, Type.LABEL_LARGE, s.on_surface_variant),
    )
    # A paused track lies flat, like the still bar on the player card
    progress = Column(ui.progress(1 if data.stream else data.progress, wavy=not data.paused), times, gap=8)

    def toggle(label: str, icon: str, on: bool) -> Node:
        return ui.chip(label, "secondary" if on else None, icon=icon)

    looping = data.loop != "Disabled"
    filters = " · ".join(data.filters[:_FILTERS_SHOWN])
    if (hidden := len(data.filters) - _FILTERS_SHOWN) > 0:
        filters += f" +{hidden}"
    settings = ui.chips(
        ui.chip(f"Volume {data.volume}%", icon="voice"),
        toggle(
            f"Loop {data.loop.lower()}" if looping else "Loop off",
            "loop_one" if data.loop == "Track" else "loop",
            looping,
        ),
        toggle("Shuffle", "shuffle", data.shuffle),
        toggle("Autoplay", "autoplay", data.autoplay),
        ui.chip(filters, "tertiary", icon="equalizer") if filters else None,
    )
    up_next = ui.list_item(
        data.up_next or "Nothing queued",
        leading=Row(
            ui.text("Up next", Type.LABEL_LARGE, s.primary),
            _artwork(ui, data.up_next_artwork, _COVER, Shape.SMALL) if data.up_next else None,
            gap=16,
        ),
        trailing=ui.chip(f"{data.queued} in queue", icon="queue_white") if data.queued else None,
    )
    return Column(track, progress, settings, up_next, gap=20)
