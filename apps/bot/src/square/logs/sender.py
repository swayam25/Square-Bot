import asyncio
import discord
from collections import deque
from dataclasses import dataclass, field
from square.core import Client
from square.core.view import DesignerView
from square.db import cache
from square.db.funcs.logs import remove_log_channel
from square.logs.card import Entry, cost, file_count, render, swatch_file, upload_size
from square.logs.catalog import EVENTS, UNFILTERED, Event, Log
from square.utils import webhook

# The first event waits briefly for others from the same moment, the rest of a burst is batched every FLUSH_DELAY
GATHER_DELAY = 0.25
FLUSH_DELAY = 1.5
MAX_QUEUE = 300
MAX_COMPONENTS = 40
MAX_TEXT = 4000
MAX_FILES = 10


@dataclass
class _Outbox:
    guild_id: int
    log: Log
    queue: deque[Entry] = field(default_factory=deque)
    dropped: int = 0
    task: asyncio.Task | None = None


_outboxes: dict[tuple[int, Log], _Outbox] = {}
_client: Client | None = None


def bind(client: Client) -> None:
    global _client
    _client = client


def ignored(
    guild: discord.Guild, channel_id: int | None = None, member: discord.Member | None = None, bot: bool = False
) -> bool:
    """Whether the server's ignore settings hide something from the Members, Messages, Voice and Server logs."""
    settings = cache.get(guild.id)
    if bot and settings.log_skip_bots:
        return True
    if (
        member
        and settings.log_ignored_role_ids
        and any(role.id in settings.log_ignored_role_ids for role in member.roles)
    ):
        return True
    if channel_id and settings.log_ignored_channel_ids:
        channel = guild.get_channel_or_thread(channel_id)
        places = {channel_id, getattr(channel, "category_id", None)}
        if isinstance(channel, discord.Thread) and channel.parent:
            places |= {channel.parent.id, channel.parent.category_id}
        return any(place in settings.log_ignored_channel_ids for place in places if place)
    return False


def wanted(
    guild: discord.Guild,
    event: Event,
    channel_id: int | None = None,
    member: discord.Member | None = None,
    bot: bool = False,
) -> bool:
    log = EVENTS[event]
    if cache.log_channel(guild.id, log) is None or event in cache.get(guild.id).log_disabled_events:
        return False
    return log in UNFILTERED or not ignored(guild, channel_id, member, bot)


def emit(guild: discord.Guild, entry: Entry) -> None:
    """Queues `entry` for its log channel. Never waits on Discord, so listeners stay fast."""
    log = EVENTS[entry.event]
    channel_id = cache.log_channel(guild.id, log)
    if channel_id is None or not wanted(guild, entry.event, entry.channel_id, entry.member, entry.bot):
        return
    box = _outboxes.setdefault((channel_id, log), _Outbox(guild.id, log))
    if len(box.queue) >= MAX_QUEUE:
        box.queue.popleft()
        box.dropped += 1
    box.queue.append(entry)
    if box.task is None or box.task.done():
        box.task = asyncio.create_task(_flush(channel_id, box))


def _take(box: _Outbox, max_bytes: int) -> list[Entry]:
    batch: list[Entry] = []
    components = text = files = size = 0
    while box.queue:
        parts, chars = cost(box.queue[0])
        count, bytes_ = file_count(box.queue[0]), upload_size(box.queue[0])
        if batch and (
            components + parts > MAX_COMPONENTS
            or text + chars > MAX_TEXT
            or files + count > MAX_FILES
            or size + bytes_ > max_bytes
        ):
            break
        batch.append(box.queue.popleft())
        components, text, files, size = components + parts, text + chars, files + count, size + bytes_
    return batch


def _unique(file: discord.File, taken: set[str]) -> None:
    """Cards batched into one message can carry files with the same name, which `attachment://` can't tell apart."""
    name, number = file.filename, 1
    while name in taken:
        name, number = f"{number}_{file.filename}", number + 1
    file.filename = name
    taken.add(name)


