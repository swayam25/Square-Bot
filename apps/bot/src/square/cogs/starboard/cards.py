import discord
import re
from collections.abc import Callable
from discord import components, ui
from square.cogs.starboard.source import Preview, Source, media_url
from square.core.view import DesignerView
from square.db.schema import StarboardPostTable, StarboardTable
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count
from typing import Any, NamedTuple

TEXT_LIMIT = 4000
COMPONENT_LIMIT = 40
GALLERY_MAX = 10
CONTENT_MAX = 2000
EMBED_TEXT_MAX = 600
FIELD_MAX = 200
FIELDS_SHOWN = 6
REPLY_MAX = 120

_URL_ONLY = re.compile(r"^<?https?://\S+>?$")
_CUSTOM_EMOJI = re.compile(r"<a?:\w+:(\d+)> ?")

Uploads = dict[int, str]
"""Source file IDs mapped to the names they were re-uploaded under."""


class Tally(NamedTuple):
    points: int
    emoji: str  # The vote emoji the points came from


def jump_url(guild_id: int, channel_id: int, message_id: int) -> str:
    return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"


def vote_emoji(board: StarboardTable) -> str:
    return board.emojis[0] if board.emojis else "⭐"


def stored_tally(post: StarboardPostTable) -> Tally:
    return Tally(post.score, post.emoji or vote_emoji(post.board))


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: max(limit - 1, 0)].rstrip() + "…"


def _size(item: ui.ViewItem) -> tuple[int, int]:
    """`(characters, components)` an item takes, counted from what Discord receives."""

    def walk(data: dict[str, Any]) -> tuple[int, int]:
        text, count = len(data.get("content") or ""), 1
        for child in [*data.get("components", []), *([data["accessory"]] if data.get("accessory") else [])]:
            more_text, more = walk(child)
            text, count = text + more_text, count + more
        return text, count

    return walk(item.to_component_dict())


class _Budget:
    def __init__(self, *reserved: ui.ViewItem):
        self.text, self.components = TEXT_LIMIT, COMPONENT_LIMIT
        for item in reserved:
            self.take(item)

    def take(self, item: ui.ViewItem) -> bool:
        text, count = _size(item)
        if text > self.text or count > self.components:
            return False
        self.text, self.components = self.text - text, self.components - count
        return True


def _media_url(media: components.UnfurledMediaItem, uploads: Uploads) -> str:
    uploaded = uploads.get(int(media.attachment_id)) if media.attachment_id else None
    return f"attachment://{uploaded}" if uploaded else media.url


def _attachments(source: Source, uploads: Uploads) -> tuple[list[discord.MediaGalleryItem], list[ui.ViewItem]]:
    shown: list[discord.MediaGalleryItem] = []
    files: list[ui.ViewItem] = []
    links: list[str] = []
    for file in [] if source.v2 else source.files:
        uploaded = uploads.get(file.id)
        url = f"attachment://{uploaded}" if uploaded else file.url
        if file.media:
            shown.append(discord.MediaGalleryItem(url=url, spoiler=file.spoiler))
        elif uploaded:
            files.append(ui.File(url, spoiler=file.spoiler))
        else:
            links.append(f"[{file.name}]({file.url})")
    for preview in source.media_previews:
        if url := media_url(preview.embed):
            shown.append(discord.MediaGalleryItem(url=url, description=preview.embed.title))
        shown += [discord.MediaGalleryItem(url=more) for more in preview.more]
    for sticker in source.stickers:
        if sticker.format is not discord.StickerFormatType.lottie:
            shown.append(discord.MediaGalleryItem(url=sticker.url, description=sticker.name))
    if links:
        files.append(ui.TextDisplay("-# " + " · ".join(links)))
    return shown[:GALLERY_MAX], files


def _reply(message: discord.Message) -> str | None:
    if not message.reference or message.snapshots:
        return None
    replied = message.reference.resolved
    if isinstance(replied, discord.Message):
        text = " ".join(replied.content.split()) or "*Click to see attachment*"
        return f"-# ↪ Replying to {replied.author.mention}: {clip(text, REPLY_MAX)}"
    if isinstance(replied, discord.DeletedReferencedMessage):
        return "-# ↪ Replying to a deleted message"
    return None


