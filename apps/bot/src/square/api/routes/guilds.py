import discord
from collections import Counter
from datetime import UTC, datetime, timedelta
from litestar import Router, get
from litestar.di import Provide
from litestar.params import Parameter
from square.api.auth import provide_guild
from square.api.schemas import (
    Activity,
    ActivityDay,
    Channel,
    Guild,
    JoinDay,
    MemberJoins,
    Role,
    ServerStats,
    UserMatch,
    channels_out,
    guild_out,
    roles_out,
    user_match,
)
from square.api.users import find_user
from square.core import Client
from square.db.funcs import invites as invites_db
from square.db.funcs import tickets as tickets_db
from typing import Annotated


@get("/me/guilds", summary="Servers the user shares with Square", tags=["Guilds"])
async def my_guilds(client: Client, actor: int) -> list[Guild]:
    return [guild_out(guild, member) for guild in client.guilds if (member := guild.get_member(actor))]


@get("/channels", summary="A server's channels, for pickers")
async def guild_channels(guild: discord.Guild) -> list[Channel]:
    return channels_out(guild)


@get("/roles", summary="A server's roles, highest first, for pickers")
async def guild_roles(guild: discord.Guild) -> list[Role]:
    return roles_out(guild)


SEARCH_LIMIT = 25


@get("/members/search", summary="Find members by name, or anyone by exact ID")
async def search_members(
    client: Client,
    guild: discord.Guild,
    q: Annotated[str, Parameter(min_length=1, max_length=100, description="A name, username or Discord ID")],
) -> list[UserMatch]:
    text = q.strip().casefold()
    if text.isdigit() and 17 <= len(text) <= 20:
        user = await find_user(client, guild, int(text))
        return [user_match(user, isinstance(user, discord.Member))] if user else []

    starts: list[discord.Member] = []
    contains: list[discord.Member] = []
    for member in guild.members:
        name, shown = member.name.casefold(), member.display_name.casefold()
        if name.startswith(text) or shown.startswith(text):
            starts.append(member)
            # Prefix matches rank first, so once there are enough of them the rest of a big server can't change the answer
            if len(starts) >= SEARCH_LIMIT:
                break
        elif len(contains) < SEARCH_LIMIT and (text in name or text in shown):
            contains.append(member)
    found = sorted(starts, key=lambda m: m.display_name.casefold()) + sorted(
        contains, key=lambda m: m.display_name.casefold()
    )
    return [user_match(member, True) for member in found[:SEARCH_LIMIT]]


JOIN_DAYS = 30


@get("/stats/joins", summary="Members who joined each day over the last 30 days")
async def member_joins(guild: discord.Guild) -> MemberJoins:
    first = discord.utils.utcnow().date() - timedelta(days=JOIN_DAYS - 1)
    counts = Counter(day for member in guild.members if member.joined_at and (day := member.joined_at.date()) >= first)
    days = [first + timedelta(days=offset) for offset in range(JOIN_DAYS)]
    return MemberJoins(
        days=[JoinDay(date=day.isoformat(), count=counts[day]) for day in days],
        members=guild.member_count or 0,
    )


@get("/stats/activity", summary="Tickets and tracked invites each day over the last 30 days")
async def activity(guild: discord.Guild) -> Activity:
    first = discord.utils.utcnow().date() - timedelta(days=JOIN_DAYS - 1)
    since = datetime.combine(first, datetime.min.time(), UTC)
    opened, closed = await tickets_db.ticket_times_since(guild.id, since)
    invited, left = await invites_db.invite_times_since(guild.id, since)

    def per_day(times: list[datetime]) -> Counter:
        return Counter(time.astimezone(UTC).date() for time in times)

    counts = [per_day(times) for times in (opened, closed, invited, left)]
    days = [first + timedelta(days=offset) for offset in range(JOIN_DAYS)]
    return Activity(
        days=[
            ActivityDay(
                date=day.isoformat(),
                tickets_opened=counts[0][day],
                tickets_closed=counts[1][day],
                invited=counts[2][day],
                left=counts[3][day],
            )
            for day in days
        ]
    )


@get("/stats/server", summary="Member, channel and boost counts from the bot's cache")
async def server_stats(guild: discord.Guild) -> ServerStats:
    humans = [member for member in guild.members if not member.bot]
    return ServerStats(
        humans=len(humans),
        bots=len(guild.members) - len(humans),
        in_voice=sum(member.voice is not None and member.voice.channel is not None for member in humans),
        boosts=guild.premium_subscription_count or 0,
        boost_level=guild.premium_tier,
        text_channels=len(guild.text_channels),
        voice_channels=len(guild.voice_channels) + len(guild.stage_channels),
        roles=len(guild.roles) - 1,
        created_at=round(guild.created_at.timestamp() * 1000),
    )


router = Router(
    "/guilds/{guild_id:str}",
    tags=["Guilds"],
    dependencies={"guild": Provide(provide_guild, sync_to_thread=False)},
    route_handlers=[guild_channels, guild_roles, search_members, member_joins, activity, server_stats],
)
