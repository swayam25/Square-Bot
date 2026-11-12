import discord
import msgspec
import time
from msgspec import UNSET, UnsetType
from sonolink import QueueMode
from sonolink.models import Playable, Playlist
from square.core import Client
from square.modules import Module
from square.music import dj, store
from square.music.core import SquarePlayer, get_player, requester_id
from square.music.history import history_tracks
from square.utils.server_log import LogType
from typing import Annotated, Literal, get_args

# Discord IDs go past JavaScript's safe integer range, so the API sends them as strings
Snowflake = Annotated[str, msgspec.Meta(pattern=r"^\d{17,20}$", description="A Discord ID")]

ChannelKind = Literal["text", "news", "voice", "stage_voice", "category", "forum", "media"]
_CHANNEL_KINDS: frozenset[str] = frozenset(get_args(ChannelKind))
Loop = Literal["off", "track", "queue"]
# Search sources the Lavalink node answers for. SoundCloud and Deezer are left out: the node errors or finds nothing
SearchSource = Literal["youtube_music", "youtube", "spotify", "apple_music"]
_LOOP: dict[QueueMode, Loop] = {QueueMode.NORMAL: "off", QueueMode.LOOP: "track", QueueMode.LOOP_ALL: "queue"}

QUEUE_LIMIT = 100
PLAYLIST_LIMIT = 500
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


class ServerStats(Schema):
    humans: int
    bots: int
    in_voice: int  # Humans in a voice channel right now
    boosts: int
    boost_level: int
    text_channels: int
    voice_channels: int
    roles: int  # @everyone left out
    created_at: int  # Unix ms


class Person(Schema):
    id: Snowflake
    name: str  # Server nickname when they still have one, else their display name
    avatar_url: str


class Track(Schema):
    identifier: str
    title: str
    author: str
    uri: str | None
    artwork_url: str | None
    length_ms: int
    is_stream: bool
    source: str
    isrc: str | None  # Set for Spotify and Apple Music tracks, which makes lyrics lookups exact
    requester: Person | None


class TrackFailure(Schema):
    title: str
    reason: str | None
    at: int  # Unix ms. Also what tells two failures apart


class SkipVote(Schema):
    started_by: Person | None
    voter_ids: list[Snowflake]
    needed: int  # Moves as members join or leave the voice channel
    ends_at: int  # Unix ms


class Viewer(Schema):
    dj: bool  # May use every control. Others can add songs, replay, skip or remove their own, and vote to skip
    in_channel: bool  # In the bot's voice channel, which every control asks for
    deafened: bool  # Deafened members can't vote on a skip


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
    listeners: list[Person]  # Everyone but bots in the bot's voice channel
    failure: TrackFailure | None  # Outlives the player, since a failure often ends it
    vote: SkipVote | None
    viewer: Viewer  # The member this state was built for


class QueueState(Schema):
    tracks: list[Track]  # Only the first `QUEUE_LIMIT`, so a huge queue doesn't flood every update
    total: int
    autoplay: list[Track]  # Autoplay's picks, played once the queue runs out. Empty while autoplay is off


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
    fake_days: int


class InvitePatch(Schema):
    fake_days: Annotated[int, msgspec.Meta(ge=0, le=MAX_FAKE_DAYS)] | UnsetType = UNSET


class MusicSettings(Schema):
    request_channel_id: Snowflake | None
    stay_channel_id: Snowflake | None
    dj_mode: bool
    dj_role_ids: list[Snowflake]


class MusicPatch(Schema):
    stay_channel_id: Snowflake | None | UnsetType = UNSET
    dj_mode: bool | UnsetType = UNSET
    dj_role_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=dj.MAX_ROLES)] | UnsetType = UNSET


class TicketSettings(Schema):
    category_id: Snowflake | None
    support_role_ids: list[Snowflake]
    max_open: MaxOpen
    confirm_close: bool
    panel_channel_id: Snowflake | None


class TicketPatch(Schema):
    category_id: Snowflake | None | UnsetType = UNSET
    support_role_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_SUPPORT_ROLES)] | UnsetType = UNSET
    max_open: MaxOpen | UnsetType = UNSET
    confirm_close: bool | UnsetType = UNSET


