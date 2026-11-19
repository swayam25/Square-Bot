import base64
import binascii
import discord
import secrets
import time
from datetime import UTC, datetime, timedelta
from litestar import Router, delete, get, patch, post
from litestar.di import Provide
from litestar.params import Parameter
from litestar.response import Stream
from msgspec import UNSET
from square.api import files as stored
from square.api import resolve
from square.api.auth import provide_guild, provide_member
from square.api.refusals import REFUSED, refused
from square.api.resolve import SettingError
from square.api.schemas import (
    GIVEAWAY_IMAGE_DATA_MAX,
    GIVEAWAY_IMAGE_MAX_BYTES,
    BonusRole,
    Entrant,
    EntrantBonus,
    EntrantPage,
    EntrantRemove,
    Giveaway,
    GiveawayCreate,
    GiveawayPage,
    GiveawayPatch,
    GiveawaySummary,
    Reroll,
    person_of,
)
from square.api.users import find_user, people_of
from square.cogs.giveaways import actions, files
from square.core import Client
from square.db import cache
from square.db.funcs import giveaways as giveaways_db
from square.db.schema import GiveawayTable
from square.modules import Module
from square.utils import storage
from typing import Annotated, Any, Literal

PAGE_SIZE = 25
MIN_LENGTH = timedelta(seconds=10)
MAX_LENGTH = timedelta(days=365)
MAX_LEAD = timedelta(days=365)
# Room left for the lines the bot adds under the description
TEXT_BUDGET = 3000
_LIVE_ONLY = {
    "channel_id",
    "starts_at",
    "ends_at",
    "winner_count",
    "required_role_ids",
    "require_all_roles",
    "blocked_role_ids",
    "min_account_days",
    "min_member_days",
    "min_invites",
    "bonus_roles",
    "ping_role_id",
    "winner_role_id",
}

GiveawayId = Annotated[int, Parameter(ge=1, le=2**31 - 1)]
BODY_LIMIT = GIVEAWAY_IMAGE_DATA_MAX + 256 * 1024
_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": ("image/png", "png"),
    b"\xff\xd8\xff": ("image/jpeg", "jpg"),
    b"GIF87a": ("image/gif", "gif"),
    b"GIF89a": ("image/gif", "gif"),
}
# Discord's attachment links are signed and expire after about a day
_LINK_TTL = 6 * 60 * 60
_LINKS_MAX = 500
_links: dict[int, tuple[str, str, float]] = {}

Upload = tuple[str, bytes, str]


def _ms(at: datetime) -> int:
    return round(at.timestamp() * 1000)


def _at(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, UTC)


def _summary_fields(giveaway: GiveawayTable) -> dict[str, Any]:
    return {
        "id": giveaway.id,
        "status": giveaway.status,
        "prize": giveaway.prize,
        "channel_id": str(giveaway.channel_id),
        "entries": giveaway.entry_count,
        "winner_count": giveaway.winner_count,
        "starts_at": _ms(giveaway.starts_at),
        "ends_at": _ms(giveaway.ends_at),
        "ended_at": _ms(giveaway.ended_at) if giveaway.ended_at else None,
        "posted": giveaway.message_id is not None,
    }


def _upload(guild: discord.Guild, uri: str) -> Upload:
    try:
        raw = base64.b64decode(uri.partition(",")[2], validate=True)
    except binascii.Error as exc:
        raise SettingError("That image isn't readable.") from exc
    limit = min(GIVEAWAY_IMAGE_MAX_BYTES, guild.filesize_limit)
    if len(raw) > limit:
        raise SettingError(f"The image must be {limit // 2**20} MB or smaller.")
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        kind = ("image/webp", "webp")
    elif not (kind := next((kind for sign, kind in _SIGNATURES.items() if raw.startswith(sign)), None)):
        raise SettingError("The image must be a PNG, JPEG, GIF or WebP.")
    return f"giveaway-{secrets.token_hex(4)}.{kind[1]}", raw, kind[0]


