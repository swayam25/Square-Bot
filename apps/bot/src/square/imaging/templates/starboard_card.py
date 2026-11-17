import msgspec
from square.imaging.canvas import open_image
from square.imaging.components import Kit
from square.imaging.layout import Column, Expand, Node, Row, Text
from square.imaging.tokens import Radius, Type
from square.utils.helpers import fmt_count


class StarboardCard(msgspec.Struct, frozen=True):
    name: str
    username: str
    avatar: bytes | None
    guild_name: str
    guild_icon: bytes | None
    rank: int | None
    received: int
    posts: int
    best: int


def build(ui: Kit, data: StarboardCard) -> Node:
    t = ui.theme
    average = data.received / data.posts if data.posts else 0
    subtitle = Row(
        ui.muted(f"@{data.username}", Type.MONO_SM),
        ui.muted("·"),
        ui.guild_icon(open_image(data.guild_icon), data.guild_name, 16, radius=Radius.MD),
        Expand(ui.muted(data.guild_name)),
        gap=8,
    )
    rank = (
        ui.chip(f"Rank #{data.rank}", "warning" if data.rank == 1 else "accent", style=Type.MONO_SM_MEDIUM)
        if data.rank
        else ui.chip("Unranked", "muted", style=Type.MONO_SM_MEDIUM)
    )
    tiles = (
        ("On the board", fmt_count(data.posts), t.accent),
        ("Best post", fmt_count(data.best), t.warning),
        ("Per post", f"{average:.1f}" if average % 1 else fmt_count(int(average)), t.success),
    )
    return Column(
        ui.header(
            data.name,
            subtitle,
            leading=ui.avatar(open_image(data.avatar), data.name, 56, Type.XL2_SEMIBOLD),
            trailing=rank,
        ),
        Row(
            ui.icon("star", 40, t.warning),
            ui.text(fmt_count(data.received), Type.MONO_5XL),
            ui.muted("stars received", Type.BASE),
            gap=16,
            align="center",
        ),
        Row(*(Expand(ui.stat(label, value, color)) for label, value, color in tiles), gap=8),
        Text(
            "Stars count the votes on posts that made the board, minus downvotes.",
            Type.XS,
            t.muted,
        ),
        gap=24,
    )
