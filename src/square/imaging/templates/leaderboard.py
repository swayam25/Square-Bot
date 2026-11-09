import msgspec
from square.imaging.canvas import open_image
from square.imaging.components import Kit, Tone
from square.imaging.layout import Box, Column, Expand, Fill, Node, Row
from square.imaging.tokens import Shape, Type
from square.utils.helpers import fmt_number


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


_PODIUM: dict[int, tuple[str, Tone]] = {1: ("1st", "primary"), 2: ("2nd", "secondary"), 3: ("3rd", "tertiary")}


def _place(ui: Kit, inviter: Inviter) -> Node:
    label, tone = _PODIUM[inviter.rank]
    lead = inviter.rank == 1
    on = ui.container(tone)[1]
    avatar = ui.avatar(open_image(inviter.avatar), inviter.name, 72 if lead else 56, tone=tone, inverted=True)
    return Expand(
        ui.card(
            ui.text(label, Type.LABEL_LARGE, on),
            ui.crowned(avatar, 72) if lead else avatar,
            ui.text(inviter.name, Type.TITLE_MEDIUM, on),
            ui.text(fmt_number(inviter.total), Type.DISPLAY_SMALL if lead else Type.HEADLINE_LARGE, on),
            ui.text("invites", Type.LABEL_MEDIUM, on),
            variant=tone,
            align="center",
            padding=(12, 24 if lead else 16),
            gap=6,
            radius=Shape.EXTRA_LARGE if lead else Shape.LARGE,
        )
    )


def _bonus_chip(ui: Kit, bonus: int) -> Node:
    """Moderators can take invites away too, so a negative bonus reads as a penalty."""
    if bonus > 0:
        return ui.chip(f"+{fmt_number(bonus)} bonus", "success", icon="add")
    return ui.chip(f"{fmt_number(bonus)} bonus", "error", icon="remove")


def _row(ui: Kit, inviter: Inviter) -> Node:
    s = ui.scheme
    return ui.list_item(
        inviter.name,
        leading=Row(
            Box(ui.text(str(inviter.rank), Type.TITLE_MEDIUM, s.on_surface_variant, align="center"), width=28),
            ui.avatar(open_image(inviter.avatar), inviter.name, 40),
            gap=12,
        ),
        supporting=ui.chips(
            ui.chip(f"{fmt_number(inviter.regular)} regular", icon="user_add_white"),
            ui.chip(f"{fmt_number(inviter.left)} left", "warning", icon="user_remove_white") if inviter.left else None,
            ui.chip(f"{fmt_number(inviter.fake)} fake", "error", icon="fake") if inviter.fake else None,
            _bonus_chip(ui, inviter.bonus) if inviter.bonus else None,
        ),
        trailing=Column(
            ui.text(fmt_number(inviter.total), Type.HEADLINE_SMALL, s.primary, align="end"),
            ui.text("invites", Type.LABEL_SMALL, s.on_surface_variant, align="end"),
        ),
    )


def build(ui: Kit, data: Leaderboard) -> Node:
    """The invite leaderboard: a podium for the top 3 on the first page, then one row per inviter."""
    s = ui.scheme
    podium = data.inviters[:3] if data.page == 1 and len(data.inviters) >= 3 else []
    rest = data.inviters[len(podium) :]
    return Column(
        ui.header(
            "Invite Leaderboard",
            Row(
                ui.text(f"{data.guild_name} ·", Type.BODY_MEDIUM, s.on_surface_variant),
                ui.icon("members", 18, s.on_surface_variant),
                Expand(ui.text(f"{fmt_number(data.member_count)} members", Type.BODY_MEDIUM, s.on_surface_variant)),
                gap=6,
            ),
            leading=ui.guild_icon(open_image(data.guild_icon), data.guild_name, 48),
            trailing=ui.chip(f"Page {data.page} of {data.pages}", "secondary"),
        ),
        Column(
            Row(*(_place(ui, podium[i]) for i in (1, 0, 2)), gap=8, align="end") if podium else None,
            *(_row(ui, inviter) for inviter in rest),
            gap=8,
        ),
        Fill(),
        ui.text(
            f"Fake invites are accounts younger than {data.fake_days} days when they joined.",
            Type.BODY_SMALL,
            s.on_surface_variant,
        ),
        gap=16,
    )
