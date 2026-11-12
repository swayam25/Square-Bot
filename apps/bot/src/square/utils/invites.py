import asyncio
import discord
from square.core import Client
from square.db import cache
from square.modules import Module
from square.utils.server_log import LogType
from typing import NamedTuple


class InviteUse(NamedTuple):
    code: str
    uses: int
    max_uses: int
    inviter_id: int | None

    @classmethod
    def from_invite(cls, invite: discord.Invite) -> InviteUse:
        return cls(invite.code, invite.uses or 0, invite.max_uses or 0, invite.inviter.id if invite.inviter else None)


_tracked: set[int] = set()
_cache: dict[int, dict[str, InviteUse]] = {}
_locks: dict[int, asyncio.Lock] = {}
_joins: dict[tuple[int, int], asyncio.Task[InviteUse | None]] = {}
_loaded = False


async def _tracked_guild_ids() -> set[int]:
    """
    Fetches the IDs of guilds that need invite tracking.

    NOTE: Any new feature showing inviters must be added here & in `_wants_tracking`.
    """
    return cache.guild_ids_with_log(LogType.MEMBERS.key) | cache.guild_ids_with_module(Module.INVITES)


async def _wants_tracking(guild_id: int) -> bool:
    return cache.enabled(guild_id, Module.INVITES) or cache.log_channel(guild_id, LogType.MEMBERS.key) is not None


async def _fetch(guild: discord.Guild) -> dict[str, InviteUse] | None:
    # Checked up front since failed requests count towards Discord's invalid request (IP ban) limit
    if not guild.me.guild_permissions.manage_guild:
        _cache.pop(guild.id, None)
        return None
    try:
        invites = {invite.code: InviteUse.from_invite(invite) for invite in await guild.invites()}
    except discord.HTTPException:
        _cache.pop(guild.id, None)
        return None
    _cache[guild.id] = invites
    return invites


async def _resolve(guild: discord.Guild) -> InviteUse | None:
    async with _locks.setdefault(guild.id, asyncio.Lock()):
        before = _cache.get(guild.id)
        after = await _fetch(guild)
        if before is None or after is None:
            return None
        used = [inv for code, inv in after.items() if inv.uses > (before[code].uses if code in before else 0)]
        if not used:  # Discord deletes an invite once it hits its max uses, so check the ones that vanished
            used = [
                inv
                for code, inv in before.items()
                if code not in after and inv.max_uses and inv.uses == inv.max_uses - 1
            ]
        return used[0] if len(used) == 1 else None


async def _load(client: Client) -> None:
    global _loaded
    if _loaded:  # on_ready fires again after reconnects
        return
    _loaded = True
    _tracked.update(await _tracked_guild_ids())
    semaphore = asyncio.Semaphore(5)

    async def fetch(guild: discord.Guild) -> None:
        async with semaphore:
            await _fetch(guild)

    await asyncio.gather(*(fetch(guild) for guild in client.guilds if guild.id in _tracked))


async def used_invite(member: discord.Member) -> InviteUse | None:
    if member.bot or member.guild.id not in _tracked:
        return None
    key = (member.guild.id, member.id)
    if key not in _joins:
        _joins[key] = asyncio.create_task(_resolve(member.guild))
        asyncio.get_running_loop().call_later(60, _joins.pop, key, None)
    return await _joins[key]


async def refresh(guild: discord.Guild) -> None:
    if await _wants_tracking(guild.id):
        _tracked.add(guild.id)
        await _fetch(guild)
    else:
        forget(guild.id)


def forget(guild_id: int) -> None:
    _tracked.discard(guild_id)
    _cache.pop(guild_id, None)
    _locks.pop(guild_id, None)


def setup(client: Client) -> None:

    async def on_ready():
        await _load(client)

    async def on_guild_join(guild: discord.Guild):
        await refresh(guild)

    async def on_guild_remove(guild: discord.Guild):
        forget(guild.id)

    async def on_invite_create(invite: discord.Invite):
        if invite.guild and (invites := _cache.get(invite.guild.id)) is not None:
            invites[invite.code] = InviteUse.from_invite(invite)

    async def on_log_channels_update(guild_id: int):
        if guild := client.get_guild(guild_id):
            await refresh(guild)

    for listener in (on_ready, on_guild_join, on_guild_remove, on_invite_create, on_log_channels_update):
        client.add_listener(listener)