def _poll(poll: discord.Poll) -> str:
    answers = "\n".join(f"- {answer.text or ''} · `{fmt_count(answer.count or 0)}`" for answer in poll.answers)
    return f"**{poll.question.text}**\n{answers}"


def _body(source: Source, name: str | None) -> str:
    """Everything the message says. `name` heads it when the post can't carry the author's name itself."""
    lines = [f"### {discord.utils.escape_markdown(name)}"] if name else []
    if reply := _reply(source.message):
        lines.append(reply)
    if source.forwarded:
        lines.append("-# ↪ Forwarded")
    content = source.content.strip()
    # Discord hides a link whose only job is showing a GIF or an image, so the card does too
    if content and not (_URL_ONLY.match(content) and source.media_previews):
        lines.append(clip(content, CONTENT_MAX))
    if source.poll:
        lines.append(_poll(source.poll))
    return "\n".join(lines)


def embed_box(preview: Preview) -> ui.Container | None:
    embed = preview.embed
    lines = []
    if embed.provider and embed.provider.name:
        lines.append(f"-# {embed.provider.name}")
    if embed.author and embed.author.name:
        author = f"[{embed.author.name}]({embed.author.url})" if embed.author.url else embed.author.name
        lines.append(f"-# {author}")
    if embed.title:
        lines.append(f"**[{embed.title}]({embed.url})**" if embed.url else f"**{embed.title}**")
    if embed.description:
        lines.append(clip(embed.description, EMBED_TEXT_MAX))
    lines += [f"**{field.name}**\n{clip(field.value, FIELD_MAX)}" for field in embed.fields[:FIELDS_SHOWN]]
    footer = [embed.footer.text] if embed.footer and embed.footer.text else []
    if embed.timestamp:
        footer.append(discord.utils.format_dt(embed.timestamp, "f"))
    footer_line = "-# " + " · ".join(footer) if footer else None

    image = embed.image.url if embed.image and embed.image.url else None
    thumbnail = embed.thumbnail.url if embed.thumbnail and embed.thumbnail.url else None
    # A video's thumbnail is its poster, so it shows big like Discord does
    if embed.video and embed.video.url and not image:
        image, thumbnail = thumbnail, None
    images = [image, *preview.more] if image else preview.more
    # The footer closes the embed, so it only joins the text when no pictures come between
    if footer_line and not images:
        lines.append(footer_line)
        footer_line = None
    if not lines and not images:
        return None

    box = ui.Container(color=embed.color.value if embed.color else None)
    if lines:
        text = ui.TextDisplay("\n".join(lines))
        box.add_item(ui.Section(text, accessory=ui.Thumbnail(thumbnail)) if thumbnail else text)
    if images:
        box.add_item(ui.MediaGallery(*(discord.MediaGalleryItem(url=url) for url in images[:GALLERY_MAX])))
    if footer_line:
        box.add_item(ui.TextDisplay(footer_line))
    return box


def _rebuild(item: components.Component | None, uploads: Uploads) -> list[ui.ViewItem]:
    """
    A fresh copy of one Components V2 part. Types it doesn't know are left out.

    Buttons are dropped too: the post links to the message, which is where they belong.
    """
    match item:
        case components.TextDisplay():
            return [ui.TextDisplay(item.content)]
        case components.Separator():
            return [ui.Separator(divider=item.divider, spacing=item.spacing)]
        case components.Thumbnail():
            return [ui.Thumbnail(_media_url(item.media, uploads), description=item.description, spoiler=item.spoiler)]
        case components.MediaGallery():
            shown = [
                discord.MediaGalleryItem(
                    _media_url(entry.media, uploads), description=entry.description, spoiler=entry.spoiler
                )
                for entry in item.items
            ]
            return [ui.MediaGallery(*shown)] if shown else []
        case components.FileComponent():
            # A file component can only show a file attached to the same message
            uploaded = uploads.get(int(item.file.attachment_id)) if item.file.attachment_id else None
            return [ui.File(f"attachment://{uploaded}", spoiler=item.spoiler)] if uploaded else []
        case components.Section():
            texts = [found for child in item.components for found in _rebuild(child, uploads)]
            accessory = _rebuild(item.accessory, uploads)
            # A section needs its accessory, so without one its text stands alone
            return [ui.Section(*texts, accessory=accessory[0])] if accessory and texts else texts
        case components.Container():
            children = [found for child in item.components for found in _rebuild(child, uploads)]
            return [ui.Container(*children, color=item.accent_color, spoiler=item.spoiler)] if children else []
    return []


