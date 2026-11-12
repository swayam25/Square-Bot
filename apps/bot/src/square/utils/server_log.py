import discord
import enum
from square.core import Client
from square.core.view import DesignerView
from square.db import cache
from square.db.funcs.logs import remove_log_channel
from square.utils import webhook


class LogType(enum.Enum):
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
        return next(log_type for log_type in cls if log_type.label == label)


async def cleanup_guild(guild_id: int, channel_ids: set[int]) -> None:
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
        webhook.invalidate(target.id)
        hook = await webhook.get_webhook(client, target)
        if hook is None:
            return
        try:
            await send(hook)
        except discord.HTTPException:
            pass


async def _channel(client: Client, guild: discord.Guild, log_type: LogType) -> discord.abc.Messageable | None:
    channel_id = cache.log_channel(guild.id, log_type.key)
    if channel_id is None:
        return None
    channel = guild.get_channel_or_thread(channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except discord.NotFound:
            # Only a deleted channel drops the setting; a Discord outage must not wipe log config
            await remove_log_channel(guild.id, log_type.key)
            client.dispatch("log_channels_update", guild.id)
            return None
    return channel if isinstance(channel, discord.abc.Messageable) else None


async def _hook(
    client: Client, channel: discord.abc.Messageable
) -> tuple[discord.Webhook, discord.abc.Snowflake] | None:
    thread, target = discord.utils.MISSING, channel
    if isinstance(channel, discord.Thread):
        thread, target = channel, channel.parent
    if not isinstance(target, discord.TextChannel):
        return None
    hook = await webhook.get_webhook(client, target)
    return (hook, thread) if hook else None


async def send(
    client: Client,
    guild: discord.Guild,
    log_type: LogType,
    view: DesignerView | None = None,
    *,
    file: discord.File | None = None,
) -> None:
    if channel := await _channel(client, guild, log_type):
        await log(client, channel, log_type, view, file=file)


async def post(
    client: Client,
    guild: discord.Guild,
    log_type: LogType,
    view: DesignerView,
    *,
    file: discord.File | None = None,
) -> int | None:
    """
    Sends one log message that can be edited later, returning its ID.

    Unlike `send`, a file goes in the same message, so the view must show it with `ui.File("attachment://name")`.
    """
    if not (channel := await _channel(client, guild, log_type)) or not (found := await _hook(client, channel)):
        return None
    hook, thread = found
    try:
        message = await hook.send(
            view=view,
            file=file or discord.utils.MISSING,
            thread=thread,
            username=f"{client.user.name if client.user else 'Square'} - {log_type}",
            wait=True,
        )
    except discord.HTTPException:
        return None
    return message.id


async def edit(
    client: Client,
    guild: discord.Guild,
    log_type: LogType,
    message_id: int,
    view: DesignerView,
    *,
    file: discord.File | None = None,
) -> bool:
    """Edits a log message sent with `post`. Returns False when it's gone, e.g. deleted or the log channel changed."""
    if not (channel := await _channel(client, guild, log_type)) or not (found := await _hook(client, channel)):
        return False
    hook, thread = found
    try:
        await hook.edit_message(message_id, view=view, file=file or discord.utils.MISSING, thread=thread)
    except discord.HTTPException:
        return False
    return True