async def _image_src(client: Client, giveaway: GiveawayTable) -> str | None:
    if not (giveaway.image_file and giveaway.message_id):
        return None
    if (hit := _links.get(giveaway.message_id)) and hit[0] == giveaway.image_file and hit[2] > time.monotonic():
        return hit[1]
    channel = client.get_channel(giveaway.channel_id)
    if not isinstance(channel, discord.TextChannel | discord.Thread | discord.VoiceChannel):
        return None
    try:
        message = await channel.fetch_message(giveaway.message_id)
    except discord.HTTPException:
        return None
    # Components V2 messages don't list their attachments, so the link comes from the gallery that shows it
    galleries = [
        item for top in message.components if isinstance(top, discord.Container) for item in top.walk_components()
    ]
    links = [entry.url for gallery in galleries if isinstance(gallery, discord.MediaGallery) for entry in gallery.items]
    found = next((link for link in links if link.split("?")[0].endswith(f"/{giveaway.image_file}")), None)
    if found:
        if len(_links) >= _LINKS_MAX:
            _links.pop(next(iter(_links)))
        _links[giveaway.message_id] = (giveaway.image_file, found, time.monotonic() + _LINK_TTL)
    return found


async def _out(client: Client, guild: discord.Guild, giveaway: GiveawayTable) -> Giveaway:
    host = await find_user(client, guild, giveaway.host_id)
    return Giveaway(
        **_summary_fields(giveaway),
        description=giveaway.description,
        message_url=(
            f"https://discord.com/channels/{guild.id}/{giveaway.channel_id}/{giveaway.message_id}"
            if giveaway.message_id
            else None
        ),
        host=person_of(giveaway.host_id, host),
        winners=await people_of(client, guild, giveaway.winner_ids),
        required_role_ids=[str(role_id) for role_id in giveaway.required_role_ids],
        require_all_roles=giveaway.require_all_roles,
        blocked_role_ids=[str(role_id) for role_id in giveaway.blocked_role_ids],
        min_account_days=giveaway.min_account_days,
        min_member_days=giveaway.min_member_days,
        min_invites=giveaway.min_invites,
        bonus_roles=[BonusRole(role_id=str(role_id), entries=entries) for role_id, entries in giveaway.bonus_roles],
        ping_role_id=str(giveaway.ping_role_id) if giveaway.ping_role_id else None,
        winner_role_id=str(giveaway.winner_role_id) if giveaway.winner_role_id else None,
        color=giveaway.color,
        image_url=giveaway.image_url,
        image_file=giveaway.image_file,
        image_src=await _image_src(client, giveaway),
        button_label=giveaway.button_label,
        button_emoji=giveaway.button_emoji,
        button_style=giveaway.button_style,  # type: ignore[arg-type]
        created_at=_ms(giveaway.created_at),
    )


async def _found(guild: discord.Guild, giveaway_id: int) -> GiveawayTable:
    if giveaway := await giveaways_db.fetch_giveaway(guild.id, giveaway_id):
        return giveaway
    raise SettingError("That giveaway is gone. It may have been deleted.")


def _channel(guild: discord.Guild, channel_id: str) -> discord.TextChannel:
    channel = resolve.text_channel(guild, channel_id)
    assert channel is not None
    perms = channel.permissions_for(guild.me)
    if not (perms.view_channel and perms.send_messages):
        raise SettingError(f"Square can't send messages in #{channel.name}.")
    return channel


def _role_ids(guild: discord.Guild, role_ids: list[str]) -> list[int]:
    return [role.id for role in resolve.roles(guild, role_ids)]


def _bonus_roles(guild: discord.Guild, bonus: list[BonusRole]) -> list[list[int]]:
    roles = resolve.roles(guild, [entry.role_id for entry in bonus])
    if len(roles) != len(bonus):
        raise SettingError("Each bonus role can only be listed once.")
    return [[role.id, entry.entries] for role, entry in zip(roles, bonus, strict=True)]


def _ping_role(guild: discord.Guild, member: discord.Member, role_id: str | None) -> int | None:
    if role_id is None:
        return None
    role = guild.get_role(int(role_id))
    if role is None:
        raise SettingError("That role isn't in this server.")
    if role.is_default() or not role.mentionable:
        name = "@everyone" if role.is_default() else f"@{role.name}"
        if not member.guild_permissions.mention_everyone:
            raise SettingError(f"Pinging {name} needs the Mention Everyone permission.")
        if not guild.me.guild_permissions.mention_everyone:
            raise SettingError(f"Square needs the Mention Everyone permission to ping {name}.")
    return role.id


def _winner_role(guild: discord.Guild, role_id: str | None) -> int | None:
    role = resolve.role(guild, role_id)
    if role is None:
        return None
    if role.is_default() or role.managed:
        raise SettingError(f"@{role.name} can't be given to winners.")
    if not role.is_assignable():
        raise SettingError(f"Square can't give @{role.name}. Move Square's role above it and allow Manage Roles.")
    return role.id


