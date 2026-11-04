"""Discord-style HTML transcripts of a channel's messages, used for ticket logs and deleted-message logs."""

from __future__ import annotations

import asyncio
import base64
import datetime
import discord
import io
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from discord.components import (
    ActionRow,
    Button,
    Container,
    FileComponent,
    MediaGallery,
    Section,
    SelectMenu,
    Separator,
    TextDisplay,
    Thumbnail,
    UnfurledMediaItem,
)
from discord.components import Component as DiscordComponent
from importlib.metadata import version
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from pathlib import Path
from square.transcript.markdown import Lookups, plain, render

log = logging.getLogger(__name__)

TEMPLATES = Path(__file__).parent / "templates"
# Discord's attachment links expire after about a day, so images are copied into the file up to this many bytes
IMAGE_BUDGET = 8 * 1024 * 1024
# Discord starts a new author block after this long, even for the same author
GROUP_WINDOW = datetime.timedelta(minutes=7)

_env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))


@dataclass
class Attachment:
    name: str
    url: str
    size: str
    image: str | None = None  # A data URI when the image was copied into the file


@dataclass
class Embed:
    color: str
    author: str | None
    title: str | None
    url: str | None
    description: Markup
    fields: list[tuple[str, Markup, bool]]
    image: str | None
    thumbnail: str | None
    footer: str | None


@dataclass
class Component:
    """A message component flattened for `components.html`, which draws it by `kind`."""

    kind: str  # container, text, section, thumbnail, gallery, file, separator, row, button or select
    children: list[Component] = field(default_factory=list)
    accessory: Component | None = None
    text: Markup = Markup("")
    color: str | None = None
    label: str = ""
    emoji: Markup = Markup("")
    style: str = ""
    url: str | None = None
    media: list[str] = field(default_factory=list)
    size: str = ""
    disabled: bool = False
    divider: bool = False
    large: bool = False


@dataclass
class Message:
    id: int
    time: datetime.datetime
    content: Markup
    edited: bool = False
    system: bool = False
    unknown: bool = False  # Deleted before the bot cached it, so only its ID and time are known
    reply: tuple[str, str] | None = None  # (author, preview), or ("", "") when the original is gone
    attachments: list[Attachment] = field(default_factory=list)
    embeds: list[Embed] = field(default_factory=list)
    components: list[Component] = field(default_factory=list)
    stickers: list[tuple[str, str]] = field(default_factory=list)
    reactions: list[tuple[Markup, int]] = field(default_factory=list)


@dataclass
class Group:
    author: str
    color: str
    avatar: str
    bot: bool
    messages: list[Message]


def _size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB"):
        if num_bytes < 1024 or unit == "MB":
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return ""


def _hex(color: discord.Colour | None, default: str) -> str:
    return f"#{color.value:06x}" if color and color.value else default


def _component_text(components: Sequence) -> str:
    """Text inside a components-v2 message (text displays, nested in containers and sections)."""
    parts = []
    for component in components:
        if (content := getattr(component, "content", None)) and isinstance(content, str):
            parts.append(content)
        for attr in ("components", "children", "items"):
            if children := getattr(component, attr, None):
                parts.append(_component_text(children))
    return "\n".join(part for part in parts if part)


_BUTTON_STYLES = {
    discord.ButtonStyle.primary: "primary",
    discord.ButtonStyle.success: "success",
    discord.ButtonStyle.danger: "danger",
    discord.ButtonStyle.premium: "primary",
}


def _emoji(emoji: discord.PartialEmoji | None) -> Markup:
    if emoji is None:
        return Markup("")
    if emoji.id:
        return Markup('<img class="emoji" alt=":{0}:" src="{1}">').format(emoji.name, emoji.url)
    return Markup.escape(emoji.name)


