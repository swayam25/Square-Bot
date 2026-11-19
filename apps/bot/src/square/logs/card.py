import datetime
import discord
import io
from dataclasses import dataclass, field
from discord import ui
from PIL import Image
from square.logs.catalog import Event
from square.utils import config
from square.utils.emoji import emoji
from typing import Literal

type Tone = Literal["theme", "red", "orange", "green"]
type Row = tuple[str, str, str]

TEXT_LIMIT = 1024
SWATCH_SIZE = 64


def clip(text: str, limit: int = TEXT_LIMIT) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def person(user: discord.abc.User) -> str:
    return f"{user.mention} (`{user.name}`)"


def person_id(user_id: int) -> str:
    return f"<@{user_id}> (`{user_id}`)"


def when(at: datetime.datetime) -> str:
    return discord.utils.format_dt(at, "R")


@dataclass(slots=True)
class Entry:
    """
    One thing that happened. Listeners only describe it, `logs.emit` decides whether and where it's posted.

    Each row is (icon, label, value). A value that starts with a newline shows as a block under its label.
    """

    event: Event
    title: str
    tone: Tone = "theme"
    rows: list[Row] = field(default_factory=list)
    thumbnail: str | None = None
    jump: str | None = None  # A message URL, shown as a "Jump to message" button
    file: discord.File | None = None
    swatch: int | None = None  # A color shown as the thumbnail, like a role's
    channel_id: int | None = None
    member: discord.Member | None = None
    bot: bool = False

    def add(self, icon: str, label: str, value: str | None) -> Entry:
        if value:
            self.rows.append((icon, label, value))
        return self


_COLORED = ("_red", "_orange", "_green")


def icon(name: str, tone: Tone) -> str:
    """A name that already ends in a color keeps it, like the red icon on a Before row."""
    if tone == "theme" or name.endswith(_COLORED):
        return str(getattr(emoji, name))
    # A color with no file yet falls back to the plain icon instead of losing the whole log
    return str(getattr(emoji, f"{name}_{tone}", None) or getattr(emoji, name))


def body(entry: Entry) -> str:
    lines = []
    for name, label, value in entry.rows:
        gap = "" if value.startswith("\n") else " "
        lines.append(f"{icon(name, entry.tone)} **{label}**:{gap}{value}")
    return "\n".join(lines)


def swatch_file(color: int, filename: str) -> discord.File:
    image = Image.new("RGB", (SWATCH_SIZE, SWATCH_SIZE), f"#{color:06x}")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)
    return discord.File(buffer, filename=filename)


def render(entry: Entry, swatch: str | None = None) -> list[ui.Item]:
    """The card, plus its jump button under it. `swatch` is the file name the color swatch was attached under."""
    header: list[ui.Item] = [ui.TextDisplay(f"## {entry.title}"), ui.TextDisplay(body(entry))]
    thumbnail = f"attachment://{swatch}" if swatch else entry.thumbnail
    items: list[ui.Item] = [ui.Section(*header, accessory=ui.Thumbnail(thumbnail))] if thumbnail else header
    if entry.file:
        items.append(ui.File(f"attachment://{entry.file.filename}"))
    card: list[ui.Item] = [
        ui.Container(*items, color=None if entry.tone == "theme" else getattr(config.color, entry.tone))
    ]
    if entry.jump:
        card.append(
            ui.ActionRow(
                ui.Button(
                    label="Jump to message",
                    emoji=emoji.messages_white,
                    style=discord.ButtonStyle.link,
                    url=entry.jump,
                )
            )
        )
    return card


def file_count(entry: Entry) -> int:
    return (entry.file is not None) + (entry.swatch is not None)


def cost(entry: Entry) -> tuple[int, int]:
    """(components, characters) the card takes up, for packing several into one message."""
    thumbnail = entry.thumbnail or entry.swatch is not None
    components = 3 + (2 if thumbnail else 0) + (1 if entry.file else 0) + (2 if entry.jump else 0)
    return components, len(entry.title) + len(body(entry)) + 4