def _min_invites(guild: discord.Guild, count: int) -> int:
    if count and not cache.enabled(guild.id, Module.INVITES):
        raise SettingError("Turn on the Invites module to ask for invites.")
    return count


def _times(starts_ms: int | None, ends_ms: int, *, scheduled: bool) -> tuple[datetime, datetime]:
    now = actions.now()
    starts = _at(starts_ms) if scheduled and starts_ms is not None else now
    if scheduled and starts_ms is not None and starts <= now:
        starts = now
    ends = _at(ends_ms)
    if starts - now > MAX_LEAD:
        raise SettingError("A giveaway can be scheduled up to a year ahead.")
    if ends - max(starts, now) < MIN_LENGTH:
        raise SettingError("The giveaway has to end at least 10 seconds after it starts.")
    if ends - starts > MAX_LENGTH:
        raise SettingError("A giveaway can run for up to a year.")
    return starts, ends


def _text(prize: str, description: str) -> tuple[str, str]:
    prize, description = prize.strip(), description.strip()
    if not prize:
        raise SettingError("Give the prize a name.")
    if len(prize) + len(description) > TEXT_BUDGET:
        raise SettingError(f"The prize and description can add up to {TEXT_BUDGET:,} characters.")
    return prize, description


@get("/", summary="This server's giveaways, newest end first")
async def list_giveaways(
    guild: discord.Guild,
    status: Literal["scheduled", "running", "ended", "all"] = "all",
    q: Annotated[str | None, Parameter(max_length=100)] = None,
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Parameter(ge=1, le=100_000)] = 1,
) -> GiveawayPage:
    text = q.strip() if q else None
    counts = await giveaways_db.count_by_status(guild.id)
    rows, total = await giveaways_db.list_giveaways(
        guild.id, None if status == "all" else status, text, order, (page - 1) * PAGE_SIZE, PAGE_SIZE
    )
    pages = max(1, -(-total // PAGE_SIZE))
    return GiveawayPage(
        items=[GiveawaySummary(**_summary_fields(row)) for row in rows],
        page=min(page, pages),
        pages=pages,
        total=total,
        **counts,
    )


@post(
    "/",
    summary="Start or schedule a giveaway",
    status_code=200,
    responses=REFUSED,
    request_max_body_size=BODY_LIMIT,
)
async def create_giveaway(
    client: Client, guild: discord.Guild, member: discord.Member, data: GiveawayCreate
) -> Giveaway:
    channel = _channel(guild, data.channel_id)
    if data.image_data and data.image_url:
        raise SettingError("Use an uploaded image or a link, not both.")
    upload = _upload(guild, data.image_data) if data.image_data else None
    prize, description = _text(data.prize, data.description)
    starts, ends = _times(data.starts_at, data.ends_at, scheduled=True)
    host_id = int(data.host_id) if data.host_id else member.id
    values = {
        "status": "scheduled" if starts > actions.now() else "running",
        "channel_id": channel.id,
        "host_id": host_id,
        "prize": prize,
        "description": description,
        "winner_count": data.winner_count,
        "starts_at": starts,
        "ends_at": ends,
        "required_role_ids": _role_ids(guild, data.required_role_ids),
        "require_all_roles": data.require_all_roles,
        "blocked_role_ids": _role_ids(guild, data.blocked_role_ids),
        "min_account_days": data.min_account_days,
        "min_member_days": data.min_member_days,
        "min_invites": _min_invites(guild, data.min_invites),
        "bonus_roles": _bonus_roles(guild, data.bonus_roles),
        "ping_role_id": _ping_role(guild, member, data.ping_role_id),
        "winner_role_id": _winner_role(guild, data.winner_role_id),
        "color": data.color,
        "image_url": data.image_url,
        "image_file": upload[0] if upload else None,
        "button_label": data.button_label.strip(),
        "button_emoji": resolve.emoji(client, data.button_emoji),
        "button_style": data.button_style,
    }
    created = await giveaways_db.create_giveaway(guild.id, **values)
    giveaway = await _found(guild, created.id)
    if giveaway.status == "scheduled" and upload:
        try:
            await files.stash(guild.id, giveaway.id, *upload)
        except storage.ERRORS as exc:
            await giveaways_db.delete_giveaway(giveaway)
            raise SettingError("Square couldn't save the image. Try again in a moment.") from exc
    if giveaway.status == "running" and not await actions.post(client, giveaway, upload[1] if upload else None):
        await giveaways_db.delete_giveaway(giveaway)
        raise SettingError(f"Square couldn't post the giveaway in #{channel.name}. Check its permissions there.")
    actions.wake()
    return await _out(client, guild, giveaway)


@get("/{giveaway_id:int}", summary="One giveaway with everything about it")
async def get_giveaway(client: Client, guild: discord.Guild, giveaway_id: GiveawayId) -> Giveaway:
    return await _out(client, guild, await _found(guild, giveaway_id))


@patch(
    "/{giveaway_id:int}",
    summary="Change a giveaway and redraw its message",
    responses=REFUSED,
    request_max_body_size=BODY_LIMIT,
)
async def update_giveaway(
    client: Client, guild: discord.Guild, member: discord.Member, giveaway_id: GiveawayId, data: GiveawayPatch
) -> Giveaway:
    giveaway = await _found(guild, giveaway_id)
    sent = {name for name in GiveawayPatch.__struct_fields__ if getattr(data, name) is not UNSET}
    if giveaway.status == "ended" and sent & _LIVE_ONLY:
        raise SettingError("Only the prize, text, host and look can change once a giveaway has ended.")
    if giveaway.status == "running" and sent & {"channel_id", "starts_at"}:
        raise SettingError("A running giveaway can't move to another channel or start time.")

    changes: dict[str, Any] = {}
    if "channel_id" in sent:
        changes["channel_id"] = _channel(guild, data.channel_id).id  # type: ignore[arg-type]
    if sent & {"prize", "description"}:
        prize, description = _text(
            data.prize if data.prize is not UNSET else giveaway.prize,
            data.description if data.description is not UNSET else giveaway.description,
        )
        changes.update(prize=prize, description=description)
    if sent & {"starts_at", "ends_at"}:
        starts_ms = data.starts_at if data.starts_at is not UNSET else _ms(giveaway.starts_at)
        ends_ms = data.ends_at if data.ends_at is not UNSET else _ms(giveaway.ends_at)
        starts, ends = _times(starts_ms, ends_ms, scheduled=giveaway.status == "scheduled")
        if giveaway.status == "scheduled":
            changes["starts_at"] = starts
        changes["ends_at"] = ends
    if "host_id" in sent:
        changes["host_id"] = int(data.host_id)  # type: ignore[arg-type]
    if "winner_count" in sent:
        changes["winner_count"] = data.winner_count
    if "required_role_ids" in sent:
        changes["required_role_ids"] = _role_ids(guild, data.required_role_ids)  # type: ignore[arg-type]
    if "blocked_role_ids" in sent:
        changes["blocked_role_ids"] = _role_ids(guild, data.blocked_role_ids)  # type: ignore[arg-type]
    if "bonus_roles" in sent:
        changes["bonus_roles"] = _bonus_roles(guild, data.bonus_roles)  # type: ignore[arg-type]
    if "ping_role_id" in sent:
        changes["ping_role_id"] = _ping_role(guild, member, data.ping_role_id)  # type: ignore[arg-type]
    if "winner_role_id" in sent:
        changes["winner_role_id"] = _winner_role(guild, data.winner_role_id)  # type: ignore[arg-type]
    if "min_invites" in sent:
        changes["min_invites"] = _min_invites(guild, data.min_invites)  # type: ignore[arg-type]
    if "button_emoji" in sent:
        changes["button_emoji"] = resolve.emoji(client, data.button_emoji)  # type: ignore[arg-type]
    if "button_label" in sent:
        changes["button_label"] = data.button_label.strip()  # type: ignore[union-attr]
    for name in ("require_all_roles", "min_account_days", "min_member_days", "color", "button_style"):
        if name in sent:
            changes[name] = getattr(data, name)
    if data.image_data is not UNSET and data.image_url:
        raise SettingError("Use an uploaded image or a link, not both.")
    upload = _upload(guild, data.image_data) if data.image_data is not UNSET else None

    # Applied in memory first, so an image swap redraws with every change at once
    for name, value in changes.items():
        setattr(giveaway, name, value)
    swapped = await _change_image(client, giveaway, data, upload, changes)
    if changes:
        await giveaways_db.save_giveaway(giveaway, **changes)
        if not swapped:
            await actions.redraw(client, giveaway)
        if changes.keys() & {"starts_at", "ends_at"}:
            actions.wake()
    return await _out(client, guild, giveaway)


async def _change_image(
    client: Client, giveaway: GiveawayTable, data: GiveawayPatch, upload: Upload | None, changes: dict[str, Any]
) -> bool:
    """Adds the fields to save to `changes`. True when the message was already redrawn with the new image."""
    if upload is None and data.image_url is UNSET:
        return False
    link = None if upload or data.image_url is UNSET else data.image_url
    giveaway.image_url = changes["image_url"] = link
    guild_id = giveaway.guild.guild_id
    if giveaway.status == "scheduled":
        if upload:
            try:
                await files.stash(guild_id, giveaway.id, *upload)
            except storage.ERRORS as exc:
                raise SettingError("Square couldn't save the image. Try again in a moment.") from exc
        elif giveaway.image_file:
            await files.drop(guild_id, giveaway.id)
        giveaway.image_file = changes["image_file"] = upload[0] if upload else None
        return False
    if not upload and not giveaway.image_file:
        return False
    if not await actions.swap_image(client, giveaway, *(upload[:2] if upload else (None, None))):
        raise SettingError("Square couldn't change the image on the giveaway's message. It may have been deleted.")
    return True


@get(
    "/{giveaway_id:int}/image",
    summary="A scheduled giveaway's uploaded image, before it's posted",
    media_type="application/octet-stream",
    responses={**REFUSED, **stored.RESPONSES},
)
async def giveaway_image(guild: discord.Guild, giveaway_id: GiveawayId, byte_range: stored.Range = None) -> Stream:
    giveaway = await _found(guild, giveaway_id)
    if giveaway.status != "scheduled" or not giveaway.image_file:
        raise SettingError("This giveaway's image is on its Discord message now.")
    key = files.key(guild.id, giveaway.id, giveaway.image_file)
    return await stored.serve(key, byte_range, "This giveaway's image is gone. Upload it again.")


@delete("/{giveaway_id:int}", summary="Delete a giveaway and its message", status_code=204)
async def delete_giveaway(client: Client, guild: discord.Guild, giveaway_id: GiveawayId) -> None:
    if giveaway := await giveaways_db.fetch_giveaway(guild.id, giveaway_id):
        await actions.remove(client, giveaway)


@post("/{giveaway_id:int}/start", summary="Start a scheduled giveaway now", status_code=200, responses=REFUSED)
async def start_giveaway(client: Client, guild: discord.Guild, giveaway_id: GiveawayId) -> Giveaway:
    giveaway = await _found(guild, giveaway_id)
    if giveaway.status != "scheduled":
        raise SettingError("This giveaway has already started.")
    _channel(guild, str(giveaway.channel_id))
    if giveaway.ends_at - actions.now() < MIN_LENGTH:
        raise SettingError("Move the end time later first. It would end as soon as it starts.")
    if not await actions.post(client, giveaway):
        raise SettingError("Square couldn't post the giveaway. Check its permissions in that channel.")
    return await _out(client, guild, giveaway)


@post(
    "/{giveaway_id:int}/end",
    summary="End a running giveaway now and pick its winners",
    status_code=200,
    responses=REFUSED,
)
async def end_giveaway(client: Client, guild: discord.Guild, giveaway_id: GiveawayId) -> Giveaway:
    giveaway = await _found(guild, giveaway_id)
    if giveaway.status == "scheduled":
        raise SettingError("This giveaway hasn't started yet.")
    if not await actions.finish(client, giveaway):
        raise SettingError("This giveaway has already ended.")
    return await _out(client, guild, giveaway)


@post("/{giveaway_id:int}/reroll", summary="Pick new winners for an ended giveaway", status_code=200, responses=REFUSED)
async def reroll_giveaway(client: Client, guild: discord.Guild, giveaway_id: GiveawayId, data: Reroll) -> Giveaway:
    giveaway = await _found(guild, giveaway_id)
    if giveaway.status != "ended":
        raise SettingError("A giveaway can only be rerolled once it has ended.")
    replace = None
    if data.user_ids is not None:
        replace = [int(user_id) for user_id in dict.fromkeys(data.user_ids)]
        if not replace or not set(replace) <= set(giveaway.winner_ids):
            raise SettingError("Pick winners of this giveaway to replace.")
    elif not giveaway.winner_ids and not giveaway.entry_count:
        raise SettingError("Nobody entered this giveaway.")
    if not await actions.reroll(client, giveaway, replace):
        raise SettingError("There's nobody left who can win. Everyone else was drawn before or can't enter.")
    return await _out(client, guild, giveaway)


@get("/{giveaway_id:int}/entrants", summary="Everyone in a giveaway, with their entries and odds")
async def list_entrants(
    client: Client,
    guild: discord.Guild,
    giveaway_id: GiveawayId,
    q: Annotated[str | None, Parameter(max_length=100)] = None,
    sort: Literal["entered", "entries"] = "entered",
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Parameter(ge=1, le=100_000)] = 1,
) -> EntrantPage:
    giveaway = await _found(guild, giveaway_id)
    winners = set(giveaway.winner_ids)
    rows: list[tuple[int, discord.Member | None, int, int, int, bool, datetime]] = []
    entries = await giveaways_db.fetch_entries(giveaway.id)
    totals = await actions.invite_totals(giveaway, guild.id, [user_id for user_id, _, _ in entries])
    for user_id, bonus, entered_at in entries:
        member = guild.get_member(user_id)
        eligible = (
            member is not None and not member.bot and actions.refusal(giveaway, member, totals.get(user_id, 0)) is None
        )
        role_bonus = actions.role_bonus(giveaway, member)
        rows.append((user_id, member, bonus, role_bonus, 1 + role_bonus + bonus, eligible, entered_at))
    tickets = sum(row[4] for row in rows if row[5])
    eligible = sum(1 for row in rows if row[5])

    needle = (q or "").strip().lower()
    if needle:
        rows = [
            row
            for row in rows
            if needle == str(row[0])
            or (row[1] and (needle in row[1].display_name.lower() or needle in row[1].name.lower()))
        ]
    if sort == "entries":
        rows.sort(key=lambda row: row[4], reverse=order == "desc")
    elif order == "desc":
        rows.reverse()

    pages = max(1, -(-len(rows) // PAGE_SIZE))
    page = min(page, pages)
    chunk = rows[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
    people = await people_of(client, guild, [row[0] for row in chunk])
    return EntrantPage(
        items=[
            Entrant(
                user=person,
                member=member is not None,
                eligible=is_eligible,
                entries=entries,
                bonus=bonus,
                role_bonus=role_bonus,
                chance=entries / tickets if is_eligible and tickets else 0,
                entered_at=_ms(entered_at),
                winner=user_id in winners,
            )
            for (user_id, member, bonus, role_bonus, entries, is_eligible, entered_at), person in zip(
                chunk, people, strict=True
            )
        ],
        page=page,
        pages=pages,
        total=len(rows),
        people=giveaway.entry_count,
        eligible=eligible,
        tickets=tickets,
    )


@post("/{giveaway_id:int}/entrants/bonus", summary="Give entrants extra entries", status_code=204, responses=REFUSED)
async def set_entrant_bonus(guild: discord.Guild, giveaway_id: GiveawayId, data: EntrantBonus) -> None:
    giveaway = await _found(guild, giveaway_id)
    if giveaway.status == "ended":
        raise SettingError("Extra entries can't change once the giveaway has ended.")
    await giveaways_db.set_bonus(giveaway.id, [int(user_id) for user_id in data.user_ids], data.bonus)


@post("/{giveaway_id:int}/entrants/remove", summary="Take people out of a giveaway", status_code=204, responses=REFUSED)
async def remove_entrants(client: Client, guild: discord.Guild, giveaway_id: GiveawayId, data: EntrantRemove) -> None:
    giveaway = await _found(guild, giveaway_id)
    if giveaway.status == "ended":
        raise SettingError("People can't be removed once the giveaway has ended. Reroll a winner instead.")
    if await giveaways_db.leave(giveaway.id, [int(user_id) for user_id in data.user_ids]):
        actions.recount(client, giveaway.id)


router = Router(
    "/guilds/{guild_id:str}/giveaways",
    opt={"module": Module.GIVEAWAYS},
    tags=["Giveaways"],
    exception_handlers={SettingError: refused},
    dependencies={
        "guild": Provide(provide_guild, sync_to_thread=False),
        "member": Provide(provide_member, sync_to_thread=False),
    },
    route_handlers=[
        list_giveaways,
        create_giveaway,
        get_giveaway,
        update_giveaway,
        giveaway_image,
        delete_giveaway,
        start_giveaway,
        end_giveaway,
        reroll_giveaway,
        list_entrants,
        set_entrant_bonus,
        remove_entrants,
    ],
)
