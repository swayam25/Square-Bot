import base64
import binascii
import discord
import io
import re
from discord import ui
from litestar import Router, get, post
from litestar.di import Provide
from square.api.auth import provide_guild, provide_member
from square.api.refusals import REFUSED, refused
from square.api.resolve import SettingError
from square.api.schemas import (
    MESSAGE_COMPONENTS_MAX,
    MESSAGE_FILE_DATA_MAX,
    MESSAGE_FILES_MAX_BYTES,
    MESSAGE_MEDIA_MAX,
    MESSAGE_TEXT_MAX,
    MessageButton,
    MessageContainer,
    MessageFile,
    MessageGallery,
    MessageMedia,
    MessagePiece,
    MessageRow,
    MessageSection,
    MessageSend,
    MessageSender,
    MessageSent,
    MessageSeparator,
    MessageTextDisplay,
    MessageThumbnail,
)
from square.core import Client
from square.utils import webhook

_ROLE_MENTION = re.compile(r"<@&(\d{17,20})>")
_ATTACHMENT = "attachment://"
# Discord refuses webhook names containing these
_BANNED_NAMES = ("discord", "clyde")
_RESERVED_NAMES = ("everyone", "here")


def _walk(components: list[MessageContainer | MessagePiece]):
    for component in components:
        yield component
        if isinstance(component, MessageContainer):
            yield from component.children


def _count(component: MessageContainer | MessagePiece) -> int:
    match component:
        case MessageContainer():
            return 1 + sum(_count(child) for child in component.children)
        case MessageSection():
            return 2 + len(component.texts)
        case MessageRow():
            return 1 + len(component.buttons)
        case _:
            return 1


def _texts(components: list[MessageContainer | MessagePiece]) -> list[str]:
    texts: list[str] = []
    for component in _walk(components):
        if isinstance(component, MessageTextDisplay):
            texts.append(component.text)
        elif isinstance(component, MessageSection):
            texts.extend(component.texts)
    return texts


def _media(components: list[MessageContainer | MessagePiece]) -> list[str]:
    urls: list[str] = []
    for component in _walk(components):
        match component:
            case MessageGallery():
                urls.extend(item.url for item in component.items)
            case MessageFile():
                urls.append(component.url)
            case MessageSection(accessory=MessageThumbnail() as thumbnail):
                urls.append(thumbnail.media.url)
    return urls


def _shown(components: list[MessageContainer | MessagePiece]) -> list[str]:
    urls: list[str] = []
    for component in _walk(components):
        match component:
            case MessageGallery():
                urls.extend(item.url for item in component.items)
            case MessageSection(accessory=MessageThumbnail() as thumbnail):
                urls.append(thumbnail.media.url)
    return urls


def _buttons(components: list[MessageContainer | MessagePiece]) -> list[MessageButton]:
    buttons: list[MessageButton] = []
    for component in _walk(components):
        if isinstance(component, MessageRow):
            buttons.extend(component.buttons)
        elif isinstance(component, MessageSection) and isinstance(component.accessory, MessageButton):
            buttons.append(component.accessory)
    return buttons


def _decode(data: MessageSend, limit: int) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for upload in data.files:
        if upload.name in files:
            raise SettingError(f"Two files are named {upload.name}.")
        try:
            raw = base64.b64decode(upload.data.partition(",")[2], validate=True)
        except binascii.Error as exc:
            raise SettingError(f"{upload.name} isn't a readable file.") from exc
        if len(raw) > limit:
            raise SettingError(f"{upload.name} is bigger than this server's {limit // 2**20} MB upload limit.")
        files[upload.name] = raw
    if sum(len(raw) for raw in files.values()) > MESSAGE_FILES_MAX_BYTES:
        raise SettingError(f"Files can add up to {MESSAGE_FILES_MAX_BYTES // 2**20} MB per message.")
    return files


