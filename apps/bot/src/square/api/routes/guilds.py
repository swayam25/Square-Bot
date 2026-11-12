import discord
from collections import Counter
from datetime import timedelta
from litestar import Router, get
from litestar.di import Provide
from square.api.auth import provide_guild
from square.api.schemas import (
    Channel,
    Guild,
    JoinDay,
    MemberJoins,
    Role,
    ServerStats,
    channels_out,
    guild_out,
    roles_out,
)
from square.core import Client


@get("/me/guilds", summary="Servers the user shares with Square", tags=["Guilds"])
async def my_guilds(client: Client, actor: int) -> list[Guild]:
    return [guild_out(guild, member) for guild in client.guilds if (member := guild.get_member(actor))]


@get("/channels", summary="A server's channels, for pickers")
async def guild_channels(guild: discord.Guild) -> list[Channel]:
    return channels_out(guild)


@get("/roles", summary="A server's roles, highest first, for pickers")
async def guild_roles(guild: discord.Guild) -> list[Role]:
    return roles_out(guild)


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
    route_handlers=[guild_channels, guild_roles, member_joins, server_stats],
)
