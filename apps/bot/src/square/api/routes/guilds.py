import discord
from litestar import get
from litestar.di import Provide
from square.api.auth import provide_guild
from square.api.schemas import Guild, Settings, guild_out, settings_out
from square.core import Client
from square.db import cache


@get("/me/guilds", summary="Servers the user can manage", tags=["Guilds"])
async def my_guilds(client: Client, actor: int) -> list[Guild]:
    guilds = []
    for guild in client.guilds:
        member = guild.get_member(actor)
        if member and member.guild_permissions.manage_guild:
            guilds.append(guild_out(guild))
    return guilds


@get(
    "/guilds/{guild_id:str}/settings",
    summary="A server's settings",
    tags=["Guilds"],
    dependencies={"guild": Provide(provide_guild, sync_to_thread=False)},
)
async def guild_settings(guild: discord.Guild) -> Settings:
    return settings_out(cache.get(guild.id))
