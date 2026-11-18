import asyncio
import datetime
import discord
from discord.ext import commands
from square.core import Client
from square.utils import config, mod_dm
from square.utils.emoji import emoji


class TimeoutEnds:
    """
    DMs members when their timeout runs out. Discord sends no event for that, so each one waits on its own task.

    Every timeout counts, also ones given outside Square. A timeout lifted early only gets the `/untimeout` DM, and
    one that ran out while the bot was offline gets none.
    """

    client: Client
    timeout_ends: dict[tuple[int, int], tuple[datetime.datetime, asyncio.Task]]

    def _watch_timeout(self, member: discord.Member) -> None:
        key = (member.guild.id, member.id)
        until = member.communication_disabled_until
        if (current := self.timeout_ends.get(key)) and current[0] == until:
            return
        if current:
            current[1].cancel()
            del self.timeout_ends[key]
        if until and until > discord.utils.utcnow():
            self.timeout_ends[key] = (until, asyncio.create_task(self._end_later(key, until)))

    async def _end_later(self, key: tuple[int, int], until: datetime.datetime) -> None:
        await discord.utils.sleep_until(until)
        self.timeout_ends.pop(key, None)
        guild = self.client.get_guild(key[0])
        member = guild.get_member(key[1]) if guild else None
        if member is None or member.communication_disabled_until != until:
            return
        dm = mod_dm.view(
            guild,
            "Your timeout ended",
            config.color.green,
            [],
            note=f"{emoji.success} You can send messages, react and join voice channels again.",
        )
        await mod_dm.send(member, dm)

    @commands.Cog.listener("on_ready")
    async def _watch_timeouts(self):
        for guild in self.client.guilds:
            for member in guild.members:
                if member.communication_disabled_until:
                    self._watch_timeout(member)

    @commands.Cog.listener("on_member_update")
    async def _timeout_changed(self, before: discord.Member, after: discord.Member):
        if before.communication_disabled_until != after.communication_disabled_until:
            self._watch_timeout(after)

    @commands.Cog.listener("on_member_remove")
    async def _timeout_left(self, member: discord.Member):
        if current := self.timeout_ends.pop((member.guild.id, member.id), None):
            current[1].cancel()

    def cog_unload(self):
        for _, task in self.timeout_ends.values():
            task.cancel()
        self.timeout_ends.clear()
