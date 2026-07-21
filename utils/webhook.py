import discord
from core import Client

# Webhooks are cached per channel so each send avoids refetching them.
_cache: dict[int, discord.Webhook] = {}
_avatar: bytes | None = None


async def get_webhook(client: Client, channel: discord.TextChannel) -> discord.Webhook | None:
    """
    Gets the single reusable webhook for a channel, creating it once.

    The webhook is named after the bot & carries its avatar. Per-message identity
    should be applied via `username` & `avatar_url` on send.

    Args:
        client (:class:`Client`): The bot client.
        channel (:class:`discord.TextChannel`): The channel to own the webhook.
    """
    global _avatar
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
    """Drops the cached webhook for a channel."""
    _cache.pop(channel_id, None)


def cleanup(channel_ids: set[int]) -> None:
    """Drops cached webhooks for all the given channels."""
    for channel_id in channel_ids:
        _cache.pop(channel_id, None)
