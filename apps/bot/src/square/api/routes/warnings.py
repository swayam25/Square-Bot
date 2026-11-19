import asyncio
import discord
from datetime import datetime
from litestar import Router, delete, get, post
from litestar.di import Provide
from litestar.params import Parameter
from square.api.auth import provide_guild, provide_member
from square.api.refusals import REFUSED, refused
from square.api.resolve import SettingError
from square.api.schemas import (
    WarnBoard,
    WarnCreate,
    WarnEntry,
    WarningItem,
    WarningsCleared,
    WarnProfile,
    WarnResult,
    person_of,
)
from square.api.users import find_user, people_of
from square.cogs.moderation import warnings as warn_cog
from square.core import Client
from square.db.funcs import automod as automod_db
from square.utils.helpers import fmt_user
from typing import Annotated

PAGE_SIZE = 25
WARNINGS_PAGE = 10
UserId = Annotated[str, Parameter(pattern=r"^\d{17,20}$", description="A Discord user ID")]
Page = Annotated[int, Parameter(ge=1, le=10_000)]


def _ms(moment: datetime) -> int:
    return round(moment.timestamp() * 1000)


def _pages(count: int, size: int, page: int) -> tuple[int, int]:
    pages = max(1, -(-count // size))
    return min(page, pages), pages


def _moderator(member: discord.Member) -> discord.Member:
    # The same permission `/warn` needs: a warning can set off a timeout, kick or ban
    if not member.guild_permissions.moderate_members:
        raise SettingError("Changing warnings needs the Timeout Members permission.")
    return member


@get("/ranking", summary="Everyone with warnings, most first")
async def warning_ranking(client: Client, guild: discord.Guild, page: Page = 1) -> WarnBoard:
    ranked = await automod_db.fetch_ranking(guild.id)
    page, pages = _pages(len(ranked), PAGE_SIZE, page)
    start = (page - 1) * PAGE_SIZE
    chunk = ranked[start : start + PAGE_SIZE]
    people = await people_of(client, guild, [user_id for user_id, _, _ in chunk])
    return WarnBoard(
        entries=[
            WarnEntry(rank=start + index, user=person, warnings=count, last_at=_ms(last))
            for index, ((_, count, last), person) in enumerate(zip(chunk, people, strict=True), start=1)
        ],
        page=page,
        pages=pages,
        people=len(ranked),
        warnings=sum(count for _, count, _ in ranked),
    )


@get("/people/{user_id:str}", summary="One person's warnings, newest first")
async def warning_profile(client: Client, guild: discord.Guild, user_id: UserId, page: Page = 1) -> WarnProfile:
    target = int(user_id)
    ranked = await automod_db.fetch_ranking(guild.id)
    rank = next((place for place, (ranked_id, _, _) in enumerate(ranked, start=1) if ranked_id == target), None)
    total = ranked[rank - 1][1] if rank else 0
    page, pages = _pages(total, WARNINGS_PAGE, page)
    start = (page - 1) * WARNINGS_PAGE
    found = await automod_db.fetch_warnings(guild.id, target, start, WARNINGS_PAGE)
    moderator_ids = list(dict.fromkeys(row.moderator_id for row in found if row.moderator_id))
    user, moderators = await asyncio.gather(find_user(client, guild, target), people_of(client, guild, moderator_ids))
    by_id = dict(zip(moderator_ids, moderators, strict=True))
    return WarnProfile(
        user=person_of(target, user),
        member=guild.get_member(target) is not None,
        rank=rank,
        total=total,
        warnings=[
            WarningItem(
                id=row.id,
                number=total - start - index,
                reason=row.reason,
                moderator=by_id[row.moderator_id] if row.moderator_id else None,
                created_at=_ms(row.created_at),
            )
            for index, row in enumerate(found)
        ],
        page=page,
        pages=pages,
    )


@post("/", summary="Warn a member, the same as /warn", status_code=200, responses=REFUSED)
async def give_warning(client: Client, guild: discord.Guild, member: discord.Member, data: WarnCreate) -> WarnResult:
    moderator = _moderator(member)
    target = guild.get_member(int(data.user_id))
    if target is None:
        user = await find_user(client, guild, int(data.user_id))
        raise SettingError(f"{fmt_user(user) if user else data.user_id} isn't in this server.")
    if problem := warn_cog.refusal(moderator, target):
        raise SettingError(problem)
    warned = await warn_cog.warn(client, guild, target, data.reason.strip(), moderator)
    return WarnResult(
        total=warned.total, punishment=warned.punishment, punished=warned.punished, messaged=warned.messaged
    )


@delete("/people/{user_id:str}/{warning_id:int}", summary="Remove one warning", status_code=204, responses=REFUSED)
async def remove_warning(
    client: Client, guild: discord.Guild, member: discord.Member, user_id: UserId, warning_id: int
) -> None:
    _moderator(member)
    if await automod_db.remove_warning(guild.id, int(user_id), warning_id) and (
        user := await find_user(client, guild, int(user_id))
    ):
        warn_cog.log_removed(guild, user, member, 1)


@delete("/people/{user_id:str}", summary="Remove every warning one person has", status_code=200, responses=REFUSED)
async def clear_warnings(
    client: Client, guild: discord.Guild, member: discord.Member, user_id: UserId
) -> WarningsCleared:
    _moderator(member)
    cleared = await automod_db.clear_warnings(guild.id, int(user_id))
    if cleared and (user := await find_user(client, guild, int(user_id))):
        warn_cog.log_removed(guild, user, member, cleared)
    return WarningsCleared(cleared=cleared)


router = Router(
    "/guilds/{guild_id:str}/warnings",
    tags=["Warnings"],
    exception_handlers={SettingError: refused},
    dependencies={
        "guild": Provide(provide_guild, sync_to_thread=False),
        "member": Provide(provide_member, sync_to_thread=False),
    },
    route_handlers=[warning_ranking, warning_profile, give_warning, remove_warning, clear_warnings],
)
