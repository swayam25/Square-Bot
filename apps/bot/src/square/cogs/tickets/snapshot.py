"""
Saves a ticket channel as data. The dashboard draws the transcript from it, so nothing here makes HTML.

Text is stored as the raw Discord markdown people typed. Names behind mentions are saved next to it, since the
members, roles and channels may be gone by the time someone reads the transcript.
"""

from __future__ import annotations

import asyncio
import discord
import logging
import msgspec
import re
import weakref
from collections.abc import Sequence
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
from square.db.funcs import tickets as db
from square.db.schema import TicketTable
from typing import Literal

log = logging.getLogger(__name__)

MESSAGE_LIMIT = 5000
# Discord's attachment links expire after about a day, so pictures are copied into the database up to this many bytes
IMAGE_BUDGET = 8 * 1024 * 1024
# No SVG: these are served back from the dashboard's own address, and an SVG can carry scripts
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
PREVIEW_LENGTH = 200

_USER = re.compile(r"<@!?(\d{17,20})>")
_ROLE = re.compile(r"<@&(\d{17,20})>")
_CHANNEL = re.compile(r"<#(\d{17,20})>")
_LINE_MARK = re.compile(r"^(?:#{1,3} |-# |>>> |> |[-*] )")
_FENCE = re.compile(r"```(?:[\w+-]+\n)?")
_locks: weakref.WeakValueDictionary[int, asyncio.Lock] = weakref.WeakValueDictionary()


class Stored(msgspec.Struct, rename="camel", kw_only=True, omit_defaults=True):
    """Saved in the database, so old rows must keep loading: new fields need a default, and none are forbidden."""


class TranscriptUser(Stored):
    name: str
    avatar: str
    color: str = ""
    bot: bool = False


class TranscriptRole(Stored):
    name: str
    color: str = ""


class TranscriptEmoji(Stored):
    name: str
    id: str = ""
    animated: bool = False


class TranscriptFile(Stored):
    name: str
    url: str
    id: str = ""
    size: int = 0
    kind: Literal["image", "video", "audio", "file"] = "file"
    width: int | None = None
    height: int | None = None
    stored: bool = False  # True when the dashboard has its own copy


class TranscriptField(Stored):
    name: str
    value: str
    inline: bool = False


class TranscriptEmbed(Stored):
    color: str = ""
    author: str = ""
    author_icon: str = ""
    title: str = ""
    url: str = ""
    description: str = ""
    fields: list[TranscriptField] = []
    image: str = ""
    thumbnail: str = ""
    footer: str = ""
    footer_icon: str = ""
    time: int | None = None  # Unix ms
    media: Literal["", "image", "video"] = ""  # a bare picture or GIF link, drawn without the embed box
    media_url: str = ""


class TranscriptComponent(Stored):
    kind: Literal[
        "container", "text", "section", "thumbnail", "gallery", "file", "separator", "row", "button", "select"
    ]
    children: list[TranscriptComponent] = []
    accessory: TranscriptComponent | None = None
    text: str = ""
    color: str = ""
    label: str = ""
    emoji: TranscriptEmoji | None = None
    style: Literal["", "primary", "secondary", "success", "danger"] = ""
    url: str = ""
    files: list[TranscriptFile] = []
    disabled: bool = False
    divider: bool = False
    large: bool = False
    placeholder: bool = False


class TranscriptReply(Stored):
    id: str
    author: str
    preview: str = ""
    attachment: bool = False  # no text, but files: Discord says "Click to see attachment"
    ping: bool = False  # the reply mentioned its author, so Discord puts an @ before the name


class TranscriptCommand(Stored):
    name: str
    user: str


class TranscriptReaction(Stored):
    emoji: TranscriptEmoji
    count: int


class TranscriptSticker(Stored):
    name: str
    url: str


class TranscriptMessage(Stored):
    id: str
    author: str
    time: int  # Unix ms
    content: str = ""
    edited: bool = False
    command: TranscriptCommand | None = None
    system: Literal["", "join", "pin", "boost", "other"] = ""
    reply: TranscriptReply | None = None
    reply_deleted: bool = False
    attachments: list[TranscriptFile] = []
    embeds: list[TranscriptEmbed] = []
    components: list[TranscriptComponent] = []
    stickers: list[TranscriptSticker] = []
    reactions: list[TranscriptReaction] = []


