from datetime import datetime
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import GiveawayEntryTable, GiveawayTable
from tortoise.exceptions import IntegrityError
from tortoise.expressions import F, Q
from tortoise.functions import Count
from tortoise.transactions import in_transaction
from typing import Any

STATUSES = ("scheduled", "running", "ended")


async def create_giveaway(guild_id: int, **values: Any) -> GiveawayTable:
    guild = await fetch_guild_settings(guild_id)
    return await GiveawayTable.create(guild=guild, **values)


async def fetch_giveaway(guild_id: int, giveaway_id: int) -> GiveawayTable | None:
    return await GiveawayTable.filter(id=giveaway_id, guild__guild_id=guild_id).select_related("guild").first()


async def fetch_giveaway_by_id(giveaway_id: int) -> GiveawayTable | None:
    return await GiveawayTable.filter(id=giveaway_id).select_related("guild").first()


async def fetch_by_message(message_id: int) -> GiveawayTable | None:
    return await GiveawayTable.filter(message_id=message_id).select_related("guild").first()


async def save_giveaway(giveaway: GiveawayTable, **values: Any) -> None:
    for key, value in values.items():
        setattr(giveaway, key, value)
    await giveaway.save(update_fields=list(values))


async def move_status(giveaway: GiveawayTable, before: str, after: str, **values: Any) -> bool:
    """Only moves it if still in `before`, so when the scheduler, commands and dashboard race, one wins."""
    changed = await GiveawayTable.filter(id=giveaway.id, status=before).update(status=after, **values)
    if changed:
        giveaway.status = after
        for key, value in values.items():
            setattr(giveaway, key, value)
    return bool(changed)


async def delete_giveaway(giveaway: GiveawayTable) -> None:
    await giveaway.delete()


async def forget_channel(channel_id: int) -> list[int]:
    """Ended giveaways stay as history. Returns the dropped scheduled ones that had a stored image."""
    stored = await GiveawayTable.filter(
        channel_id=channel_id, status="scheduled", image_file__isnull=False
    ).values_list("id", flat=True)
    await GiveawayTable.filter(channel_id=channel_id, status__in=("scheduled", "running")).delete()
    await GiveawayTable.filter(channel_id=channel_id).update(message_id=None)
    return stored


async def list_giveaways(
    guild_id: int, status: str | None, q: str | None, order: str, offset: int, limit: int
) -> tuple[list[GiveawayTable], int]:
    query = GiveawayTable.filter(guild__guild_id=guild_id)
    if status:
        query = query.filter(status=status)
    if q:
        query = query.filter(prize__icontains=q)
    total = await query.count()
    rows = await query.order_by(f"{'-' if order == 'desc' else ''}ends_at", "-id").offset(offset).limit(limit)
    return rows, total


async def count_by_status(guild_id: int) -> dict[str, int]:
    rows = (
        await GiveawayTable.filter(guild__guild_id=guild_id)
        .annotate(n=Count("id"))
        .group_by("status")
        .values_list("status", "n")
    )
    counts = dict.fromkeys(STATUSES, 0)
    counts.update(dict(rows))
    return counts


async def search_giveaways(guild_id: int, statuses: tuple[str, ...], text: str, limit: int) -> list[GiveawayTable]:
    query = GiveawayTable.filter(guild__guild_id=guild_id, status__in=statuses)
    if text:
        match = Q(prize__icontains=text)
        query = query.filter(match | Q(id=int(text)) if text.isdigit() and len(text) < 10 else match)
    return await query.order_by("-id").limit(limit)


async def next_due(startable: set[int]) -> datetime | None:
    """Only servers in `startable` can have scheduled giveaways start."""
    starts = (
        await GiveawayTable.filter(status="scheduled", guild__guild_id__in=startable)
        .order_by("starts_at")
        .limit(1)
        .values_list("starts_at", flat=True)
    )
    ends = await GiveawayTable.filter(status="running").order_by("ends_at").limit(1).values_list("ends_at", flat=True)
    times = [*starts, *ends]
    return min(times) if times else None


async def fetch_due(now: datetime, startable: set[int]) -> tuple[list[GiveawayTable], list[GiveawayTable]]:
    starting = (
        await GiveawayTable.filter(status="scheduled", starts_at__lte=now, guild__guild_id__in=startable)
        .select_related("guild")
        .order_by("starts_at")
    )
    ending = await GiveawayTable.filter(status="running", ends_at__lte=now).select_related("guild").order_by("ends_at")
    return starting, ending


async def fetch_running() -> list[GiveawayTable]:
    return await GiveawayTable.filter(status="running").select_related("guild")


async def fetch_running_with_invites(guild_id: int) -> list[GiveawayTable]:
    return await GiveawayTable.filter(guild__guild_id=guild_id, status="running", min_invites__gt=0).select_related(
        "guild"
    )


async def enter(giveaway_id: int, user_id: int) -> bool:
    """False when they were already in."""
    try:
        async with in_transaction() as conn:
            await GiveawayEntryTable.create(giveaway_id=giveaway_id, user_id=user_id, using_db=conn)
            await GiveawayTable.filter(id=giveaway_id).using_db(conn).update(entry_count=F("entry_count") + 1)
    except IntegrityError:
        return False
    return True


async def leave(giveaway_id: int, user_ids: list[int]) -> int:
    async with in_transaction() as conn:
        removed = await GiveawayEntryTable.filter(giveaway_id=giveaway_id, user_id__in=user_ids).using_db(conn).delete()
        if removed:
            await GiveawayTable.filter(id=giveaway_id).using_db(conn).update(entry_count=F("entry_count") - removed)
    return removed


async def fetch_entry(giveaway_id: int, user_id: int) -> GiveawayEntryTable | None:
    return await GiveawayEntryTable.filter(giveaway_id=giveaway_id, user_id=user_id).first()


async def fetch_entries(giveaway_id: int) -> list[tuple[int, int, datetime]]:
    """Every entry as `(user_id, bonus, entered_at)`, oldest first."""
    return (
        await GiveawayEntryTable.filter(giveaway_id=giveaway_id)
        .order_by("id")
        .values_list("user_id", "bonus", "entered_at")
    )


async def set_bonus(giveaway_id: int, user_ids: list[int], bonus: int) -> int:
    return await GiveawayEntryTable.filter(giveaway_id=giveaway_id, user_id__in=user_ids).update(bonus=bonus)