class ModuleSettings(Schema):
    logs: bool
    tickets: bool
    invites: bool


class ModulePatch(Schema):
    logs: bool | UnsetType = UNSET
    tickets: bool | UnsetType = UNSET
    invites: bool | UnsetType = UNSET


# A new `Module` needs a field in both structs above, so the bot refuses to start until it has one
for _struct in (ModuleSettings, ModulePatch):
    if set(_struct.__struct_fields__) != {module.value for module in Module}:
        raise RuntimeError(f"{_struct.__name__} must have exactly one field per Module")


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


def _person_out(user: discord.User | discord.Member) -> Person:
    return Person(
        id=str(user.id),
        name=user.display_name,
        avatar_url=user.display_avatar.replace(size=64, static_format="webp").url,
    )


def _person(player: SquarePlayer, user_id: int) -> Person | None:
    user = player.guild.get_member(user_id) or player.client.get_user(user_id)
    return None if user is None else _person_out(user)


def _listeners(player: SquarePlayer) -> list[Person]:
    members = getattr(player.channel, "members", [])
    return [_person_out(m) for m in sorted(members, key=lambda m: m.display_name.casefold()) if not m.bot]


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
        isrc=track.isrc,
        requester=None if player is None or rid is None else _person(player, rid),
    )


def _failure(guild_id: int) -> TrackFailure | None:
    failed = store.failure(guild_id)
    return TrackFailure(title=failed.title, reason=failed.reason, at=failed.at) if failed else None


def live_player(client: Client, guild_id: int) -> SquarePlayer | None:
    player = get_player(client, guild_id)
    return player if player and player.connected else None


def _vote(player: SquarePlayer) -> SkipVote | None:
    vote = store.skip_vote(player.guild.id)
    if (
        vote is None
        or vote.is_finished()
        or player.current is None
        or vote.track.identifier != player.current.identifier
    ):
        return None
    return SkipVote(
        started_by=_person(player, vote.starter.id),
        voter_ids=[str(voter) for voter in vote.voters],
        needed=vote.needed,
        ends_at=round(vote.expires_at.timestamp() * 1000),
    )


def _viewer(player: SquarePlayer | None, member: discord.Member) -> Viewer:
    voice = member.voice
    in_channel = player is not None and voice is not None and voice.channel == player.channel
    return Viewer(
        dj=dj.is_dj(member, player),
        in_channel=in_channel,
        deafened=in_channel and (voice.deaf or voice.self_deaf),
    )


def player_out(client: Client, guild: discord.Guild, member: discord.Member) -> PlayerState:
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
            listeners=[],
            failure=_failure(guild.id),
            vote=None,
            viewer=_viewer(None, member),
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
        listeners=_listeners(player),
        failure=_failure(guild.id),
        vote=_vote(player),
        viewer=_viewer(player, member),
    )


def queue_out(client: Client, guild: discord.Guild) -> QueueState:
    if (player := live_player(client, guild.id)) is None:
        return QueueState(tracks=[], total=0, autoplay=[])
    queue = player.queue
    picks = list(queue.autoplay_tracks)[:QUEUE_LIMIT] if player.autoplay_on else []
    # Indexed rather than `queue.tracks`, which copies the whole queue
    return QueueState(
        tracks=[_track(player, queue[i]) for i in range(min(len(queue), QUEUE_LIMIT))],
        total=len(queue),
        autoplay=[_track(player, track) for track in picks],
    )


def history_out(player: SquarePlayer | None) -> list[Track]:
    return [_track(player, track) for track in history_tracks(player)] if player else []


def search_out(data: object, limit: int) -> SearchResults:
    """
    A search result as the dashboard shows it. Requesters are left out, since nobody has queued these yet.

    `limit` caps plain matches; a playlist lists its tracks so they can be picked one by one.
    """
    if isinstance(data, Playlist):
        return SearchResults(
            playlist=PlaylistInfo(name=data.name, track_count=len(data)),
            tracks=[_track(None, track) for track in data.tracks[:PLAYLIST_LIMIT]],
        )
    found = data if isinstance(data, list) else [data] if data else []
    return SearchResults(playlist=None, tracks=[_track(None, track) for track in found[:limit]])