class Transcript(Stored):
    channel: str
    saved_at: int  # Unix ms
    messages: list[TranscriptMessage]
    users: dict[str, TranscriptUser] = {}
    roles: dict[str, TranscriptRole] = {}
    channels: dict[str, str] = {}


def _ms(when) -> int:
    return round(when.timestamp() * 1000)


def _hex(color: discord.Colour | None) -> str:
    return f"#{color.value:06x}" if color and color.value else ""


def _kind(content_type: str | None) -> Literal["image", "video", "audio", "file"]:
    match (content_type or "").split("/", 1)[0]:
        case "image":
            return "image"
        case "video":
            return "video"
        case "audio":
            return "audio"
    return "file"


def _emoji(emoji: discord.PartialEmoji | discord.Emoji | str | None) -> TranscriptEmoji | None:
    if emoji is None:
        return None
    if isinstance(emoji, str):
        return TranscriptEmoji(name=emoji)
    return TranscriptEmoji(name=emoji.name, id=str(emoji.id) if emoji.id else "", animated=bool(emoji.animated))


def _preview(content: str) -> str:
    """Discord's reply line: the inline markdown stays, the line-level marks go, and it's all one line."""
    lines = (_LINE_MARK.sub("", line.strip()) for line in _FENCE.sub("`", content).splitlines())
    text = " ".join(line for line in lines if line)
    return text if len(text) <= PREVIEW_LENGTH else text[: PREVIEW_LENGTH - 1] + "…"


_BUTTON_STYLES: dict[discord.ButtonStyle, Literal["primary", "success", "danger"]] = {
    discord.ButtonStyle.primary: "primary",
    discord.ButtonStyle.success: "success",
    discord.ButtonStyle.danger: "danger",
    discord.ButtonStyle.premium: "primary",
}


