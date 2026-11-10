import msgspec
from square.imaging.canvas import open_image
from square.imaging.components import Kit
from square.imaging.layout import Column, Expand, Node, Row, Text
from square.imaging.tokens import Radius, Type
from square.utils.helpers import fmt_count


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
    t = ui.theme
    kinds = (
        ("Regular", data.regular, t.accent),
        ("Bonus", data.bonus, t.success),
        ("Left", data.left, t.warning),
        ("Fake", data.fake, t.danger),
    )
    subtitle = Row(
        ui.muted(f"@{data.username}", Type.MONO_SM),
        ui.muted("·"),
        ui.guild_icon(open_image(data.guild_icon), data.guild_name, 16, radius=Radius.MD),
        Expand(ui.muted(data.guild_name)),
        gap=8,
    )
    rank = (
        ui.chip(f"Rank #{data.rank}", "accent", style=Type.MONO_SM_MEDIUM)
        if data.rank
        else ui.chip("Unranked", "muted", style=Type.MONO_SM_MEDIUM)
    )
    # Negative bonuses take invites away, so they can't be a share of the bar
    counted = [max(value, 0) for _, value, _ in kinds]
    share = round(100 * counted[0] / sum(counted)) if sum(counted) else 0
    return Column(
        ui.header(
            data.name,
            subtitle,
            leading=ui.avatar(open_image(data.avatar), data.name, 56, Type.XL2_SEMIBOLD),
            trailing=rank,
        ),
        Column(
            Row(
                ui.text(fmt_count(data.total), Type.MONO_5XL),
                ui.muted("total invites", Type.BASE),
                gap=16,
                align="baseline",
            ),
            ui.split_bar(
                *((value, color) for value, (_, _, color) in zip(counted, kinds, strict=True)),
                label=f"{share}% regular".upper() if counted[0] else None,
            ),
            gap=16,
        ),
        Row(*(Expand(ui.stat(label, fmt_count(value), color)) for label, value, color in kinds), gap=8),
        Text(
            f"Total counts regular and bonus invites. Fake invites are accounts younger than {data.fake_days} days "
            "when they joined.",
            Type.XS,
            t.muted,
        ),
        gap=24,
    )