def _check(data: MessageSend, files: dict[str, bytes]) -> None:
    if sum(_count(component) for component in data.components) > MESSAGE_COMPONENTS_MAX:
        raise SettingError(f"A message can have up to {MESSAGE_COMPONENTS_MAX} components.")
    if sum(len(text) for text in _texts(data.components)) > MESSAGE_TEXT_MAX:
        raise SettingError(f"A message can have up to {MESSAGE_TEXT_MAX} characters of text.")
    if len(_media(data.components)) > MESSAGE_MEDIA_MAX:
        raise SettingError(f"A message can show up to {MESSAGE_MEDIA_MAX} pictures, videos and files in total.")
    # Discord trims these and then refuses them as empty
    if any(not text.strip() for text in _texts(data.components)):
        raise SettingError("Text can't be only spaces.")
    if any(not (button.label or "").strip() and not button.emoji for button in _buttons(data.components)):
        raise SettingError("Every button needs a label or an emoji.")
    used = {url.removeprefix(_ATTACHMENT) for url in _media(data.components) if url.startswith(_ATTACHMENT)}
    if missing := used - files.keys():
        raise SettingError(f"{min(missing)} wasn't uploaded.")
    # Discord takes any file here but then draws a broken tile, so only pictures and videos go in galleries and thumbnails
    types = {upload.name: upload.data.removeprefix("data:").partition(";")[0] for upload in data.files}
    for url in _shown(data.components):
        name = url.removeprefix(_ATTACHMENT)
        if url.startswith(_ATTACHMENT) and not types.get(name, "").startswith(("image/", "video/")):
            raise SettingError(f"{name} isn't a picture or video, so it can only go in a File component.")
    if data.username is not None:
        name = data.username.strip().casefold()
        if not name:
            raise SettingError("The name can't be only spaces.")
        if any(word in name for word in _BANNED_NAMES):
            raise SettingError('Discord doesn\'t allow "Discord" or "Clyde" in a webhook\'s name.')
        if name in _RESERVED_NAMES:
            raise SettingError('Discord doesn\'t allow "everyone" or "here" as a name.')


def _refusal(exc: discord.HTTPException) -> str:
    # "Invalid Form Body\nIn components.0.emoji.name: Invalid emoji" -> just the reason, the path means nothing to people
    reason = (exc.text or str(exc)).strip().splitlines()[-1].rpartition(": ")[2].strip().rstrip(".")
    return f"Discord refused the message: {reason.lower()}."


def _item(media: MessageMedia) -> discord.MediaGalleryItem:
    return discord.MediaGalleryItem(media.url, description=media.description, spoiler=media.spoiler)


def _button(button: MessageButton) -> ui.Button:
    label = (button.label or "").strip() or None
    return ui.Button(url=button.url, label=label, emoji=button.emoji, disabled=button.disabled)


def _build(component: MessageContainer | MessagePiece) -> ui.Item:
    match component:
        case MessageContainer():
            return ui.Container(
                *(_build(child) for child in component.children),
                color=int(component.color[1:], 16) if component.color else None,
                spoiler=component.spoiler,
            )
        case MessageTextDisplay():
            return ui.TextDisplay(component.text)
        case MessageSection():
            accessory = component.accessory
            return ui.Section(
                *(ui.TextDisplay(text) for text in component.texts),
                accessory=_button(accessory)
                if isinstance(accessory, MessageButton)
                else ui.Thumbnail(
                    accessory.media.url, description=accessory.media.description, spoiler=accessory.media.spoiler
                ),
            )
        case MessageGallery():
            return ui.MediaGallery(*(_item(item) for item in component.items))
        case MessageFile():
            return ui.File(component.url, spoiler=component.spoiler)
        case MessageSeparator():
            spacing = discord.SeparatorSpacingSize.large if component.large else discord.SeparatorSpacingSize.small
            return ui.Separator(divider=component.divider, spacing=spacing)
        case MessageRow():
            return ui.ActionRow(*(_button(button) for button in component.buttons))


