import msgspec
import zlib
from square.imaging.canvas import open_image
from square.imaging.components import Kit, initial
from square.imaging.layout import Box, Column, Node, Paragraph, Picture, Row, Text
from square.imaging.theme import AVATAR_FILLS, GRAY_950
from square.imaging.tokens import Type

SIZE = 360
PADDING = 32
SIZES = (Type.XL3_MEDIUM, Type.XL2_MEDIUM, Type.XL_MEDIUM, Type.LG_MEDIUM, Type.BASE_MEDIUM)


class QuoteCard(msgspec.Struct, frozen=True):
    text: str
    name: str
    username: str
    avatar: bytes | None
    color: bool = False
    flip: bool = False


def _portrait(ui: Kit, data: QuoteCard) -> Node:
    image = open_image(data.avatar)
    if image is None:
        fill = AVATAR_FILLS[zlib.crc32(data.name.encode()) % len(AVATAR_FILLS)]
        letter = Text(initial(data.name), Type.DISPLAY_PLACE, GRAY_950, align="center")
        return Box(letter, fill=fill, width=SIZE, height=SIZE)
    if not data.color:
        image = image.convert("LA").convert("RGBA")
    return Picture(image, SIZE, fade="left" if data.flip else "right")


def build(ui: Kit, data: QuoteCard) -> Node:
    t = ui.theme
    author = Column(
        ui.text(data.name, Type.BASE_SEMIBOLD, align="center"),
        Text(f"@{data.username}", Type.MONO_SM, t.muted, align="center"),
        gap=4,
    )
    room = SIZE - PADDING * 2 - author.measure(SIZE) - 24
    words = Box(
        Column(Paragraph(data.text, SIZES, t.text, room, align="center"), author, gap=24),
        padding=PADDING,
    )
    portrait = _portrait(ui, data)
    row = Row(words, portrait) if data.flip else Row(portrait, words)
    return Box(row, height=SIZE)
