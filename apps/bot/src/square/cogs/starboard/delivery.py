import aiohttp
import discord
import io
import logging
import re
from dataclasses import dataclass
from square.cogs.starboard import cards
from square.cogs.starboard.source import File, Source
from square.core import Client
from square.db.schema import StarboardPostTable, StarboardTable
from square.utils import fetch, webhook
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

REUPLOAD_MAX = 10 * 1024 * 1024
_CDN_HOSTS = {"cdn.discordapp.com", "media.discordapp.net"}
# Discord refuses webhook names containing these
_RESERVED = re.compile("clyde|discord", re.IGNORECASE)
_QUIET = discord.AllowedMentions.none()


@dataclass(frozen=True)
class Download:
    id: int
    name: str
    raw: bytes
    spoiler: bool

    def file(self) -> discord.File:
        """A new one per send, since a sent file is used up."""
        return discord.File(io.BytesIO(self.raw), filename=self.name, spoiler=self.spoiler)


def _uploads(downloads: list[Download]) -> cards.Uploads:
    return {download.id: download.name for download in downloads}


def stored(uploads: cards.Uploads) -> dict[str, str]:
    return {str(file_id): name for file_id, name in uploads.items()}


async def download(message: discord.Message) -> list[Download]:
    """Discord's file links expire, so files small enough are posted again with the card."""
    assert message.guild is not None
    targets: list[File] = [file for file in Source(message).files if urlsplit(file.url).hostname in _CDN_HOSTS]
    if not targets:
        return []
    budget = message.guild.filesize_limit
    found: list[Download] = []
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        for index, file in enumerate(targets):
            limit = min(REUPLOAD_MAX, budget)
            if (file.size or 0) > limit or (raw := await fetch.read(session, file.url, limit)) is None:
                continue
            budget -= len(raw)
            found.append(Download(file.id, f"{index}_{file.name.removeprefix('SPOILER_')}", raw, file.spoiler))
    return found


def board_channel(client: Client, board: StarboardTable) -> discord.TextChannel | None:
    channel = client.get_channel(board.channel_id)
    return channel if isinstance(channel, discord.TextChannel) else None


def _identity(author: discord.Member | discord.User) -> tuple[str, str] | None:
    for name in (author.display_name, author.name):
        if 1 <= len(name) <= 80 and not _RESERVED.search(name):
            return name, author.display_avatar.url
    return None


async def _webhook(client: Client, channel: discord.TextChannel) -> discord.Webhook | None:
    if not channel.permissions_for(channel.guild.me).manage_webhooks:
        return None
    return await webhook.get_webhook(client, channel)


async def send(
    client: Client, board: StarboardTable, message: discord.Message, tally: cards.Tally
) -> tuple[int, int | None, cards.Uploads] | None:
    """`(post ID, webhook ID or None, uploads)`, or None when it couldn't post."""
    if (channel := board_channel(client, board)) is None:
        return None
    downloads = await download(message)
    uploads = _uploads(downloads)
    if (identity := _identity(message.author)) and (hook := await _webhook(client, channel)):
        try:
            sent = await hook.send(
                view=cards.post_card(
                    board, message, tally, uploads, usable=cards.usable_emojis(client, channel, webhook=True)
                ),
                files=[found.file() for found in downloads],
                username=identity[0],
                avatar_url=identity[1],
                allowed_mentions=_QUIET,
                wait=True,
            )
            return sent.id, hook.id, uploads
        except discord.NotFound:
            webhook.invalidate(channel.id)
        except discord.HTTPException:
            log.warning("Starboard %d's webhook refused a post, the bot posts it instead", board.id, exc_info=True)
    try:
        sent = await channel.send(
            view=cards.post_card(
                board,
                message,
                tally,
                uploads,
                usable=cards.usable_emojis(client, channel, webhook=False),
                name=message.author.display_name,
            ),
            files=[found.file() for found in downloads],
            allowed_mentions=_QUIET,
        )
    except discord.Forbidden:
        return None
    except discord.HTTPException:
        log.warning("Couldn't post message %d on starboard %d", message.id, board.id, exc_info=True)
        return None
    return sent.id, None, uploads


async def edit(
    client: Client, board: StarboardTable, message: discord.Message, post: StarboardPostTable, tally: cards.Tally
) -> cards.Uploads | None:
    """The post's uploads after the edit, or None when it can't be edited any more and needs posting again."""
    channel = board_channel(client, board)
    if channel is None or post.post_id is None:
        return None
    kept = {int(file_id): name for file_id, name in post.uploaded.items()}
    # Edits can only drop files, so while every re-uploaded one is still there the post's copies still match
    fresh = not kept.keys() <= {file.id for file in Source(message).files}
    downloads = await download(message) if fresh else []
    uploads = _uploads(downloads) if fresh else kept
    replace = {"files": [found.file() for found in downloads], "attachments": []} if fresh else {}
    try:
        if post.webhook_id:
            hook = await _webhook(client, channel)
            if hook is None or hook.id != post.webhook_id:
                return None
            view = cards.post_card(
                board, message, tally, uploads, usable=cards.usable_emojis(client, channel, webhook=True)
            )
            await hook.edit_message(post.post_id, view=view, allowed_mentions=_QUIET, **replace)
        else:
            view = cards.post_card(
                board,
                message,
                tally,
                uploads,
                usable=cards.usable_emojis(client, channel, webhook=False),
                name=message.author.display_name,
            )
            # A partial message can't send files
            target = await channel.fetch_message(post.post_id) if fresh else channel.get_partial_message(post.post_id)
            await target.edit(view=view, allowed_mentions=_QUIET, **replace)
    except discord.NotFound:
        return None
    except discord.HTTPException:
        log.warning("Couldn't update starboard post %d", post.id, exc_info=True)
        return kept
    return uploads


async def delete(client: Client, board: StarboardTable, post_id: int, webhook_id: int | None) -> None:
    if (channel := board_channel(client, board)) is None:
        return
    if webhook_id and (hook := await _webhook(client, channel)) and hook.id == webhook_id:
        try:
            await hook.delete_message(post_id)
            return
        except discord.HTTPException:
            pass
    try:
        await channel.get_partial_message(post_id).delete()
    except discord.HTTPException:
        pass