class _Builder:
    def __init__(self, guild: discord.Guild, stored: set[int]):
        self.guild = guild
        self.stored = stored
        self.users: dict[str, TranscriptUser] = {}
        self.texts: list[str] = []
        self.mentioned: dict[int, discord.User | discord.Member] = {}

    def user(self, user: discord.User | discord.Member) -> str:
        key = str(user.id)
        if key not in self.users:
            self.users[key] = TranscriptUser(
                name=user.display_name,
                avatar=user.display_avatar.replace(size=128, static_format="webp").url,
                color=_hex(user.color) if isinstance(user, discord.Member) else "",
                bot=user.bot,
            )
        return key

    def text(self, text: str | None) -> str:
        if text:
            self.texts.append(text)
        return text or ""

    def file(self, attachment: discord.Attachment) -> TranscriptFile:
        return TranscriptFile(
            id=str(attachment.id),
            name=attachment.filename,
            url=attachment.url,
            size=attachment.size,
            kind=_kind(attachment.content_type),
            width=attachment.width,
            height=attachment.height,
            stored=attachment.id in self.stored,
        )

    def media(self, item: UnfurledMediaItem, drawn: set[int], name: str = "", video: bool = False) -> TranscriptFile:
        if item.attachment_id:
            drawn.add(item.attachment_id)
        return TranscriptFile(
            id=str(item.attachment_id) if item.attachment_id else "",
            name=name,
            url=item.url,
            kind="video" if video else "image",
            width=getattr(item, "width", None),
            height=getattr(item, "height", None),
            stored=bool(item.attachment_id) and item.attachment_id in self.stored,
        )

    def components(self, components: Sequence[DiscordComponent], drawn: set[int]) -> list[TranscriptComponent]:
        return [converted for component in components if (converted := self.component(component, drawn))]

    def component(self, component: DiscordComponent, drawn: set[int]) -> TranscriptComponent | None:
        match component:
            case Container():
                return TranscriptComponent(
                    kind="container",
                    children=self.components(component.components, drawn),
                    color=_hex(component.accent_color),
                )
            case TextDisplay():
                return TranscriptComponent(kind="text", text=self.text(component.content))
            case Section():
                return TranscriptComponent(
                    kind="section",
                    children=self.components(component.components, drawn),
                    accessory=self.component(component.accessory, drawn) if component.accessory else None,
                )
            case Thumbnail():
                return TranscriptComponent(kind="thumbnail", files=[self.media(component.media, drawn)])
            case MediaGallery():
                return TranscriptComponent(
                    kind="gallery",
                    files=[
                        self.media(
                            item.media,
                            drawn,
                            item.description or "",
                            _kind(getattr(item.media, "content_type", None)) == "video",
                        )
                        for item in component.items
                    ],
                )
            case FileComponent():
                name = component.name or component.file.url.rsplit("/", 1)[-1].split("?")[0]
                file = self.media(component.file, drawn, name)
                file.kind, file.size, file.stored = "file", component.size or 0, False
                return TranscriptComponent(kind="file", files=[file])
            case Separator():
                return TranscriptComponent(
                    kind="separator",
                    divider=bool(component.divider),
                    large=component.spacing == discord.SeparatorSpacingSize.large,
                )
            case ActionRow():
                return TranscriptComponent(kind="row", children=self.components(component.children, drawn))
            case Button():
                return TranscriptComponent(
                    kind="button",
                    label=component.label or "",
                    emoji=_emoji(component.emoji),
                    style=_BUTTON_STYLES.get(component.style, "secondary"),
                    url=component.url or "",
                    disabled=component.disabled,
                )
            case SelectMenu():
                picked = [option.label for option in component.options if option.default]
                return TranscriptComponent(
                    kind="select",
                    label=", ".join(picked) or component.placeholder or "Make a selection",
                    disabled=component.disabled,
                    placeholder=not picked,
                )
        return None

    def embed(self, embed: discord.Embed) -> TranscriptEmbed:
        media, media_url = "", ""
        if embed.type == "gifv" and embed.video and embed.video.url:
            media, media_url = "video", embed.video.url
        elif embed.type == "image" and (url := (embed.thumbnail.url if embed.thumbnail else None) or embed.url):
            media, media_url = "image", url
        return TranscriptEmbed(
            color=_hex(embed.colour if isinstance(embed.colour, discord.Colour) else None),
            author=(embed.author.name if embed.author else None) or "",
            author_icon=(embed.author.icon_url if embed.author else None) or "",
            title=embed.title or "",
            url=embed.url or "",
            description=self.text(embed.description),
            fields=[
                TranscriptField(name=field.name or "", value=self.text(field.value), inline=bool(field.inline))
                for field in embed.fields
            ],
            image=(embed.image.url if embed.image else None) or "",
            thumbnail=(embed.thumbnail.url if embed.thumbnail else None) or "",
            footer=(embed.footer.text if embed.footer else None) or "",
            footer_icon=(embed.footer.icon_url if embed.footer else None) or "",
            time=_ms(embed.timestamp) if embed.timestamp else None,
            media=media,
            media_url=media_url,
        )

    def message(self, message: discord.Message) -> TranscriptMessage:
        system = _system(message)
        for user in message.mentions:
            self.mentioned[user.id] = user
        drawn: set[int] = set()
        components = self.components(message.components, drawn)
        reply, reply_deleted = None, False
        if message.reference is not None and not system:
            resolved = message.reference.resolved
            if isinstance(resolved, discord.Message):
                preview = self.text(_preview(resolved.content))
                reply = TranscriptReply(
                    id=str(resolved.id),
                    author=self.user(resolved.author),
                    preview=preview,
                    attachment=not preview and bool(resolved.attachments),
                    ping=any(user.id == resolved.author.id for user in message.mentions),
                )
            reply_deleted = isinstance(resolved, discord.DeletedReferencedMessage)
        command = None
        # The public `interaction` is deprecated for `interaction_metadata`, which leaves out the command's name
        if (used := message._interaction) is not None and used.name and used.user:
            command = TranscriptCommand(name=used.name, user=self.user(used.user))
        return TranscriptMessage(
            id=str(message.id),
            author=self.user(message.author),
            time=_ms(message.created_at),
            content=(message.system_content or "") if system else self.text(message.content),
            edited=message.edited_at is not None,
            command=command,
            system=system,
            reply=reply,
            reply_deleted=reply_deleted,
            attachments=[self.file(a) for a in message.attachments if a.id not in drawn],
            embeds=[self.embed(embed) for embed in message.embeds],
            components=components,
            stickers=[TranscriptSticker(name=sticker.name, url=sticker.url) for sticker in message.stickers],
            reactions=[
                TranscriptReaction(emoji=shown, count=reaction.count)
                for reaction in message.reactions
                if (shown := _emoji(reaction.emoji))
            ],
        )

    def lookups(self) -> tuple[dict[str, TranscriptRole], dict[str, str]]:
        everything = "\n".join(self.texts)
        for user_id in {int(found) for found in _USER.findall(everything)}:
            if user := self.guild.get_member(user_id) or self.mentioned.get(user_id):
                self.user(user)
        roles = {
            str(role.id): TranscriptRole(name=role.name, color=_hex(role.color))
            for role_id in {int(found) for found in _ROLE.findall(everything)}
            if (role := self.guild.get_role(role_id))
        }
        channels = {
            str(channel.id): channel.name
            for channel_id in {int(found) for found in _CHANNEL.findall(everything)}
            if (channel := self.guild.get_channel_or_thread(channel_id))
        }
        return roles, channels