def _mentions(guild: discord.Guild, texts: list[str], everyone: bool) -> discord.AllowedMentions:
    if everyone:
        return discord.AllowedMentions(everyone=True, users=True, roles=True, replied_user=False)
    # Webhooks ping any role they name, so only roles anyone may ping go through for people without Mention Everyone
    ids = {int(found) for text in texts for found in _ROLE_MENTION.findall(text)}
    roles = [role for role_id in ids if (role := guild.get_role(role_id)) and role.mentionable]
    return discord.AllowedMentions(everyone=False, users=True, roles=roles[:100], replied_user=False)


@get("/sender", summary="The name and avatar a message has when none are given, and the upload limit")
async def message_sender(client: Client, guild: discord.Guild) -> MessageSender:
    bot = client.user
    assert bot is not None
    return MessageSender(
        name=bot.name,
        avatar_url=bot.display_avatar.with_size(128).url,
        upload_limit=min(guild.filesize_limit, MESSAGE_FILES_MAX_BYTES),
    )


@post(
    "/",
    summary="Send a Components V2 message through the bot's webhook",
    status_code=200,
    responses=REFUSED,
    request_max_body_size=MESSAGE_FILE_DATA_MAX + 256 * 1024,
)
async def send_message(client: Client, guild: discord.Guild, member: discord.Member, data: MessageSend) -> MessageSent:
    channel = guild.get_channel(int(data.channel_id))
    if not isinstance(channel, discord.TextChannel):
        raise SettingError("Pick a text channel to send to.")
    mine = channel.permissions_for(guild.me)
    if not (mine.view_channel and mine.send_messages and mine.manage_webhooks):
        raise SettingError(f"I need `Send Messages` and `Manage Webhooks` in {channel.mention}.")
    theirs = channel.permissions_for(member)
    if not (theirs.view_channel and theirs.send_messages):
        raise SettingError(f"You can't send messages in {channel.mention}.")
    if data.files and not theirs.attach_files:
        raise SettingError(f"You can't attach files in {channel.mention}.")

    raw = _decode(data, guild.filesize_limit)
    _check(data, raw)
    used = {url.removeprefix(_ATTACHMENT) for url in _media(data.components) if url.startswith(_ATTACHMENT)}
    mentions = _mentions(guild, _texts(data.components), theirs.mention_everyone)

    async def deliver(retry: bool) -> discord.WebhookMessage:
        hook = await webhook.get_webhook(client, channel)
        if hook is None:
            raise SettingError(f"I couldn't set up a webhook in {channel.mention}.")
        try:
            return await hook.send(
                view=ui.DesignerView(*(_build(component) for component in data.components), timeout=None, store=False),
                files=[discord.File(io.BytesIO(raw[name]), filename=name) for name in sorted(used)],
                username=data.username.strip() if data.username else discord.utils.MISSING,
                avatar_url=data.avatar_url or discord.utils.MISSING,
                allowed_mentions=mentions,
                wait=True,
            )
        except discord.NotFound as exc:
            # The cached webhook was deleted in Discord
            webhook.invalidate(channel.id)
            if retry:
                return await deliver(False)
            raise SettingError(f"I couldn't set up a webhook in {channel.mention}.") from exc
        except discord.HTTPException as exc:
            raise SettingError(_refusal(exc)) from exc
        except ValueError as exc:
            raise SettingError(str(exc)) from exc

    message = await deliver(True)
    return MessageSent(channel_id=str(channel.id), message_id=str(message.id), url=message.jump_url)


router = Router(
    "/guilds/{guild_id:str}/messages",
    tags=["Messages"],
    exception_handlers={SettingError: refused},
    dependencies={
        "guild": Provide(provide_guild, sync_to_thread=False),
        "member": Provide(provide_member, sync_to_thread=False),
    },
    route_handlers=[message_sender, send_message],
)
