import discord
from core import Client
from core.view import DesignerView

# Webhooks are cached per (channel, name) so each log avoids refetching them.
_webhook_cache: dict[tuple[int, str], discord.Webhook] = {}


class LogType:
    """Log categories used to name the webhook (`{bot} - {log type}`)."""

    MOD = "Mod Log"
    MOD_CMD = "Mod Command Log"
    MESSAGE = "Message Log"
    MUSIC = "Music Log"
    TICKET = "Ticket Log"


async def _webhook(client: Client, channel: discord.abc.GuildChannel, log_type: str) -> discord.Webhook:
    """
    Gets the cached webhook for a channel and log type, creating it if needed.

    Parameters:
        client (Client): The bot client.
        channel (discord.abc.GuildChannel): The channel to own the webhook.
        log_type (str): The log category, used in the webhook name.
    """
    name = f"{client.user.name} - {log_type}"
    key = (channel.id, name)
    if key not in _webhook_cache:
        hook = discord.utils.get(await channel.webhooks(), name=name)
        if hook is None:
            hook = await channel.create_webhook(name=name, avatar=await client.user.display_avatar.read())
        _webhook_cache[key] = hook
    return _webhook_cache[key]


async def cleanup_guild(guild_id: int, channel_ids: set[int]) -> None:
    """Removes all cached webhooks belonging to the given guild's channels."""
    for key in [k for k in _webhook_cache if k[0] in channel_ids]:
        _webhook_cache.pop(key, None)


async def log(
    client: Client,
    channel: discord.abc.Messageable,
    log_type: str,
    view: DesignerView | None = None,
    *,
    file: discord.File | None = None,
    delete_after: float | None = None,
) -> None:
    """
    Sends a log message through a per-channel webhook named `{bot} - {log type}`.

    Parameters:
        client (Client): The bot client.
        channel (discord.abc.Messageable): The channel to log in (threads log via their parent).
        log_type (str): The log category, used in the webhook name.
        view (DesignerView | None): The components view to send.
        file (discord.File | None): Optional file attachment, sent on its own to stay valid alongside components.
        delete_after (float | None): Seconds before the log auto-deletes.
    """
    thread = discord.utils.MISSING
    target = channel
    if isinstance(channel, discord.Thread):
        thread, target = channel, channel.parent
    if target is None:
        return
    try:
        hook = await _webhook(client, target, log_type)
        if file is not None:
            msg = await hook.send(file=file, thread=thread, wait=True)
            if delete_after is not None:
                await msg.delete(delay=delete_after)
        if view is not None:
            msg = await hook.send(view=view, thread=thread, wait=True)
            if delete_after is not None:
                await msg.delete(delay=delete_after)
    except discord.NotFound:
        _webhook_cache.pop((target.id, f"{client.user.name} - {log_type}"), None)