def _components(
    components: Sequence[DiscordComponent], lookups: Lookups, images: dict[int, str], drawn: set[int]
) -> list[Component]:
    """
    Converts message components for the template.

    Files the components show are added to `drawn`, so they aren't listed again as plain attachments.
    """

    def media(item: UnfurledMediaItem) -> str:
        if item.attachment_id:
            drawn.add(item.attachment_id)
            return images.get(item.attachment_id) or item.url
        return item.url

    def convert(component: DiscordComponent) -> Component | None:
        match component:
            case Container():
                children = _components(component.components, lookups, images, drawn)
                return Component("container", children, color=_hex(component.accent_color, "") or None)
            case TextDisplay():
                return Component("text", text=render(component.content, lookups))
            case Section():
                accessory = convert(component.accessory) if component.accessory else None
                return Component("section", _components(component.components, lookups, images, drawn), accessory)
            case Thumbnail():
                return Component("thumbnail", media=[media(component.media)])
            case MediaGallery():
                return Component("gallery", media=[media(item.media) for item in component.items])
            case FileComponent():
                name = component.name or component.file.url.rsplit("/", 1)[-1].split("?")[0]
                size = _size(component.size) if component.size else ""
                return Component("file", label=name, url=media(component.file), size=size)
            case Separator():
                large = component.spacing == discord.SeparatorSpacingSize.large
                return Component("separator", divider=bool(component.divider), large=large)
            case ActionRow():
                return Component("row", _components(component.children, lookups, images, drawn))
            case Button():
                return Component(
                    "button",
                    label=component.label or "",
                    emoji=_emoji(component.emoji),
                    style=_BUTTON_STYLES.get(component.style, "secondary"),
                    url=component.url,
                    disabled=component.disabled,
                )
            case SelectMenu():
                picked = [option.label for option in component.options if option.default]
                label = ", ".join(picked) or component.placeholder or "Make a selection"
                return Component("select", label=label, disabled=component.disabled, style="" if picked else "empty")
        return None

    return [converted for component in components if (converted := convert(component))]


def _lookups(guild: discord.Guild) -> Lookups:
    return Lookups(
        users={member.id: member.display_name for member in guild.members},
        roles={role.id: (role.name, _hex(role.color, "#c9cdfb")) for role in guild.roles},
        channels={channel.id: channel.name for channel in guild.channels},
    )


async def _copy_images(messages: Sequence[discord.Message], budget: int) -> dict[int, str]:
    """Downloads image attachments as data URIs, oldest first, until the budget is spent."""
    picked: list[discord.Attachment] = []
    for message in messages:
        for attachment in message.attachments:
            if not (attachment.content_type or "").startswith("image/"):
                continue
            encoded = (attachment.size + 2) // 3 * 4
            if encoded <= budget:
                picked.append(attachment)
                budget -= encoded
    semaphore = asyncio.Semaphore(4)

    async def fetch(attachment: discord.Attachment) -> tuple[int, str | None]:
        async with semaphore:
            try:
                data = await attachment.read()
            except discord.HTTPException:
                return attachment.id, None  # Already gone, it stays a link
        return attachment.id, f"data:{attachment.content_type};base64,{base64.b64encode(data).decode()}"

    return {key: uri for key, uri in await asyncio.gather(*(fetch(a) for a in picked)) if uri}


