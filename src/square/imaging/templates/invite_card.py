import msgspec
from square.imaging.canvas import open_image
from square.imaging.components import Kit
from square.imaging.layout import Column, Expand, Node, Row
from square.imaging.tokens import Shape, Type
from square.utils.helpers import fmt_number


class InviteCard(msgspec.Struct, frozen=True):
    name: str
    username: str
    avatar: bytes | None
    guild_name: str
    guild_icon: bytes | None
    rank: int | None
    regular: int
    left: int
    fake: int
    bonus: int
    fake_days: int

    @property
    def total(self) -> int:
        return self.regular + self.bonus


def build(ui: Kit, data: InviteCard) -> Node:
    """One member's invites: their total, a bar splitting every invite by kind, and a tile per kind."""
    s = ui.scheme
    kinds = (
        ("Regular", data.regular, s.primary, "user_add_white"),
        ("Bonus", data.bonus, s.success, "add"),
        ("Left", data.left, s.warning, "user_remove_white"),
        ("Fake", data.fake, s.error, "fake"),
    )
    avatar = ui.avatar(open_image(data.avatar), data.name, 56)
    subtitle = Row(
        ui.text(f"@{data.username} ·", Type.BODY_MEDIUM, s.on_surface_variant),
        # Fits the 20dp subtitle line
        ui.guild_icon(open_image(data.guild_icon), data.guild_name, 18, radius=Shape.EXTRA_SMALL),
        Expand(ui.text(data.guild_name, Type.BODY_MEDIUM, s.on_surface_variant)),
        gap=6,
    )
    return Column(
        ui.header(
            data.name,
            subtitle,
            leading=ui.crowned(avatar, 56) if data.rank == 1 else avatar,
            trailing=ui.chip(f"Rank #{data.rank}" if data.rank else "Unranked", "secondary"),
        ),
        Column(
            Row(
                ui.text(fmt_number(data.total), Type.DISPLAY_MEDIUM, s.primary),
                ui.icon("invite", 24, s.on_surface_variant),
                ui.text("total invites", Type.TITLE_MEDIUM, s.on_surface_variant),
                gap=12,
                align="end",
            ),
            # Negative bonuses take invites away, so they can't be a share of the bar
            ui.segmented_bar(*((max(value, 0), color) for _, value, color, _ in kinds)),
            gap=12,
        ),
        Row(
            *(Expand(ui.stat(label, fmt_number(value), color, icon=icon)) for label, value, color, icon in kinds), gap=8
        ),
        ui.text(
            f"Total counts regular and bonus invites. Fake invites are accounts younger than {data.fake_days} days "
            "when they joined.",
            Type.BODY_SMALL,
            s.on_surface_variant,
        ),
        gap=20,
    )
