import asyncio
import discord
from discord.ext import commands
from square.core import Client
from square.core.cog import Cog
from square.db import cache
from square.db.funcs import autorole as autorole_db
from square.modules import Module


def givable(guild: discord.Guild, role_ids: list[int]) -> list[discord.Role]:
    top = guild.me.top_role
    return [
        role
        for role_id in dict.fromkeys(role_ids)
        if (role := guild.get_role(role_id)) and not role.is_default() and not role.managed and role < top
    ]


class AutoRole(Cog, module=Module.AUTOROLE):
    def __init__(self, client: Client):
        self.client = client
        self._waiting: set[asyncio.Task] = set()

    def cog_unload(self):
        for task in self._waiting:
            task.cancel()

    async def _add(self, member: discord.Member, roles: list[discord.Role], reason: str) -> None:
        roles = [role for role in roles if role not in member.roles]
        if not roles:
            return
        try:
            await member.add_roles(*roles, reason=reason)
        except discord.Forbidden, discord.NotFound:
            pass

    async def _give(self, member: discord.Member) -> None:
        settings = cache.get(member.guild.id)
        role_ids = [
            *(settings.autorole_bot_ids if member.bot and settings.autorole_split else settings.autorole_ids),
            *settings.autorole_users.get(member.id, ()),
        ]
        await self._add(member, givable(member.guild, role_ids), "Auto role")

    async def _give_later(self, guild_id: int, member_id: int, delay: int) -> None:
        await asyncio.sleep(delay)
        guild = self.client.get_guild(guild_id)
        if guild and (member := guild.get_member(member_id)) and cache.enabled(guild_id, Module.AUTOROLE):
            await self._give(member)

    async def _schedule(self, member: discord.Member) -> None:
        delay = cache.get(member.guild.id).autorole_delay
        if delay <= 0:
            await self._give(member)
            return
        task = asyncio.create_task(self._give_later(member.guild.id, member.id, delay))
        self._waiting.add(task)
        task.add_done_callback(self._waiting.discard)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not cache.enabled(member.guild.id, Module.AUTOROLE):
            return
        settings = cache.get(member.guild.id)
        if settings.autorole_sticky and (kept := await autorole_db.take_roles(member.guild.id, member.id)):
            ignored = set(settings.autorole_sticky_ignore_ids)
            await self._add(
                member, [role for role in givable(member.guild, kept) if role.id not in ignored], "Sticky roles"
            )
        if settings.autorole_screening and member.pending and not member.bot:
            return
        await self._schedule(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if (
            before.pending
            and not after.pending
            and cache.enabled(after.guild.id, Module.AUTOROLE)
            and cache.get(after.guild.id).autorole_screening
        ):
            await self._schedule(after)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not cache.enabled(member.guild.id, Module.AUTOROLE) or not cache.get(member.guild.id).autorole_sticky:
            return
        role_ids = [role.id for role in member.roles if not role.is_default() and not role.managed]
        if role_ids:
            await autorole_db.keep_roles(member.guild.id, member.id, role_ids)


def setup(client: Client):
    client.add_cog(AutoRole(client))
