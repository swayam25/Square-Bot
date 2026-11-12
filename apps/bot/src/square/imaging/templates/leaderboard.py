import msgspec
from square.imaging.canvas import open_image, text_width
from square.imaging.components import Kit
from square.imaging.layout import Box, Column, Expand, Fill, Node, Row, Spacer
from square.imaging.theme import MIST_300, ORANGE_300, RGB
from square.imaging.tokens import Radius, Type
from square.utils.helpers import fmt_count


class Inviter(msgspec.Struct, frozen=True):
    rank: int
    name: str
    avatar: bytes | None
    total: int
    regular: int
    left: int
    fake: int
    bonus: int


class Leaderboard(msgspec.Struct, frozen=True):
    guild_name: str
    guild_icon: bytes | None
    member_count: int
    fake_days: int
    page: int
    pages: int
    inviters: list[Inviter]


_STEPS = {1: 144, 2: 120, 3: 96}


def _podium_ink(ui: Kit, rank: int) -> RGB:
    return {1: ui.theme.warning, 2: MIST_300, 3: ORANGE_300}[rank]


def _place(ui: Kit, inviter: Inviter) -> Node:
    ink = _podium_ink(ui, inviter.rank)
    step = Box(
        Column(
            ui.text(str(inviter.rank), Type.DISPLAY_PLACE, ink, align="center"),
            ui.text(("1st", "2nd", "3rd")[inviter.rank - 1].upper(), Type.MONO_XS_LABEL, ink, align="center"),
            gap=2,
        ),
        padding=(16, 0, 0, 0),
        fill=ui.theme.tint(ink, 0.1),
        radius=Radius.XL2,
        height=_STEPS[inviter.rank],
        align="start",
    )
    return Expand(
        Column(
            Row(Spacer(), ui.avatar(open_image(inviter.avatar), inviter.name, 56), Spacer()),
            Column(
                ui.text(inviter.name, Type.BASE_SEMIBOLD, align="center"),
                ui.muted(fmt_count(inviter.total), Type.MONO_SM_MEDIUM, align="center"),
                gap=2,
            ),
            step,
            gap=16,
        )
    )


def _splits(inviters: list[Inviter]) -> list[str]:
    columns = [
        ("regular", [fmt_count(inviter.regular) for inviter in inviters]),
        ("left", [fmt_count(inviter.left) for inviter in inviters]),
        ("fake", [fmt_count(inviter.fake) for inviter in inviters]),
    ]
    bonus = [
        f"{'+' if inviter.bonus > 0 else ''}{fmt_count(inviter.bonus)}" if inviter.bonus else "" for inviter in inviters
    ]
    if any(bonus):
        columns.append(("bonus", bonus))
    widths = [max(map(len, counts)) for _, counts in columns]
    rows = []
    for i in range(len(inviters)):
        parts = [
            f"{counts[i]:>{width}} {label}" if counts[i] else " " * (width + 1 + len(label))
            for (label, counts), width in zip(columns, widths, strict=True)
        ]
        row = parts[0]
        for part in parts[1:]:
            row += (" · " if part.strip() else "   ") + part
        rows.append(row)
    return rows


def _row(ui: Kit, inviter: Inviter, split: str, rank_width: float) -> Node:
    return Column(
        Box(Spacer(1), fill=ui.theme.line, height=1),
        Box(
            Row(
                Box(ui.muted(str(inviter.rank), Type.MONO_SM), width=rank_width),
                ui.avatar(open_image(inviter.avatar), inviter.name, 32),
                Expand(ui.text(inviter.name, Type.BASE_MEDIUM)),
                ui.muted(split, Type.MONO_XS),
                Box(ui.text(fmt_count(inviter.total), Type.MONO_BASE, align="end"), width=64),
                gap=16,
            ),
            padding=(8, 0),
            height=48,
        ),
    )


def build(ui: Kit, data: Leaderboard) -> Node:
    podium = data.inviters[:3] if data.page == 1 and len(data.inviters) >= 3 else []
    rest = data.inviters[len(podium) :]
    rank_width = max([24.0, *(text_width(str(inviter.rank), Type.MONO_SM) for inviter in rest)])
    subtitle = Row(
        ui.muted(data.guild_name),
        ui.muted(" · "),
        ui.muted(fmt_count(data.member_count), Type.MONO_SM),
        ui.muted(" members"),
    )
    return Column(
        ui.header(
            "Invite leaderboard",
            subtitle,
            leading=ui.guild_icon(open_image(data.guild_icon), data.guild_name, 40),
            trailing=ui.muted(f"{data.page} / {data.pages}", Type.MONO_SM),
        ),
        Row(*(_place(ui, podium[i]) for i in (1, 0, 2)), gap=8, align="end") if podium else None,
        Column(*(_row(ui, inviter, split, rank_width) for inviter, split in zip(rest, _splits(rest), strict=True)))
        if rest
        else None,
        Fill(),
        gap=24,
    )
