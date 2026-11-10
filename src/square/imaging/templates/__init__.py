from collections.abc import Callable
from io import BytesIO
from PIL import Image, ImageDraw
from square.imaging import Template
from square.imaging.templates import invite_card, leaderboard, now_playing

# Fake data for `python -m square.imaging`: one `sample_<template>` per template, registered in `PREVIEWS`. Cover the
# edge cases (long or styled names, big numbers, missing avatars) so layout bugs show up here first.


def sample_leaderboard() -> leaderboard.Leaderboard:
    """
    Edge cases for the leaderboard.

    Font fallback (✦ ♛ 𝓶), color emoji (🚀 ⭐ ❤️ 🇮🇳 👍🏽), truncation, compact numbers from thousands to millions,
    and a negative bonus.
    """
    names = [
        "kaizen",
        "rinbo ✦",
        "𝓶𝓸𝓬𝓱𝓲",
        "arcturus 🚀",
        "nyx ⭐",
        "a_really_long_username_that_never_seems_to_end_at_all",
        "Pixel ♛",
        "zoë ❤️",
        "Δelta",
        "ghost 🇮🇳👍🏽",
    ]
    inviters = []
    for rank, name in enumerate(names, start=1):
        regular = 1_248_000 // rank**3
        bonus = {1: 1500, 3: 10, 6: -3}.get(rank, 0)
        inviters.append(leaderboard.Inviter(rank, name, None, regular + bonus, regular, rank * 2 % 9, rank % 3, bonus))
    return leaderboard.Leaderboard("My Server", None, 2_384_512, 7, 1, 4, inviters)


def _sample_icon() -> bytes:
    """A stand-in server icon: a cyan-900 square with a white ring, enough to check size and corner rounding."""
    image = Image.new("RGBA", (128, 128), (0x10, 0x4E, 0x64, 255))
    ImageDraw.Draw(image).ellipse((32, 32, 96, 96), outline=(255, 255, 255, 255), width=14)
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def sample_invite_card() -> invite_card.InviteCard:
    """A long styled name with an emoji, compact numbers, and every kind of invite present so each segment shows."""
    return invite_card.InviteCard(
        name="𝓶𝓸𝓬𝓱𝓲 the long-named inviter 🚀",
        username="mochi.dev",
        avatar=None,
        guild_name="My Server",
        guild_icon=_sample_icon(),
        rank=3,
        regular=18_420,
        left=2_310,
        fake=640,
        bonus=1_500,
        fake_days=7,
    )


def _sample_artwork() -> bytes:
    """A 4:3 thumbnail with black letterbox bars around a 16:9 picture, like YouTube serves, to check the trim."""
    image = Image.new("RGB", (480, 360), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    for row in range(270):
        draw.line((0, 45 + row, 480, 45 + row), fill=(0x6A + row // 3, 0x2C, 0x7E - row // 4))
    draw.ellipse((170, 110, 310, 250), fill=(0xF4, 0xC4, 0x5A))
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def sample_now_playing() -> now_playing.NowPlaying:
    """A long title with an emoji, a requester without an avatar, more filters than fit, and a queue."""
    return now_playing.NowPlaying(
        title="Midnight City (Extended Mix) 🌃 feat. Someone With A Very Long Name",
        author="M83",
        source="youtube",
        artwork=_sample_artwork(),
        requester="𝓶𝓸𝓬𝓱𝓲",
        requester_avatar=None,
        progress=0.42,
        elapsed="01:47",
        duration="04:03",
        stream=False,
        paused=False,
        volume=80,
        loop="Queue",
        shuffle=False,
        autoplay=True,
        filters=["Bass Boost", "Nightcore", "8D"],
        up_next="Kids by MGMT",
        up_next_artwork=_sample_icon(),
        queued=12,
    )


PREVIEWS: dict[str, tuple[Template, Callable[[], object]]] = {
    "invite_card": (invite_card.build, sample_invite_card),
    "leaderboard": (leaderboard.build, sample_leaderboard),
    "now_playing": (now_playing.build, sample_now_playing),
}
