import discord
import enum
from core import Client
from core.view import DesignerView
from utils import webhook


class LogType(enum.Enum):
    """
    Log categories.

    Each member holds a `key` (stored in the database) and a `label`
    (shown as the webhook sender name suffix).
    """

    MODERATION = ("moderation", "Moderation Log")
    MEMBERS = ("members", "Member Log")
    MESSAGES = ("messages", "Message Log")
    CHANNELS = ("channels", "Channel Log")
    ROLES = ("roles", "Role Log")
    SERVER = ("server", "Server Log")
    VOICE = ("voice", "Voice Log")
    INVITES = ("invites", "Invite Log")
    AUTOMOD = ("automod", "AutoMod Log")
    TICKETS = ("tickets", "Ticket Log")

    def __init__(self, key: str, label: str):
        self.key = key
        self.label = label

    def __str__(self) -> str:
        return self.label

    @classmethod
    def from_label(cls, label: str) -> LogType:
        """Resolves a log type from its label (e.g. "Moderation Log")."""
        return next(log_type for log_type in cls if log_type.label == label)


async def cleanup_guild(guild_id: int, channel_ids: set[int]) -> None:
    """Removes all cached webhooks belonging to the given guild's channels."""
    webhook.cleanup(channel_ids)


async def log(
    client: Client,
    channel: discord.abc.Messageable,
    log_type: LogType,
    view: DesignerView | None = None,
    *,
    file: discord.File | None = None,
    delete_after: float | None = None,
) -> None:
    """
    Sends a log message through the channel's single shared webhook, renamed per message to `{bot} - {log type}`.

    Parameters:
        client (Client): The bot client.
        channel (discord.abc.Messageable): The channel to log in (threads log via their parent).
        log_type (LogType): The log category, shown as the sender name.
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

    async def send(hook: discord.Webhook) -> None:
        username = f"{client.user.name} - {log_type}"
        if file is not None:
            msg = await hook.send(file=file, thread=thread, username=username, wait=True)
            if delete_after is not None:
                await msg.delete(delay=delete_after)
        if view is not None:
            msg = await hook.send(view=view, thread=thread, username=username, wait=True)
            if delete_after is not None:
                await msg.delete(delay=delete_after)

    hook = await webhook.get_webhook(client, target)
    if hook is None:
        return
    try:
        await send(hook)
    except discord.NotFound:
        # Webhook was deleted externally, recreate & retry once
        webhook.invalidate(target.id)
        hook = await webhook.get_webhook(client, target)
        if hook is None:
            return
        try:
            await send(hook)
        except discord.HTTPException:
            pass
