import discord
import hmac
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.exceptions import (
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
    ServiceUnavailableException,
)
from litestar.handlers import BaseRouteHandler
from litestar.params import Parameter
from litestar.types import Guard
from square.api.resolve import SettingError
from square.core import Client
from square.db import cache
from square.modules import Module
from typing import Annotated


def secret_guard(secret: str) -> Guard:
    expected = f"Bearer {secret}".encode()

    def guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        # Constant-time, so response timing can't leak the secret a byte at a time
        if not hmac.compare_digest(connection.headers.get("authorization", "").encode(), expected):
            raise NotAuthorizedException()

    return guard


def module_guard(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    """Refuses a route marked with `opt={"module": ...}` while that module is off, like its commands do."""
    module: Module | None = handler.opt.get("module")
    guild_id, actor = connection.path_params.get("guild_id"), connection.headers.get("x-actor-id", "")
    if not module or not guild_id or cache.enabled(int(guild_id), module):
        return
    client: Client | None = connection.app.state.client
    guild = client.get_guild(int(guild_id)) if client else None
    # Outsiders fall through to the usual "Guild not found", so this never reveals a server's modules to them
    if guild and actor.isdigit() and guild.get_member(int(actor)):
        raise SettingError(f"{module.label} is turned off in this server.")


def provide_client(state: State) -> Client:
    client: Client | None = state.client
    if client is None or not client.is_ready():
        raise ServiceUnavailableException("Square is still starting. Try again in a moment.")
    return client


def provide_actor(
    actor_id: Annotated[
        str,
        Parameter(
            header="x-actor-id",
            pattern=r"^\d{17,20}$",
            description="The signed-in Discord user the dashboard is acting for",
        ),
    ],
) -> int:
    return int(actor_id)


GuildId = Annotated[str, Parameter(pattern=r"^\d{17,20}$", description="A Discord ID")]


def provide_member_guild(client: Client, guild_id: GuildId, actor: int) -> discord.Guild:
    guild = client.get_guild(int(guild_id))
    # One answer for "bot isn't there" and "you aren't there", so neither is revealed
    if guild is None or guild.get_member(actor) is None:
        raise NotFoundException("Guild not found")
    return guild


def provide_guild(client: Client, guild_id: GuildId, actor: int) -> discord.Guild:
    guild = provide_member_guild(client, guild_id, actor)
    member = guild.get_member(actor)
    if member is None or not member.guild_permissions.manage_guild:
        raise PermissionDeniedException("Manage Server permission required")
    return guild


def provide_member(guild: discord.Guild, actor: int) -> discord.Member:
    if (member := guild.get_member(actor)) is None:
        raise NotFoundException("Guild not found")
    return member
