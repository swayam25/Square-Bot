import base64
import binascii
import discord
from discord.http import Route
from litestar import Router, delete, get, patch
from litestar.di import Provide
from msgspec import UNSET
from square.api.auth import provide_guild, provide_member
from square.api.refusals import REFUSED, refused
from square.api.resolve import SettingError
from square.api.schemas import IMAGE_DATA_MAX, IMAGE_MAX_BYTES, BotProfile, BotProfilePatch
from square.core import Client
from typing import Any

# Discord returns the bot's server bio only in reply to the bot's own member PATCH, never on a member fetch
_bios: dict[int, str | None] = {}
_account: dict[str, Any] = {}

_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}


def _image(uri: str | None, field: str) -> str | None:
    if uri is None:
        return None
    payload = uri.partition(",")[2]
    try:
        raw = base64.b64decode(payload, validate=True)
    except binascii.Error as exc:
        raise SettingError(f"The {field} isn't a readable image.") from exc
    if len(raw) > IMAGE_MAX_BYTES:
        raise SettingError(f"The {field} must be {IMAGE_MAX_BYTES // 2**20} MB or smaller.")
    mime = next((mime for signature, mime in _SIGNATURES.items() if raw.startswith(signature)), None)
    if mime is None:
        raise SettingError(f"The {field} must be a PNG, JPEG or GIF.")
    return f"data:{mime};base64,{payload}"


async def _edit(client: Client, guild: discord.Guild, reason: str | None = None, **fields: Any) -> discord.Member:
    try:
        data = await client.http.edit_member(guild.id, "@me", reason=reason, **fields)
    except discord.HTTPException as exc:
        raise SettingError(f"Discord refused that: {exc.text or exc}") from exc
    _bios[guild.id] = data.get("bio") or None
    return discord.Member(data=data, guild=guild, state=client._connection)


async def _out(client: Client, guild: discord.Guild, me: discord.Member) -> BotProfile:
    if not _account:
        _account.update(await client.http.request(Route("GET", "/users/@me")))
    account = discord.User(state=client._connection, data=_account)
    bot = client.user
    assert bot is not None
    return BotProfile(
        name=bot.display_name,
        nick=me.nick,
        bio=_bios.get(guild.id),
        avatar_url=me.guild_avatar.with_size(256).url if me.guild_avatar else None,
        banner_url=me.guild_banner.with_size(1024).url if me.guild_banner else None,
        global_bio=_account.get("bio") or None,
        global_avatar_url=bot.display_avatar.with_size(256).url,
        global_banner_url=account.banner.with_size(1024).url if account.banner else None,
        banner_color=str(account.accent_color) if account.accent_color else None,
    )


def _reason(member: discord.Member) -> str:
    return f"Dashboard: {member} ({member.id})"


def _check_nick(guild: discord.Guild) -> None:
    if not guild.me.guild_permissions.change_nickname:
        raise SettingError("Square needs the `Change Nickname` permission to change its nickname here.")


@get("/", summary="The bot's profile in this server")
async def get_bot_profile(client: Client, guild: discord.Guild) -> BotProfile:
    me = guild.me if guild.id in _bios else await _edit(client, guild)
    return await _out(client, guild, me)


@patch(
    "/",
    summary="Change the bot's nickname, avatar, banner or bio in this server",
    responses=REFUSED,
    request_max_body_size=2 * IMAGE_DATA_MAX + 64 * 1024,
)
async def update_bot_profile(
    client: Client, guild: discord.Guild, member: discord.Member, data: BotProfilePatch
) -> BotProfile:
    fields: dict[str, str | None] = {}
    if data.nick is not UNSET:
        _check_nick(guild)
        fields["nick"] = data.nick or ""
    if data.bio is not UNSET:
        fields["bio"] = data.bio or ""
    if data.avatar is not UNSET:
        fields["avatar"] = _image(data.avatar, "avatar")
    if data.banner is not UNSET:
        fields["banner"] = _image(data.banner, "banner")
    if not fields:
        return await _out(client, guild, guild.me)
    me = await _edit(client, guild, _reason(member), **fields)
    return await _out(client, guild, me)


async def reset_profile(client: Client, guild: discord.Guild, actor: discord.Member) -> discord.Member:
    fields: dict[str, str | None] = {"avatar": None, "banner": None, "bio": ""}
    if guild.me.nick:
        _check_nick(guild)
        fields["nick"] = ""
    return await _edit(client, guild, _reason(actor), **fields)


@delete("/", summary="Go back to the bot's global profile in this server", status_code=200, responses=REFUSED)
async def reset_bot_profile(client: Client, guild: discord.Guild, member: discord.Member) -> BotProfile:
    return await _out(client, guild, await reset_profile(client, guild, member))


router = Router(
    "/guilds/{guild_id:str}/profile",
    tags=["Profile"],
    exception_handlers={SettingError: refused},
    dependencies={
        "guild": Provide(provide_guild, sync_to_thread=False),
        "member": Provide(provide_member, sync_to_thread=False),
    },
    route_handlers=[get_bot_profile, update_bot_profile, reset_bot_profile],
)
