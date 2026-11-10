import discord
import msgspec
from msgspec import UNSET, UnsetType
from square.music.dj import MAX_ROLES
from square.settings import invites, tickets
from square.utils.server_log import LogType
from typing import Annotated, Literal, get_args

# Discord IDs go past JavaScript's safe integer range, so the API sends them as strings
Snowflake = Annotated[str, msgspec.Meta(pattern=r"^\d{17,20}$", description="A Discord ID")]

ChannelKind = Literal["text", "news", "voice", "stage_voice", "category", "forum", "media"]
_CHANNEL_KINDS: frozenset[str] = frozenset(get_args(ChannelKind))


class Schema(msgspec.Struct, rename="camel", kw_only=True, forbid_unknown_fields=True):
    pass


class Health(Schema):
    ready: bool
    guilds: int
    latency_ms: int | None


class Guild(Schema):
    id: Snowflake
    name: str
    icon_url: str | None
    member_count: int


class Channel(Schema):
    id: Snowflake
    name: str
    type: ChannelKind
    parent_id: Snowflake | None
    position: int


class Role(Schema):
    id: Snowflake
    name: str
    color: str | None
    position: int
    managed: bool
    assignable: bool  # Below the bot's top role and not managed, so the bot can give it out


class Problem(Schema):
    detail: str


class Notes(Schema):
    """Things the bot couldn't finish, like a channel it wasn't allowed to delete."""

    notes: list[str]


class GeneralSettings(Schema):
    autorole_id: Snowflake | None
    media_only_channel_id: Snowflake | None


class GeneralPatch(Schema):
    autorole_id: Snowflake | None | UnsetType = UNSET
    media_only_channel_id: Snowflake | None | UnsetType = UNSET


class LogChannels(Schema):
    moderation: Snowflake | None = None
    members: Snowflake | None = None
    messages: Snowflake | None = None
    channels: Snowflake | None = None
    roles: Snowflake | None = None
    server: Snowflake | None = None
    voice: Snowflake | None = None
    invites: Snowflake | None = None
    automod: Snowflake | None = None
    tickets: Snowflake | None = None


class LogChannelsPatch(Schema):
    """Log types to change. `null` turns one off."""

    moderation: Snowflake | None | UnsetType = UNSET
    members: Snowflake | None | UnsetType = UNSET
    messages: Snowflake | None | UnsetType = UNSET
    channels: Snowflake | None | UnsetType = UNSET
    roles: Snowflake | None | UnsetType = UNSET
    server: Snowflake | None | UnsetType = UNSET
    voice: Snowflake | None | UnsetType = UNSET
    invites: Snowflake | None | UnsetType = UNSET
    automod: Snowflake | None | UnsetType = UNSET
    tickets: Snowflake | None | UnsetType = UNSET


# A new `LogType` needs a field in both structs above, so the bot refuses to start until it has one
for _struct in (LogChannels, LogChannelsPatch):
    if set(_struct.__struct_fields__) != {log_type.key for log_type in LogType}:
        raise RuntimeError(f"{_struct.__name__} must have exactly one field per LogType key")


class LogSettings(Schema):
    channels: LogChannels


class LogPatch(Schema):
    channels: LogChannelsPatch


class InviteSettings(Schema):
    tracker: bool
    fake_days: int


class InvitePatch(Schema):
    tracker: bool | UnsetType = UNSET
    fake_days: Annotated[int, msgspec.Meta(ge=0, le=invites.MAX_FAKE_DAYS)] | UnsetType = UNSET


class MusicSettings(Schema):
    request_channel_id: Snowflake | None
    stay_channel_id: Snowflake | None
    dj_mode: bool
    dj_role_ids: list[Snowflake]


class MusicPatch(Schema):
    stay_channel_id: Snowflake | None | UnsetType = UNSET
    dj_mode: bool | UnsetType = UNSET
    dj_role_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_ROLES)] | UnsetType = UNSET


class TicketSettings(Schema):
    enabled: bool
    category_id: Snowflake | None
    support_role_ids: list[Snowflake]
    max_open: tickets.MaxOpen
    confirm_close: bool
    panel_channel_id: Snowflake | None


class TicketPatch(Schema):
    enabled: bool | UnsetType = UNSET
    category_id: Snowflake | None | UnsetType = UNSET
    support_role_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=tickets.MAX_SUPPORT_ROLES)] | UnsetType = UNSET
    max_open: tickets.MaxOpen | UnsetType = UNSET
    confirm_close: bool | UnsetType = UNSET


def id_of(item: discord.abc.Snowflake | None) -> str | None:
    return None if item is None else str(item.id)


def guild_out(guild: discord.Guild) -> Guild:
    return Guild(
        id=str(guild.id),
        name=guild.name,
        icon_url=guild.icon.url if guild.icon else None,
        member_count=guild.member_count or 0,
    )


def channels_out(guild: discord.Guild) -> list[Channel]:
    return [
        Channel(
            id=str(channel.id),
            name=channel.name,
            type=kind,
            parent_id=id_of(channel.category),
            position=channel.position,
        )
        for channel in sorted(guild.channels, key=lambda channel: channel.position)
        if (kind := str(channel.type)) in _CHANNEL_KINDS
    ]


def roles_out(guild: discord.Guild) -> list[Role]:
    top = guild.me.top_role
    return [
        Role(
            id=str(role.id),
            name=role.name,
            color=str(role.color) if role.color.value else None,
            position=role.position,
            managed=role.managed,
            assignable=not role.managed and role < top,
        )
        for role in reversed(guild.roles)
        if not role.is_default()
    ]
