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
from square.core import Client
from typing import Annotated


def secret_guard(secret: str) -> Guard:
    """Lets a request through only with `Authorization: Bearer <secret>`, so only the dashboard server can call the API."""
    expected = f"Bearer {secret}".encode()

    def guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        # Constant-time, so response timing can't leak the secret a byte at a time
        if not hmac.compare_digest(connection.headers.get("authorization", "").encode(), expected):
            raise NotAuthorizedException()

    return guard


def provide_client(state: State) -> Client:
    client: Client | None = state.client
    if client is None or not client.is_ready():
        raise ServiceUnavailableException("The bot is still starting")
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


def provide_guild(
    client: Client,
    guild_id: Annotated[str, Parameter(pattern=r"^\d{17,20}$", description="A Discord ID")],
    actor: int,
) -> discord.Guild:
    """The guild, if the actor can manage it. Same rule as Discord: Manage Server, which admins and the owner have."""
    guild = client.get_guild(int(guild_id))
    member = guild.get_member(actor) if guild else None
    # One answer for "bot isn't there" and "you aren't there", so neither is revealed
    if guild is None or member is None:
        raise NotFoundException("Guild not found")
    if not member.guild_permissions.manage_guild:
        raise PermissionDeniedException("Manage Server permission required")
    return guild