def layout_copy(source: Source, uploads: Uploads) -> list[ui.ViewItem]:
    """A Components V2 message's own layout. Parts outside any container are grouped into one, in order."""
    blocks: list[ui.ViewItem] = []
    loose: list[ui.ViewItem] = []
    for component in source.layout:
        for item in _rebuild(component, uploads):
            if isinstance(item, ui.Container):
                if loose:
                    blocks.append(ui.Container(*loose))
                    loose = []
                blocks.append(item)
            else:
                loose.append(item)
    if loose:
        blocks.append(ui.Container(*loose))
    return blocks


def usable_emojis(
    client: discord.Client, channel: discord.abc.GuildChannel | discord.Thread, *, webhook: bool
) -> Callable[[int], bool]:
    """
    Whether a custom emoji shows in a message the bot sends here. Discord turns the rest into plain `:name:` text.

    Only emojis the bot can see work: its own, and ones from servers it's in. Those from other servers also need
    Use External Emojis, which webhooks and interaction replies take from @everyone.
    """
    guild = channel.guild
    external = channel.permissions_for(guild.default_role if webhook else guild.me).use_external_emojis

    def usable(emoji_id: int) -> bool:
        if (found := client.get_emoji(emoji_id)) is None:
            return False
        home = getattr(found, "guild_id", None)
        return home is None or home == guild.id or external

    return usable


def _drop_emojis(view: DesignerView, usable: Callable[[int], bool]) -> None:
    def keep(match: re.Match[str]) -> str:
        return match.group(0) if usable(int(match.group(1))) else ""

    for item in view.walk_children():
        if isinstance(item, ui.TextDisplay):
            item.content = _CUSTOM_EMOJI.sub(keep, item.content)


def post_card(
    board: StarboardTable,
    message: discord.Message,
    tally: Tally,
    uploads: Uploads | None = None,
    *,
    usable: Callable[[int], bool],
    name: str | None = None,
) -> DesignerView:
    """
    The message as its board shows it. Mentions show without pinging, since the client allows none.

    Webhook posts carry the author's name and avatar themselves. Pass `name` when the bot posts it instead.
    """
    uploads = uploads or {}
    source = Source(message)
    card = ui.Container(color=int(board.color[1:], 16) if board.color else config.color.orange)
    if body := _body(source, name):
        card.add_item(ui.TextDisplay(body))
    gallery, files = _attachments(source, uploads)
    if gallery:
        card.add_item(ui.MediaGallery(*gallery))
    for item in files:
        card.add_item(item)
    card.add_item(
        ui.TextDisplay(
            f"-# {tally.emoji} **{fmt_count(tally.points)}** · {message.author.mention} · {message.channel.mention}"
            f" · {discord.utils.format_dt(message.created_at, 'R')}"
        )
    )
    guild_id = message.guild.id if message.guild else 0
    jump = ui.ActionRow(
        ui.Button(
            label="Jump to message",
            emoji=emoji.messages_white,
            style=discord.ButtonStyle.link,
            url=jump_url(guild_id, message.channel.id, message.id),
        )
    )

    budget = _Budget(card, jump)
    extra = [box for preview in source.link_previews if (box := embed_box(preview))]
    if source.v2:
        extra += layout_copy(source, uploads)
    kept = []
    for item in extra:
        # Whatever doesn't fit Discord's caps is left off from the end
        if not budget.take(item):
            break
        kept.append(item)
    view = DesignerView(card, *kept, jump, timeout=None, store=False)
    _drop_emojis(view, usable)
    return view


def board_status(board: StarboardTable, tally: Tally, posted: bool) -> str:
    state = "On the board" if posted else f"Needs `{board.threshold}`"
    return f"<#{board.channel_id}>\n{tally.emoji} `{tally.points}` · {state}"


def dashboard_url(guild_id: int) -> str:
    return f"{config.dashboard_url}/guild/{guild_id}/starboard"
