import discord
from litestar import Router, get
from litestar.di import Provide
from square.api.auth import provide_guild
from square.api.schemas import PlayerState, QueueState, player_out, queue_out
from square.core import Client


@get("/player", summary="What's playing right now. `/live` pushes the same shape as it changes")
async def music_player(client: Client, guild: discord.Guild) -> PlayerState:
    return player_out(client, guild)


@get("/queue", summary="The upcoming tracks. `/live` pushes the same shape as it changes")
async def music_queue(client: Client, guild: discord.Guild) -> QueueState:
    return queue_out(client, guild)


router = Router(
    "/guilds/{guild_id:str}/music",
    tags=["Music"],
    dependencies={"guild": Provide(provide_guild, sync_to_thread=False)},
    route_handlers=[music_player, music_queue],
)
