import discord
from litestar import Router, get
from litestar.di import Provide
from square.api.auth import provide_guild
from square.api.schemas import Channel, Guild, Role, channels_out, guild_out, roles_out
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


router = Router(
    "/guilds/{guild_id:str}",
    tags=["Guilds"],
    dependencies={"guild": Provide(provide_guild, sync_to_thread=False)},
    route_handlers=[guild_channels, guild_roles],
)
