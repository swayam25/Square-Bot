import discord
from dataclasses import dataclass
from datetime import datetime
from square.db import cache
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import GuildTable, InviteBonusTable, InviteJoinTable
from tortoise import connections
from tortoise.expressions import Q
from tortoise.functions import Count
from tortoise.transactions import in_transaction


@dataclass(frozen=True)
class InviteCounts:
    regular: int = 0
    left: int = 0
    fake: int = 0
    bonus: int = 0

    @property
    def total(self) -> int:
        return self.regular + self.bonus


_REGULAR = Q(left_at__isnull=True, fake=False)


async def set_fake_days(guild_id: int, days: int) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.invite_fake_days = days
    await guild.save(update_fields=["invite_fake_days"])
    cache.entry(guild_id).invite_fake_days = days


async def record_join(guild_id: int, member: discord.Member, inviter_id: int | None, code: str | None) -> bool:
    joined_at = member.joined_at or discord.utils.utcnow()
    fake = (joined_at - member.created_at).days < cache.get(guild_id).invite_fake_days
    guild = await fetch_guild_settings(guild_id)
    await InviteJoinTable.update_or_create(
        guild=guild,
        member_id=member.id,
        defaults={"inviter_id": inviter_id, "code": code, "joined_at": joined_at, "left_at": None, "fake": fake},
    )
    return fake


async def record_leave(guild_id: int, member_id: int) -> None:
    await InviteJoinTable.filter(guild__guild_id=guild_id, member_id=member_id, left_at__isnull=True).update(
        left_at=discord.utils.utcnow()
    )


async def fetch_counts(guild_id: int, user_id: int) -> InviteCounts:
    rows = (
        await InviteJoinTable.filter(guild__guild_id=guild_id, inviter_id=user_id)
        .annotate(
            n_regular=Count("id", _filter=_REGULAR),
            n_left=Count("id", _filter=Q(left_at__isnull=False)),
            n_fake=Count("id", _filter=Q(fake=True)),
        )
        .group_by("inviter_id")
        .values("n_regular", "n_left", "n_fake")
    )
    bonus = await InviteBonusTable.filter(guild__guild_id=guild_id, user_id=user_id).first()
    row = rows[0] if rows else {}
    return InviteCounts(
        row.get("n_regular", 0), row.get("n_left", 0), row.get("n_fake", 0), bonus.amount if bonus else 0
    )


async def fetch_leaderboard(guild_id: int) -> list[tuple[int, InviteCounts]]:
    rows = (
        await InviteJoinTable.filter(guild__guild_id=guild_id, inviter_id__isnull=False)
        .annotate(
            n_regular=Count("id", _filter=_REGULAR),
            n_left=Count("id", _filter=Q(left_at__isnull=False)),
            n_fake=Count("id", _filter=Q(fake=True)),
        )
        .group_by("inviter_id")
        .values_list("inviter_id", "n_regular", "n_left", "n_fake")
    )
    bonuses = dict(await InviteBonusTable.filter(guild__guild_id=guild_id).values_list("user_id", "amount"))
    counts = {
        inviter_id: InviteCounts(regular, left, fake, bonuses.pop(inviter_id, 0))
        for inviter_id, regular, left, fake in rows
    }
    counts |= {user_id: InviteCounts(bonus=amount) for user_id, amount in bonuses.items()}
    return sorted(
        ((user_id, c) for user_id, c in counts.items() if c.total), key=lambda item: (-item[1].total, item[0])
    )


_RANK_SQL = """
WITH totals AS (
    SELECT user_id, SUM(n)::bigint AS total
    FROM (
        SELECT j.inviter_id AS user_id, COUNT(*) FILTER (WHERE j.left_at IS NULL AND NOT j.fake) AS n
        FROM invite_join j JOIN guild g ON g.id = j.guild_id
        WHERE g.guild_id = $1::bigint AND j.inviter_id IS NOT NULL
        GROUP BY j.inviter_id
        UNION ALL
        SELECT b.user_id, b.amount
        FROM invite_bonus b JOIN guild g ON g.id = b.guild_id
        WHERE g.guild_id = $1::bigint
    ) parts
    GROUP BY user_id
)
SELECT COUNT(*) AS ahead FROM totals WHERE total <> 0 AND (total > $3::bigint OR (total = $3::bigint AND user_id < $2::bigint))
"""


async def fetch_rank(guild_id: int, user_id: int, total: int) -> int | None:
    if not total:
        return None
    rows = await connections.get("default").execute_query_dict(_RANK_SQL, [guild_id, user_id, total])
    return rows[0]["ahead"] + 1


async def fetch_join(guild_id: int, member_id: int) -> InviteJoinTable | None:
    return await InviteJoinTable.filter(guild__guild_id=guild_id, member_id=member_id).first()


async def add_bonus(guild_id: int, user_id: int, amount: int) -> int:
    guild = await fetch_guild_settings(guild_id)
    row, _ = await InviteBonusTable.get_or_create(guild=guild, user_id=user_id)
    row.amount += amount
    await row.save()
    return row.amount


async def fetch_invitees(guild_id: int, user_id: int, limit: int) -> list[InviteJoinTable]:
    return (
        await InviteJoinTable.filter(guild__guild_id=guild_id, inviter_id=user_id).order_by("-joined_at").limit(limit)
    )


async def change_bonuses(guild_id: int, user_ids: list[int], amount: int, *, add: bool) -> dict[int, int]:
    guild = await fetch_guild_settings(guild_id)
    bonuses: dict[int, int] = {}
    async with in_transaction():
        for user_id in user_ids:
            row, _ = await InviteBonusTable.get_or_create(guild=guild, user_id=user_id)
            row.amount = row.amount + amount if add else amount
            await row.save(update_fields=["amount"])
            bonuses[user_id] = row.amount
    return bonuses


async def reset_invites(guild_id: int, user_id: int | None = None) -> None:
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    joins = InviteJoinTable.filter(guild=guild)  # Deletes can't join across relations
    bonuses = InviteBonusTable.filter(guild=guild)
    if user_id is not None:
        joins, bonuses = joins.filter(inviter_id=user_id), bonuses.filter(user_id=user_id)
    await joins.delete()
    await bonuses.delete()


async def invite_times_since(guild_id: int, since: datetime) -> tuple[list[datetime], list[datetime]]:
    joins = InviteJoinTable.filter(guild__guild_id=guild_id)
    invited = await joins.filter(joined_at__gte=since, inviter_id__isnull=False).values_list("joined_at", flat=True)
    left = await joins.filter(left_at__gte=since).values_list("left_at", flat=True)
    return list(invited), list(left)
