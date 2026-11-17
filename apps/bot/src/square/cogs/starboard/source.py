import discord
from dataclasses import dataclass
from discord import components
from urllib.parse import urlsplit


def media_url(embed: discord.Embed) -> str | None:
    """The embed's best media. A clip comes first, since that's how a GIF link shows its animation."""
    for part in (embed.video, embed.image, embed.thumbnail):
        if part and part.url:
            return part.url
    return None


def media_only(embed: discord.Embed) -> bool:
    """
    An embed that only shows a picture or a clip, like a GIF or an image link.

    Read from what it holds, not its `type`, which Discord calls loosely defined and deprecated. GIF hosts title
    their clips, so a title only rules out a picture: a bot embed with a title and an image stays an embed.
    """
    if embed.description or embed.fields or (embed.author and embed.author.name):
        return False
    if embed.video and embed.video.url:
        return True
    return not embed.title and media_url(embed) is not None


@dataclass(frozen=True)
class File:
    id: int
    url: str
    name: str
    size: int | None = None
    spoiler: bool = False
    media: bool = False


@dataclass
class Preview:
    embed: discord.Embed
    more: list[str]  # Images of the embeds after it that share its link, which Discord shows in its grid


def _previews(embeds: list[discord.Embed]) -> list[Preview]:
    """Discord merges embeds that share a link into one, so a post with four pictures comes as four embeds."""
    previews: list[Preview] = []
    for embed in embeds:
        image = embed.image.url if embed.image else None
        if previews and image and embed.url and embed.url == previews[-1].embed.url:
            previews[-1].more.append(image)
        else:
            previews.append(Preview(embed, []))
    return previews


def is_media(content_type: str | None) -> bool:
    return (content_type or "").startswith(("image/", "video/"))


def _v2_files(items: list[components.Component]) -> list[File]:
    found: dict[int, File] = {}

    def add(media: components.UnfurledMediaItem | None, size: int | None = None, *, shown: bool = True) -> None:
        if media is None or not media.attachment_id or int(media.attachment_id) in found:
            return
        name = urlsplit(media.url).path.rsplit("/", 1)[-1] or "file"
        found[int(media.attachment_id)] = File(int(media.attachment_id), media.url, name, size, media=shown)

    def walk(item: components.Component) -> None:
        match item:
            case components.MediaGallery():
                for entry in item.items:
                    add(entry.media)
            case components.Thumbnail():
                add(item.media)
            case components.FileComponent():
                add(item.file, item.size, shown=False)
            case components.Section():
                for child in [*item.components, item.accessory]:
                    walk(child)
            case components.Container():
                for child in item.components:
                    walk(child)

    for item in items:
        walk(item)
    return list(found.values())


class Source:
    """What a message shows. Forwards are unwrapped, since their content lives in a snapshot."""

    def __init__(self, message: discord.Message):
        self.message = message
        snapshot = message.snapshots[0].message if message.snapshots and message.snapshots[0].message else None
        self.forwarded = snapshot is not None
        self.content: str = (snapshot.content if snapshot else message.content) or ""
        self.previews = _previews(list(snapshot.embeds if snapshot else message.embeds))
        shown = snapshot or message
        self.stickers = list(shown.stickers)
        self.poll = None if snapshot else message.poll
        self.layout: list[components.Component] = list(shown.components)
        # A Components V2 message places its own files, so they show inside its copied layout instead
        self.v2 = shown.flags.is_components_v2
        attachments = snapshot.attachments if snapshot else message.attachments
        self.files = (
            _v2_files(self.layout)
            if self.v2
            else [
                File(item.id, item.url, item.filename, item.size, item.is_spoiler(), is_media(item.content_type))
                for item in attachments
            ]
        )

    @property
    def media_previews(self) -> list[Preview]:
        return [preview for preview in self.previews if media_only(preview.embed)]

    @property
    def link_previews(self) -> list[Preview]:
        return [preview for preview in self.previews if not media_only(preview.embed)]
