import asyncio
import discord
import logging
from litestar import Router, get, post
from litestar.di import Provide
from litestar.params import Parameter
from square.api.auth import provide_guild, provide_member
from square.api.resolve import SettingError
from square.api.routes.settings import REFUSED, refused
from square.api.schemas import (
    Bonus,
    BonusChange,
    InviteBoard,
    Invitee,
    InviteEntry,
    InviteProfile,
    person_of,
)
from square.api.users import find_user, people_of
from square.core import Client
from square.db.funcs import invites as invites_db
from typing import Annotated, Literal

log = logging.getLogger(__name__)

PAGE_SIZE = 25
SortKey = Literal["total", "regular", "left", "fake", "bonus"]
RECENT_INVITEES = 20


@get("/leaderboard", summary="Everyone with invites, highest first")
async def invite_leaderboard(
    client: Client,
    guild: discord.Guild,
    page: Annotated[int, Parameter(ge=1, le=10_000)] = 1,
    sort: SortKey = "total",
    order: Literal["asc", "desc"] = "desc",
) -> InviteBoard:
    ranked = await invites_db.fetch_leaderboard(guild.id)
    ranks = {user_id: rank for rank, (user_id, _) in enumerate(ranked, start=1)}
    sign = -1 if order == "desc" else 1
    board = sorted(ranked, key=lambda item: (sign * getattr(item[1], sort), ranks[item[0]]))
    pages = max(1, -(-len(board) // PAGE_SIZE))
    page = min(page, pages)
    start = (page - 1) * PAGE_SIZE
    chunk = board[start : start + PAGE_SIZE]
    people = await people_of(client, guild, [user_id for user_id, _ in chunk])
    return InviteBoard(
        entries=[
            InviteEntry(
                rank=ranks[user_id],
                user=person,
                regular=counts.regular,
                left=counts.left,
                fake=counts.fake,
                bonus=counts.bonus,
                total=counts.total,
            )
            for (user_id, counts), person in zip(chunk, people, strict=True)
        ],
        page=page,
        pages=pages,
        people=len(board),
    )


@get("/people/{user_id:str}", summary="One person's invites, who invited them and who they invited")
async def invite_profile(
    client: Client, guild: discord.Guild, user_id: Annotated[str, Parameter(pattern=r"^\d{17,20}$")]
) -> InviteProfile:
    target = int(user_id)
    counts = await invites_db.fetch_counts(guild.id, target)
    rank, join, invitees, user = await asyncio.gather(
        invites_db.fetch_rank(guild.id, target, counts.total),
        invites_db.fetch_join(guild.id, target),
        invites_db.fetch_invitees(guild.id, target, RECENT_INVITEES),
        find_user(client, guild, target),
    )
    inviter_id = join.inviter_id if join else None
    inviter, people = await asyncio.gather(
        find_user(client, guild, inviter_id) if inviter_id else asyncio.sleep(0),
        people_of(client, guild, [row.member_id for row in invitees]),
    )
    return InviteProfile(
        rank=rank,
        user=person_of(target, user),
        member=guild.get_member(target) is not None,
        regular=counts.regular,
        left=counts.left,
        fake=counts.fake,
        bonus=counts.bonus,
        total=counts.total,
        invited_by=person_of(inviter_id, inviter) if inviter_id else None,
        invitees=[
            Invitee(
                user=person,
                joined_at=round(row.joined_at.timestamp() * 1000),
                left=row.left_at is not None,
                fake=row.fake,
            )
            for row, person in zip(invitees, people, strict=True)
        ],
    )


@post("/bonus", summary="Add to or set the bonus invites of one or more people", status_code=200, responses=REFUSED)
async def change_bonus(guild: discord.Guild, member: discord.Member, data: BonusChange) -> list[Bonus]:
    if data.mode == "add" and data.amount == 0:
        raise SettingError("Pick an amount other than 0.")
    user_ids = list(dict.fromkeys(int(user_id) for user_id in data.user_ids))
    bonuses = await invites_db.change_bonuses(guild.id, user_ids, data.amount, add=data.mode == "add")
    log.info(
        "Dashboard: %s (%s) %s %s bonus invites for %d people in %s (%s)",
        member,
        member.id,
        "added" if data.mode == "add" else "set",
        data.amount,
        len(user_ids),
        guild,
        guild.id,
    )
    return [Bonus(user_id=str(user_id), bonus=bonus) for user_id, bonus in bonuses.items()]


router = Router(
    "/guilds/{guild_id:str}/invites",
    tags=["Invites"],
    exception_handlers={SettingError: refused},
    dependencies={
        "guild": Provide(provide_guild, sync_to_thread=False),
        "member": Provide(provide_member, sync_to_thread=False),
    },
    route_handlers=[invite_leaderboard, invite_profile, change_bonus],
)
