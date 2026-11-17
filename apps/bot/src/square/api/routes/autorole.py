import asyncio
import discord
from litestar import Router, delete, get, patch
from litestar.di import Provide
from msgspec import UNSET
from square.api import resolve
from square.api.auth import provide_guild
from square.api.refusals import REFUSED, refused
from square.api.resolve import SettingError
from square.api.schemas import AutorolePatch, AutoroleSettings, AutoroleUser, person_of
from square.api.users import find_user
from square.core import Client
from square.db import cache
from square.db.funcs import autorole as autorole_db
from typing import Any


def _role_ids(guild: discord.Guild, role_ids: list[int]) -> list[str]:
    return [str(role_id) for role_id in role_ids if guild.get_role(role_id)]


async def _settings(client: Client, guild: discord.Guild) -> AutoroleSettings:
    settings = cache.get(guild.id)
    user_ids = list(settings.autorole_users)
    users = await asyncio.gather(*(find_user(client, guild, user_id) for user_id in user_ids))
    return AutoroleSettings(
        role_ids=_role_ids(guild, settings.autorole_ids),
        bot_role_ids=_role_ids(guild, settings.autorole_bot_ids),
        split_bots=settings.autorole_split,
        users=[
            AutoroleUser(
                user=person_of(user_id, user),
                member=isinstance(user, discord.Member),
                role_ids=_role_ids(guild, settings.autorole_users[user_id]),
            )
            for user_id, user in zip(user_ids, users, strict=True)
        ],
        delay=settings.autorole_delay,
        wait_for_screening=settings.autorole_screening,
        sticky=settings.autorole_sticky,
        sticky_ignore_ids=_role_ids(guild, settings.autorole_sticky_ignore_ids),
        kept=await autorole_db.kept_count(guild.id) if settings.autorole_sticky else 0,
    )


def _givable(guild: discord.Guild, role_ids: list[str]) -> list[int]:
    roles = resolve.roles(guild, role_ids)
    for role in roles:
        if role.managed or role >= guild.me.top_role:
            raise SettingError(f"Square can't give out {role.mention}, it's above Square's role or managed.")
    return [role.id for role in roles]


@get("/", summary="Join roles, sticky roles and their timing")
async def get_autorole(client: Client, guild: discord.Guild) -> AutoroleSettings:
    return await _settings(client, guild)


@patch("/", summary="Change AutoRole", responses=REFUSED)
async def update_autorole(client: Client, guild: discord.Guild, data: AutorolePatch) -> AutoroleSettings:
    # Resolve and check everything first, so a refusal doesn't leave the change half applied
    values: dict[str, Any] = {}
    if data.role_ids is not UNSET:
        values["autorole_ids"] = _givable(guild, data.role_ids)
    if data.bot_role_ids is not UNSET:
        values["autorole_bot_ids"] = _givable(guild, data.bot_role_ids)
    if data.split_bots is not UNSET:
        values["autorole_split"] = data.split_bots
    if data.delay is not UNSET:
        values["autorole_delay"] = data.delay
    if data.wait_for_screening is not UNSET:
        values["autorole_screening"] = data.wait_for_screening
    if data.sticky is not UNSET:
        values["autorole_sticky"] = data.sticky
    if data.sticky_ignore_ids is not UNSET:
        values["autorole_sticky_ignore_ids"] = [role.id for role in resolve.roles(guild, data.sticky_ignore_ids)]
    users = None
    if data.users is not UNSET:
        if len({entry.user_id for entry in data.users}) != len(data.users):
            raise SettingError("Each person can only be listed once.")
        users = {int(entry.user_id): _givable(guild, entry.role_ids) for entry in data.users}
    if values.get("autorole_sticky") and not guild.me.guild_permissions.manage_roles:
        raise SettingError("Square needs the `Manage Roles` permission to give roles back.")

    if values:
        await autorole_db.save(guild.id, **values)
    if users is not None:
        await autorole_db.set_users(guild.id, users)
    return await _settings(client, guild)


@delete("/", summary="Reset AutoRole", status_code=200)
async def reset_autorole(client: Client, guild: discord.Guild) -> AutoroleSettings:
    """Nobody loses a role they already have. Roles kept for people who left are forgotten."""
    await autorole_db.reset(guild.id)
    return await _settings(client, guild)


router = Router(
    "/guilds/{guild_id:str}/autorole",
    tags=["AutoRole"],
    exception_handlers={SettingError: refused},
    dependencies={"guild": Provide(provide_guild, sync_to_thread=False)},
    route_handlers=[get_autorole, update_autorole, reset_autorole],
)