def _system(message: discord.Message) -> Literal["", "join", "pin", "boost", "other"]:
    if not message.is_system():
        return ""
    match message.type:
        case discord.MessageType.new_member:
            return "join"
        case discord.MessageType.pins_add:
            return "pin"
        case (
            discord.MessageType.premium_guild_subscription
            | discord.MessageType.premium_guild_tier_1
            | discord.MessageType.premium_guild_tier_2
            | discord.MessageType.premium_guild_tier_3
        ):
            return "boost"
    return "other"


async def _copy_images(ticket: TicketTable, messages: Sequence[discord.Message]) -> set[int]:
    """Copies the ticket's pictures that aren't saved yet, and drops the ones whose message is gone."""
    have = await db.stored_file_sizes(ticket)
    wanted = [
        attachment
        for message in messages
        for attachment in message.attachments
        if (attachment.content_type or "").split(";", 1)[0].strip() in IMAGE_TYPES
    ]
    wanted_ids = {attachment.id for attachment in wanted}
    if gone := set(have) - wanted_ids:
        await db.delete_files(ticket, gone)
    kept = set(have) & wanted_ids
    budget = IMAGE_BUDGET - sum(have[attachment_id] for attachment_id in kept)
    picked: list[discord.Attachment] = []
    for attachment in wanted:
        if attachment.id not in kept and attachment.size <= budget:
            picked.append(attachment)
            budget -= attachment.size
    semaphore = asyncio.Semaphore(4)

    async def copy(attachment: discord.Attachment) -> int | None:
        async with semaphore:
            try:
                data = await attachment.read()
            except discord.HTTPException:
                return None
        content_type = (attachment.content_type or "").split(";", 1)[0].strip()
        await db.add_file(ticket, attachment.id, content_type, data)
        return attachment.id

    copied = await asyncio.gather(*(copy(attachment) for attachment in picked))
    return kept | {attachment_id for attachment_id in copied if attachment_id}


async def save(
    guild: discord.Guild, channel: discord.TextChannel, ticket: TicketTable, *, unless_saved_after: int | None = None
) -> None:
    """Reads the channel and saves it as the ticket's transcript, replacing the one saved before.

    With `unless_saved_after` (Unix ms), a save that finished after then counts, so viewers who asked at the same
    moment share one read of the channel instead of each reading thousands of messages.
    """
    # Held in a local, so the weak dict keeps the lock for as long as anyone is using or waiting on it
    lock = _locks.get(ticket.id) or _locks.setdefault(ticket.id, asyncio.Lock())
    async with lock:
        if unless_saved_after is not None:
            row = await db.fetch_transcript(ticket)
            if row is not None and _ms(row.saved_at) > unless_saved_after:
                return
        messages = [message async for message in channel.history(limit=MESSAGE_LIMIT)]
        messages.sort(key=lambda message: message.id)
        builder = _Builder(guild, await _copy_images(ticket, messages))
        saved: list[TranscriptMessage] = []
        for index, message in enumerate(messages):
            saved.append(builder.message(message))
            if index % 250 == 249:
                await asyncio.sleep(0)  # a long ticket is a lot of work, and the music keeps playing meanwhile
        roles, channels = builder.lookups()
        transcript = Transcript(
            channel=channel.name,
            saved_at=_ms(discord.utils.utcnow()),
            messages=saved,
            users=builder.users,
            roles=roles,
            channels=channels,
        )
        # Postgres refuses a NUL inside JSON text
        data = msgspec.json.decode(msgspec.json.encode(transcript).replace(b"\\u0000", b""))
        participants = sorted({message.author.id for message in messages if not message.author.bot})
        await db.save_transcript(ticket, data, len(saved), participants)


async def load(ticket: TicketTable) -> tuple[Transcript, int] | None:
    if (row := await db.fetch_transcript(ticket)) is None:
        return None
    return msgspec.convert(row.data, Transcript), _ms(row.saved_at)