def _message(message: discord.Message, lookups: Lookups, images: dict[int, str]) -> Message:
    content = message.system_content if message.is_system() else message.content
    drawn: set[int] = set()
    components = _components(message.components, lookups, images, drawn)
    reply = None
    if message.reference is not None and not message.is_system():
        resolved = message.reference.resolved
        reply = (
            (
                resolved.author.display_name,
                plain(resolved.content or _component_text(resolved.components) or "Attachment"),
            )
            if isinstance(resolved, discord.Message)
            else ("", "")
        )
    embeds = [
        Embed(
            color=_hex(embed.colour if isinstance(embed.colour, discord.Colour) else None, "#1e1f22"),
            author=embed.author.name if embed.author else None,
            title=embed.title,
            url=embed.url,
            description=render(embed.description or "", lookups),
            fields=[(f.name or "", render(f.value or "", lookups), bool(f.inline)) for f in embed.fields],
            image=embed.image.url if embed.image else None,
            thumbnail=embed.thumbnail.url if embed.thumbnail else None,
            footer=embed.footer.text if embed.footer else None,
        )
        for embed in message.embeds
    ]
    reactions = []
    for reaction in message.reactions:
        if isinstance(reaction.emoji, str):
            shown = Markup.escape(reaction.emoji)
        else:
            shown = Markup('<img class="emoji" alt="{0}" src="{1}">').format(reaction.emoji.name, reaction.emoji.url)
        reactions.append((shown, reaction.count))
    return Message(
        id=message.id,
        time=message.created_at,
        content=Markup.escape(content) if message.is_system() else render(content, lookups),
        edited=message.edited_at is not None,
        system=message.is_system(),
        reply=reply,
        attachments=[
            Attachment(a.filename, a.url, _size(a.size), images.get(a.id))
            for a in message.attachments
            if a.id not in drawn
        ],
        embeds=embeds,
        components=components,
        stickers=[(sticker.name, sticker.url) for sticker in message.stickers],
        reactions=reactions,
    )


def _group(entries: list[tuple[discord.User | discord.Member | None, Message]]) -> list[Group]:
    groups: list[Group] = []
    last_author: int | None = None
    for author, message in entries:
        previous = groups[-1].messages[-1] if groups else None
        same = (
            author is not None
            and author.id == last_author
            and previous is not None
            and message.time - previous.time < GROUP_WINDOW
            and message.reply is None
        )
        if same:
            groups[-1].messages.append(message)
            continue
        if author is None:
            groups.append(Group("Unknown", "#949ba4", "", False, [message]))
        else:
            color = _hex(author.color, "#f2f3f5") if isinstance(author, discord.Member) else "#f2f3f5"
            groups.append(Group(author.display_name, color, author.display_avatar.url, author.bot, [message]))
        last_author = author.id if author else None
    return groups


async def render_transcript(
    messages: Iterable[discord.Message],
    *,
    guild: discord.Guild,
    channel_name: str,
    title: str,
    summary: Sequence[tuple[str, str]] = (),
    unknown_ids: Iterable[int] = (),
) -> str:
    """
    Renders messages as a self-contained HTML page that looks like the Discord channel.

    Args:
        messages: The messages, in any order.
        guild (:class:`discord.Guild`): Their guild, used for names, roles and the upload size limit.
        channel_name (str): Shown in the header.
        title (str): The page heading, e.g. "Ticket #0042".
        summary: Label and value pairs shown under the heading, e.g. who opened and closed a ticket.
        unknown_ids: IDs of messages that weren't cached, shown with only their time.
    """
    ordered = sorted(messages, key=lambda m: m.id)
    budget = min(IMAGE_BUDGET, guild.filesize_limit - 2 * 1024 * 1024)
    images = await _copy_images(ordered, budget)
    lookups = _lookups(guild)
    entries: list[tuple[discord.User | discord.Member | None, Message]] = [
        (m.author, _message(m, lookups, images)) for m in ordered
    ]
    entries += [
        (None, Message(id=i, time=discord.utils.snowflake_time(i), content=Markup(""), unknown=True))
        for i in unknown_ids
    ]
    entries.sort(key=lambda entry: entry[1].id)
    return _env.get_template("transcript.html").render(
        css=Markup((TEMPLATES / "transcript.css").read_text()),  # noqa: S704 - our own stylesheet
        title=title,
        guild_name=guild.name,
        guild_icon=guild.icon.url if guild.icon else None,
        channel_name=channel_name,
        summary=summary,
        groups=_group(entries),
        message_count=len(entries),
        generated=discord.utils.utcnow(),
        version=version("square"),
    )


async def transcript_file(filename: str, *args, **kwargs) -> discord.File:
    """`render_transcript` as a file ready to send, e.g. `ticket-0042.html`."""
    page = await render_transcript(*args, **kwargs)
    return discord.File(io.BytesIO(page.encode()), filename=filename)
