import discord
from dataclasses import dataclass
from square.db import cache
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import GuildTable, InviteBonusTable, InviteJoinTable
from tortoise.expressions import Q
from tortoise.functions import Count


@dataclass(frozen=True)
class InviteCounts:
    regular: int = 0
    left: int = 0
    fake: int = 0
    bonus: int = 0

    @property
    def total(self) -> int:
        return self.regular + self.bonus


# Still in the server and not a fake account: the invites that count
_REGULAR = Q(left_at__isnull=True, fake=False)


async def set_fake_days(guild_id: int, days: int) -> None:
    """
    Sets how young an account can be when it joins before it counts as fake.

    Args:
        guild_id (int): The guild ID to perform action on.
        days (int): The minimum account age in days.
    """
    guild = await fetch_guild_settings(guild_id)
    guild.invite_fake_days = days
    await guild.save()
    cache.entry(guild_id).invite_fake_days = days


async def record_join(guild_id: int, member: discord.Member, inviter_id: int | None, code: str | None) -> bool:
    """
    Records who invited a member. A rejoin updates the same row, so leaving and rejoining can't inflate counts.

    Args:
        guild_id (int): The guild ID to perform action on.
        member (:class:`discord.Member`): The member who joined.
        inviter_id (int | None): Who created the invite, if known.
        code (str | None): The invite code, if known.

    Returns:
        bool: Whether the account counts as fake (younger than the guild's threshold).
    """
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
    """
    Marks a member as gone, so they move from the inviter's regular count to left.

    Args:
        guild_id (int): The guild ID to perform action on.
        member_id (int): The member who left.
    """
    await InviteJoinTable.filter(guild__guild_id=guild_id, member_id=member_id, left_at__isnull=True).update(
        left_at=discord.utils.utcnow()
    )


async def fetch_counts(guild_id: int, user_id: int) -> InviteCounts:
    """
    Counts a user's invites in one query, plus their bonus.

    Args:
        guild_id (int): The guild ID to perform action on.
        user_id (int): The inviter.
    """
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
    """
    Every inviter's counts, highest total first.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
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
    return sorted(((user_id, c) for user_id, c in counts.items() if c.total), key=lambda item: -item[1].total)


async def fetch_join(guild_id: int, member_id: int) -> InviteJoinTable | None:
    """
    How a member last joined: inviter, code and time.

    Args:
        guild_id (int): The guild ID to perform action on.
        member_id (int): The member to look up.
    """
    return await InviteJoinTable.filter(guild__guild_id=guild_id, member_id=member_id).first()


async def add_bonus(guild_id: int, user_id: int, amount: int) -> int:
    """
    Adds (or with a negative amount, removes) bonus invites.

    Args:
        guild_id (int): The guild ID to perform action on.
        user_id (int): Who gets the bonus.
        amount (int): How many invites to add.

    Returns:
        int: The user's new bonus.
    """
    guild = await fetch_guild_settings(guild_id)
    row, _ = await InviteBonusTable.get_or_create(guild=guild, user_id=user_id)
    row.amount += amount
    await row.save()
    return row.amount


async def reset_invites(guild_id: int, user_id: int | None = None) -> None:
    """
    Clears a user's invites and bonus as an inviter, or everyone's when no user is given.

    Args:
        guild_id (int): The guild ID to perform action on.
        user_id (int | None): The inviter to reset, or None for the whole guild.
    """
    guild = await GuildTable.filter(guild_id=guild_id).first()
    if not guild:
        return
    joins = InviteJoinTable.filter(guild=guild)  # Deletes can't join across relations
    bonuses = InviteBonusTable.filter(guild=guild)
    if user_id is not None:
        joins, bonuses = joins.filter(inviter_id=user_id), bonuses.filter(user_id=user_id)
    await joins.delete()
    await bonuses.delete()
