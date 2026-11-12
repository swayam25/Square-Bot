import asyncio
import discord
from square.core import Client

_cache: dict[int, discord.Webhook] = {}
_locks: dict[int, asyncio.Lock] = {}
_avatar: bytes | None = None


async def get_webhook(client: Client, channel: discord.TextChannel) -> discord.Webhook | None:
    global _avatar
    if webhook := _cache.get(channel.id):
        return webhook
    # One lookup per channel at a time, or a burst of logs into a new channel creates a webhook each
    async with _locks.setdefault(channel.id, asyncio.Lock()):
        if webhook := _cache.get(channel.id):
            return webhook
        try:
            webhooks = await channel.webhooks()
            webhook = next(
                (wh for wh in webhooks if wh.name == client.user.name and wh.user and wh.user.id == client.user.id),
                None,
            )
            if not webhook:
                if _avatar is None:
                    _avatar = await client.user.display_avatar.read()
                webhook = await channel.create_webhook(name=client.user.name, avatar=_avatar)
        except discord.HTTPException:
            return None
        _cache[channel.id] = webhook
        return webhook


def invalidate(channel_id: int) -> None:
    _cache.pop(channel_id, None)


def cleanup(channel_ids: set[int]) -> None:
    for channel_id in channel_ids:
        _cache.pop(channel_id, None)
        _locks.pop(channel_id, None)
