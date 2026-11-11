import discord
import msgspec
import time
from msgspec import UNSET, UnsetType
from sonolink import QueueMode
from sonolink.models import Playable, Playlist
from square.core import Client
from square.music.core import SquarePlayer, get_player, requester_id
from square.music.dj import MAX_ROLES
from square.music.history import history_tracks
from square.utils.server_log import LogType
from typing import Annotated, Literal, get_args

# Discord IDs go past JavaScript's safe integer range, so the API sends them as strings
Snowflake = Annotated[str, msgspec.Meta(pattern=r"^\d{17,20}$", description="A Discord ID")]

ChannelKind = Literal["text", "news", "voice", "stage_voice", "category", "forum", "media"]
_CHANNEL_KINDS: frozenset[str] = frozenset(get_args(ChannelKind))
Loop = Literal["off", "track", "queue"]
_LOOP: dict[QueueMode, Loop] = {QueueMode.NORMAL: "off", QueueMode.LOOP: "track", QueueMode.LOOP_ALL: "queue"}

QUEUE_LIMIT = 100
MAX_FAKE_DAYS = 365
MAX_SUPPORT_ROLES = 10
MaxOpen = Literal[1, 2, 3, 5]


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
    can_manage: bool  # Settings need Manage Server. Music only needs membership, with its own rules per control


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


class JoinDay(Schema):
    date: str  # UTC day, YYYY-MM-DD
    count: int


class MemberJoins(Schema):
    days: list[JoinDay]  # Oldest first. Only members still in the server, since Discord keeps no record of leavers
    members: int


class Track(Schema):
    identifier: str
    title: str
    author: str
    uri: str | None
    artwork_url: str | None
    length_ms: int
    is_stream: bool
    source: str
    requester_id: Snowflake | None


class PlayerState(Schema):
    voice_channel_id: Snowflake | None
    track: Track | None
    paused: bool
    position_ms: int
    position_at: int  # Unix ms when `position_ms` was read, so the dashboard can keep the clock moving on its own
    volume: int
    loop: Loop
    shuffle: bool
    autoplay: bool
    eq: list[str]  # Active presets, by the names `GET /music/eq-presets` lists


class QueueState(Schema):
    tracks: list[Track]  # Only the first `QUEUE_LIMIT`, so a huge queue doesn't flood every update
    total: int


class PlaylistInfo(Schema):
    name: str
    track_count: int


class SearchResults(Schema):
    playlist: PlaylistInfo | None  # Set when the query was a playlist link, which queues as a whole
    tracks: list[Track]


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
    fake_days: Annotated[int, msgspec.Meta(ge=0, le=MAX_FAKE_DAYS)] | UnsetType = UNSET


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
    max_open: MaxOpen
    confirm_close: bool
    panel_channel_id: Snowflake | None


class TicketPatch(Schema):
    enabled: bool | UnsetType = UNSET
    category_id: Snowflake | None | UnsetType = UNSET
    support_role_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_SUPPORT_ROLES)] | UnsetType = UNSET
    max_open: MaxOpen | UnsetType = UNSET
    confirm_close: bool | UnsetType = UNSET


def id_of(item: discord.abc.Snowflake | None) -> str | None:
    return None if item is None else str(item.id)


def guild_out(guild: discord.Guild, member: discord.Member) -> Guild:
    return Guild(
        id=str(guild.id),
        name=guild.name,
        icon_url=guild.icon.replace(size=128, static_format="webp").url if guild.icon else None,
        member_count=guild.member_count or 0,
        can_manage=member.guild_permissions.manage_guild,
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


def _track(player: SquarePlayer | None, track: Playable) -> Track:
    rid = requester_id(player, track) if player else None
    return Track(
        identifier=track.identifier,
        title=track.title,
        author=track.author,
        uri=track.uri,
        artwork_url=track.artwork,
        length_ms=track.length,
        is_stream=track.is_stream,
        source=track.source_name,
        requester_id=None if rid is None else str(rid),
    )


def live_player(client: Client, guild_id: int) -> SquarePlayer | None:
    player = get_player(client, guild_id)
    return player if player and player.connected else None


def player_out(client: Client, guild: discord.Guild) -> PlayerState:
    if (player := live_player(client, guild.id)) is None:
        return PlayerState(
            voice_channel_id=None,
            track=None,
            paused=False,
            position_ms=0,
            position_at=round(time.time() * 1000),
            volume=100,
            loop="off",
            shuffle=False,
            autoplay=False,
            eq=[],
        )
    return PlayerState(
        voice_channel_id=id_of(player.channel),
        track=_track(player, player.current) if player.current else None,
        paused=player.paused,
        position_ms=player.position if player.current else 0,
        position_at=round(time.time() * 1000),
        volume=player.volume,
        loop=_LOOP[player.queue_mode],
        shuffle=player.shuffled,
        autoplay=player.autoplay_on,
        eq=list(player.presets),
    )


def queue_out(client: Client, guild: discord.Guild) -> QueueState:
    if (player := live_player(client, guild.id)) is None:
        return QueueState(tracks=[], total=0)
    queue = player.queue
    # Indexed rather than `queue.tracks`, which copies the whole queue
    return QueueState(tracks=[_track(player, queue[i]) for i in range(min(len(queue), QUEUE_LIMIT))], total=len(queue))


def history_out(player: SquarePlayer | None) -> list[Track]:
    return [_track(player, track) for track in history_tracks(player)] if player else []


def search_out(data: object, limit: int) -> SearchResults:
    """A search result as the dashboard shows it. Requesters are left out, since nobody has queued these yet."""
    if isinstance(data, Playlist):
        return SearchResults(
            playlist=PlaylistInfo(name=data.name, track_count=len(data)),
            tracks=[_track(None, track) for track in data.tracks[:limit]],
        )
    found = data if isinstance(data, list) else [data] if data else []
    return SearchResults(playlist=None, tracks=[_track(None, track) for track in found[:limit]])