async def _send_batch(guild: discord.Guild, box: _Outbox) -> None:
    batch = _take(box, guild.filesize_limit)
    dropped, box.dropped = box.dropped, 0
    items: list[discord.ui.Item] = []
    files: list[discord.File] = []
    taken: set[str] = set()
    for index, entry in enumerate(batch):
        swatch = None
        if entry.swatch is not None:
            swatch = f"swatch-{index}.png"
            files.append(swatch_file(entry.swatch, swatch))
            taken.add(swatch)
        for file in [entry.file, *(upload.file for upload in entry.uploads)]:
            if file:
                _unique(file, taken)
                files.append(file)
        items.extend(render(entry, swatch))
    if dropped:
        items.append(discord.ui.TextDisplay(f"-# {dropped} more events skipped, too many at once."))
    await _deliver(guild, box.log, DesignerView(*items), files)


async def _flush(channel_id: int, box: _Outbox) -> None:
    await asyncio.sleep(GATHER_DELAY)
    while box.queue:
        guild = _client.get_guild(box.guild_id) if _client else None
        if guild is None:
            box.queue.clear()
            break
        while box.queue:
            await _send_batch(guild, box)
        await asyncio.sleep(FLUSH_DELAY)
    _outboxes.pop((channel_id, box.log), None)


async def _destination(guild: discord.Guild, log: Log) -> discord.abc.Messageable | None:
    channel_id = cache.log_channel(guild.id, log)
    if channel_id is None or _client is None:
        return None
    channel = guild.get_channel_or_thread(channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except discord.NotFound:
            # Only a deleted channel drops the setting, a Discord outage must not wipe it
            await remove_log_channel(guild.id, log)
            _client.dispatch("log_channels_update", guild.id)
            return None
        except discord.HTTPException:
            return None
    return channel if isinstance(channel, discord.abc.Messageable) else None


async def _hook(channel: discord.abc.Messageable) -> tuple[discord.Webhook, discord.abc.Snowflake] | None:
    thread, target = discord.utils.MISSING, channel
    if isinstance(channel, discord.Thread):
        thread, target = channel, channel.parent
    if not isinstance(target, discord.TextChannel) or _client is None:
        return None
    hook = await webhook.get_webhook(_client, target)
    return (hook, thread) if hook else None


def _username(log: Log) -> str:
    return f"{_client.user.name if _client and _client.user else 'Square'} - {log.label} Log"


async def _deliver(
    guild: discord.Guild, log: Log, view: DesignerView, files: list[discord.File], *, retry: bool = True
) -> discord.WebhookMessage | None:
    if not (channel := await _destination(guild, log)) or not (found := await _hook(channel)):
        return None
    hook, thread = found
    try:
        return await hook.send(
            view=view, files=files or discord.utils.MISSING, thread=thread, username=_username(log), wait=True
        )
    except discord.NotFound:
        webhook.invalidate(getattr(channel, "parent_id", None) or channel.id)
        if retry:
            for file in files:
                file.reset()
            return await _deliver(guild, log, view, files, retry=False)
    except discord.HTTPException:
        pass
    return None


async def post(guild: discord.Guild, log: Log, view: DesignerView, *, file: discord.File | None = None) -> int | None:
    """Sends one log message right away, skipping the queue, and returns its ID so it can be edited later."""
    message = await _deliver(guild, log, view, [file] if file else [])
    return message.id if message else None


async def edit(
    guild: discord.Guild, log: Log, message_id: int, view: DesignerView, *, file: discord.File | None = None
) -> bool:
    """Edits a message sent with `post`. False when it's gone, e.g. deleted or the log channel changed."""
    if not (channel := await _destination(guild, log)) or not (found := await _hook(channel)):
        return False
    hook, thread = found
    try:
        await hook.edit_message(message_id, view=view, file=file or discord.utils.MISSING, thread=thread)
    except discord.HTTPException:
        return False
    return True


def forget(guild_id: int) -> None:
    for key in [key for key, box in _outboxes.items() if box.guild_id == guild_id]:
        box = _outboxes.pop(key)
        box.queue.clear()
