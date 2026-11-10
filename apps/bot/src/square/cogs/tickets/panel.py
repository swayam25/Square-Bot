"""
The "Open a ticket" panel's lifecycle, kept like the music card.

It's adopted on every startup so it always shows the current layout, reposted when someone deletes it, and moved back
to the bottom of its channel when anyone posts under it.
"""

import asyncio
import discord
from collections.abc import Collection
from square.cogs.tickets import cards
from square.core import Client
from square.db import cache
from square.db.funcs.tickets import set_ticket_panel
from square.music.utils import delete_quietly

# Seconds of quiet before the panel moves back under new messages, so a burst costs one repost instead of one each
STICK_DELAY = 3

_sticking: dict[int, asyncio.Task] = {}


def is_panel_channel(guild_id: int, channel_id: int) -> bool:
    """A plain dict lookup: this runs for every message the bot sees."""
    return cache.get(guild_id).ticket_panel_channel_id == channel_id


async def post(channel: discord.TextChannel) -> discord.Message:
    """
    Posts a fresh panel and drops the previous one.

    The new ID is saved before the old message is deleted, so that delete never looks like someone removing the panel.
    """
    old_id = cache.get(channel.guild.id).ticket_panel_message_id
    message = await channel.send(view=cards.panel())
    await set_ticket_panel(channel.guild.id, channel.id, message.id)
    if old_id:
        await delete_quietly(channel.get_partial_message(old_id))
    return message


async def unbind(guild_id: int) -> None:
    await set_ticket_panel(guild_id, None, None)
    if task := _sticking.pop(guild_id, None):
        task.cancel()


async def adopt(client: Client, guild_id: int) -> None:
    """Brings a guild's panel up to date: edited in place when it's still the newest message, reposted otherwise."""
    settings = cache.get(guild_id)
    channel_id, message_id = settings.ticket_panel_channel_id, settings.ticket_panel_message_id
    if channel_id is None:
        return
    try:
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
    except discord.NotFound, discord.Forbidden:
        await unbind(guild_id)  # Deleted, or hidden from the bot, while it was offline
        return
    except discord.HTTPException:
        return
    if not isinstance(channel, discord.TextChannel):
        return
    if message_id and channel.last_message_id == message_id:
        try:
            await channel.get_partial_message(message_id).edit(view=cards.panel())
            return
        except discord.NotFound:
            pass
        except discord.HTTPException:
            return
    try:
        await post(channel)
    except discord.HTTPException:
        pass  # Lost send access. The settings page still shows the channel, so it can be fixed from there.


async def adopt_all(client: Client) -> None:
    """Adopts every guild's panel, one at a time so a broken guild can't take the rest down."""
    for guild_id in cache.guild_ids_with_ticket_panel():
        try:
            await adopt(client, guild_id)
        except Exception:
            continue


def stick(channel: discord.TextChannel) -> None:
    """Moves the panel back under new messages once the channel goes quiet."""
    if task := _sticking.pop(channel.guild.id, None):
        task.cancel()
    _sticking[channel.guild.id] = asyncio.create_task(_stick_later(channel))


async def _stick_later(channel: discord.TextChannel) -> None:
    await asyncio.sleep(STICK_DELAY)
    # Out of the dict before posting, so a message arriving mid-post schedules a new move instead of cancelling this one
    _sticking.pop(channel.guild.id, None)
    if is_panel_channel(channel.guild.id, channel.id):
        try:
            await post(channel)
        except discord.HTTPException:
            pass


async def repost_if_deleted(client: Client, guild_id: int, message_ids: Collection[int]) -> None:
    settings = cache.get(guild_id)
    if settings.ticket_panel_message_id not in message_ids or settings.ticket_panel_channel_id is None:
        return
    channel = client.get_channel(settings.ticket_panel_channel_id)
    if isinstance(channel, discord.TextChannel):
        try:
            await post(channel)
        except discord.HTTPException:
            pass
