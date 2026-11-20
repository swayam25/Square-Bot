import discord
import inspect
import msgspec
import time
from discord.commands import ApplicationCommand, MessageCommand, SlashCommand, SlashCommandGroup, UserCommand
from msgspec import UNSET, UnsetType
from sonolink import QueueMode
from sonolink.models import Playable, Playlist
from square.api import resolve
from square.cogs.moderation.warnings import MAX_REASON
from square.cogs.tickets.snapshot import Transcript
from square.core import Client
from square.core.cog import Cog
from square.logs.catalog import Event, Log
from square.modules import Module
from square.music import dj, store
from square.music.core import SquarePlayer, get_player, requester_id
from square.music.history import history_tracks
from square.utils import check
from typing import Annotated, Literal, get_args

# Discord IDs go past JavaScript's safe integer range, so the API sends them as strings
Snowflake = Annotated[str, msgspec.Meta(pattern=r"^\d{17,20}$", description="A Discord ID")]
Bitfield = Annotated[str, msgspec.Meta(pattern=r"^\d+$", description="Discord permission bits as a decimal string")]

ChannelKind = Literal["text", "news", "voice", "stage_voice", "category", "forum", "media"]
_CHANNEL_KINDS: frozenset[str] = frozenset(get_args(ChannelKind))
Loop = Literal["off", "track", "queue"]
SearchSource = Literal["youtube_music", "youtube", "spotify", "apple_music"]
_LOOP: dict[QueueMode, Loop] = {QueueMode.NORMAL: "off", QueueMode.LOOP: "track", QueueMode.LOOP_ALL: "queue"}

QUEUE_LIMIT = 100
PLAYLIST_LIMIT = 500
MAX_FAKE_DAYS = 365
MAX_SUPPORT_ROLES = 10
MAX_AUTOROLES = 10
MAX_AUTOROLE_USERS = 50
MAX_AUTOROLE_DELAY = 3600
MAX_STICKY_IGNORE = 25
MAX_BONUS_USERS = 100
MAX_BONUS = 100_000
MAX_OPEN_TICKETS = 25
MaxOpen = Annotated[int, msgspec.Meta(ge=1, le=MAX_OPEN_TICKETS)]


class Schema(msgspec.Struct, rename="camel", kw_only=True, forbid_unknown_fields=True):
    pass


class BotEmoji(Schema):
    name: str
    id: Snowflake | UnsetType = UNSET
    animated: bool = False


class CommandOption(Schema):
    name: str
    type: Literal["string", "integer", "number", "boolean", "user", "channel", "role", "mentionable", "attachment"]
    description: str
    required: bool
    choices: list[str]
    channel_types: list[ChannelKind]
    min: int | float | None
    max: int | float | None
    autocomplete: bool


class BotCommand(Schema):
    name: str
    kind: Literal["slash", "message", "user"]
    description: str
    options: list[CommandOption]
    permissions: Bitfield | None
    install: Literal["server", "both", "account"]


class CommandCategory(Schema):
    name: str
    description: str
    module: Module | None
    commands: list[BotCommand]


class Guild(Schema):
    id: Snowflake
    name: str
    icon_url: str | None
    member_count: int
    can_manage: bool
    can_moderate: bool


class Channel(Schema):
    id: Snowflake
    name: str
    type: ChannelKind
    parent_id: Snowflake | None
    position: int


class MentionedChannel(Schema):
    id: Snowflake
    name: str
    type: ChannelKind
    guild_id: Snowflake
    guild_name: str
    guild_icon_url: str | None


class BotPermissions(Schema):
    guild: Bitfield
    channels: dict[Snowflake, Bitfield]
    top_role: int
    features: list[str]


class Role(Schema):
    id: Snowflake
    name: str
    color: str | None
    position: int
    managed: bool


class Emoji(Schema):
    id: Snowflake
    name: str
    animated: bool
    usable: bool


class JoinDay(Schema):
    date: str  # UTC day, YYYY-MM-DD
    count: int


class MemberJoins(Schema):
    days: list[JoinDay]
    members: int


class ActivityDay(Schema):
    date: str  # UTC day, YYYY-MM-DD
    tickets_opened: int
    tickets_closed: int
    invited: int
    left: int


class Activity(Schema):
    days: list[ActivityDay]


class ServerStats(Schema):
    humans: int
    bots: int
    in_voice: int
    boosts: int
    boost_level: int
    text_channels: int
    voice_channels: int
    roles: int
    created_at: int  # Unix ms


class Person(Schema):
    id: Snowflake
    name: str
    avatar_url: str


class UserMatch(Schema):
    id: Snowflake
    name: str
    username: str
    avatar_url: str
    bot: bool
    member: bool


class Track(Schema):
    identifier: str
    title: str
    author: str
    uri: str | None
    artwork_url: str | None
    length_ms: int
    is_stream: bool
    source: str
    isrc: str | None
    requester: Person | None


class TrackFailure(Schema):
    title: str
    reason: str | None
    at: int  # Unix ms. Also what tells two failures apart


class SkipVote(Schema):
    started_by: Person | None
    voter_ids: list[Snowflake]
    needed: int
    ends_at: int  # Unix ms


class Viewer(Schema):
    dj: bool
    in_channel: bool
    deafened: bool
    queue_lock: str | None = None  # why the bot would refuse to queue for them right now


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
    eq: list[str]
    listeners: list[Person]
    failure: TrackFailure | None
    vote: SkipVote | None
    viewer: Viewer


class QueueState(Schema):
    tracks: list[Track]
    total: int
    autoplay: list[Track]


class PlaylistInfo(Schema):
    name: str
    track_count: int


class SearchResults(Schema):
    playlist: PlaylistInfo | None
    tracks: list[Track]


class Problem(Schema):
    detail: str


class Notes(Schema):
    """Things the bot couldn't finish, like a channel it wasn't allowed to delete."""

    notes: list[str]


AutoroleIds = Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_AUTOROLES)]


class AutoroleUser(Schema):
    user: Person
    member: bool
    role_ids: list[Snowflake]


class AutoroleUserPatch(Schema):
    user_id: Snowflake
    role_ids: Annotated[list[Snowflake], msgspec.Meta(min_length=1, max_length=MAX_AUTOROLES)]


class InviteEntry(Schema):
    rank: int
    user: Person
    regular: int
    left: int
    fake: int
    bonus: int
    total: int


class InviteBoard(Schema):
    entries: list[InviteEntry]
    page: int
    pages: int
    people: int


class Invitee(Schema):
    user: Person
    joined_at: int  # Unix ms
    left: bool
    fake: bool


class InviteProfile(Schema):
    rank: int | None
    user: Person
    member: bool
    regular: int
    left: int
    fake: int
    bonus: int
    total: int
    invited_by: Person | None
    invitees: list[Invitee]


class WarnEntry(Schema):
    rank: int
    user: Person
    warnings: int
    last_at: int  # Unix ms


class WarnBoard(Schema):
    entries: list[WarnEntry]
    page: int
    pages: int
    people: int
    warnings: int


class WarningItem(Schema):
    id: int
    number: int
    reason: str
    moderator: Person | None  # None when AutoMod gave it
    created_at: int  # Unix ms


class WarnProfile(Schema):
    user: Person
    member: bool
    rank: int | None
    total: int
    warnings: list[WarningItem]
    page: int
    pages: int


class WarnCreate(Schema):
    user_id: Snowflake
    reason: Annotated[str, msgspec.Meta(max_length=MAX_REASON)] = ""


class WarnResult(Schema):
    total: int
    punishment: str | None
    punished: bool
    messaged: bool


class WarningsCleared(Schema):
    cleared: int


class BonusChange(Schema):
    user_ids: Annotated[list[Snowflake], msgspec.Meta(min_length=1, max_length=MAX_BONUS_USERS)]
    amount: Annotated[int, msgspec.Meta(ge=-MAX_BONUS, le=MAX_BONUS)]
    mode: Literal["add", "set"]


class Bonus(Schema):
    user_id: Snowflake
    bonus: int


TicketStatus = Literal["open", "closed", "deleted"]


class TicketEntry(Schema):
    number: int
    label: str
    status: TicketStatus
    channel_id: Snowflake | None
    channel_name: str | None
    opener: Person
    claimed_by: Person | None
    reason: str
    created_at: int  # Unix ms
    closed_at: int | None
    messages: int | None


class TicketPage(Schema):
    entries: list[TicketEntry]
    page: int
    pages: int
    total: int
    open: int
    closed: int
    deleted: int


class TicketDetail(TicketEntry):
    closed_by: Person | None
    people: list[Person]


class TicketTranscript(Schema):
    ticket: TicketDetail
    live: bool  # the channel still exists, so links to its files still work
    transcript: Transcript | None


class Purged(Schema):
    removed: int


class AutoroleSettings(Schema):
    role_ids: list[Snowflake]
    bot_role_ids: list[Snowflake]
    split_bots: bool
    users: list[AutoroleUser]
    delay: int
    wait_for_screening: bool
    sticky: bool
    sticky_ignore_ids: list[Snowflake]
    kept: int  # People who left with roles the bot is keeping for them


class AutorolePatch(Schema):
    role_ids: AutoroleIds | UnsetType = UNSET
    bot_role_ids: AutoroleIds | UnsetType = UNSET
    split_bots: bool | UnsetType = UNSET
    users: Annotated[list[AutoroleUserPatch], msgspec.Meta(max_length=MAX_AUTOROLE_USERS)] | UnsetType = UNSET
    delay: Annotated[int, msgspec.Meta(ge=0, le=MAX_AUTOROLE_DELAY)] | UnsetType = UNSET
    wait_for_screening: bool | UnsetType = UNSET
    sticky: bool | UnsetType = UNSET
    sticky_ignore_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_STICKY_IGNORE)] | UnsetType = UNSET


class LogChannels(Schema):
    moderation: Snowflake | None = None
    automod: Snowflake | None = None
    members: Snowflake | None = None
    messages: Snowflake | None = None
    voice: Snowflake | None = None
    server: Snowflake | None = None
    tickets: Snowflake | None = None


class LogChannelsPatch(Schema):
    """Logs to change. `null` turns one off."""

    moderation: Snowflake | None | UnsetType = UNSET
    automod: Snowflake | None | UnsetType = UNSET
    members: Snowflake | None | UnsetType = UNSET
    messages: Snowflake | None | UnsetType = UNSET
    voice: Snowflake | None | UnsetType = UNSET
    server: Snowflake | None | UnsetType = UNSET
    tickets: Snowflake | None | UnsetType = UNSET


# A new `Log` needs a field in both structs above, so the bot refuses to start until it has one
for _struct in (LogChannels, LogChannelsPatch):
    if set(_struct.__struct_fields__) != set(Log):
        raise RuntimeError(f"{_struct.__name__} must have exactly one field per Log")

MAX_LOG_IGNORED_CHANNELS = 50
MAX_LOG_IGNORED_ROLES = 25


class LogSettings(Schema):
    channels: LogChannels
    disabled_events: list[Event]
    ignored_channel_ids: list[Snowflake]  # A category covers its channels
    ignored_role_ids: list[Snowflake]
    skip_bots: bool


class LogPatch(Schema):
    channels: LogChannelsPatch | UnsetType = UNSET
    disabled_events: Annotated[list[Event], msgspec.Meta(max_length=len(get_args(Event)))] | UnsetType = UNSET
    ignored_channel_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_LOG_IGNORED_CHANNELS)] | UnsetType = (
        UNSET
    )
    ignored_role_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_LOG_IGNORED_ROLES)] | UnsetType = UNSET
    skip_bots: bool | UnsetType = UNSET


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


NICK_MAX = 32
BIO_MAX = 190
IMAGE_MAX_BYTES = 8 * 1024 * 1024
IMAGE_DATA_MAX = len("data:image/jpeg;base64,") + -(-IMAGE_MAX_BYTES // 3) * 4
ImageData = Annotated[
    str,
    msgspec.Meta(
        max_length=IMAGE_DATA_MAX,
        pattern=r"^data:image/(png|jpeg|gif);base64,",
        description="A PNG, JPEG or GIF as a base64 data URI",
    ),
]


class BotProfile(Schema):
    name: str
    nick: str | None
    bio: str | None
    avatar_url: str | None
    banner_url: str | None
    global_bio: str | None
    global_avatar_url: str
    global_banner_url: str | None
    banner_color: str | None


class BotProfilePatch(Schema):
    nick: Annotated[str, msgspec.Meta(min_length=1, max_length=NICK_MAX)] | None | UnsetType = UNSET
    bio: Annotated[str, msgspec.Meta(min_length=1, max_length=BIO_MAX)] | None | UnsetType = UNSET
    avatar: ImageData | None | UnsetType = UNSET
    banner: ImageData | None | UnsetType = UNSET


MESSAGE_COMPONENTS_MAX = 40
MESSAGE_TEXT_MAX = 4000
MESSAGE_MEDIA_MAX = 40
MESSAGE_FILES_MAX = 10
MESSAGE_FILES_MAX_BYTES = 16 * 1024 * 1024
MESSAGE_FILE_DATA_MAX = 128 + -(-MESSAGE_FILES_MAX_BYTES // 3) * 4
WEBHOOK_NAME_MAX = 80
BUTTON_LABEL_MAX = 80
MEDIA_DESCRIPTION_MAX = 1024
SECTION_TEXTS_MAX = 3
ROW_BUTTONS_MAX = 5
GALLERY_ITEMS_MAX = 10

HexColor = Annotated[str, msgspec.Meta(pattern=r"^#[0-9a-fA-F]{6}$")]
HttpsUrl = Annotated[str, msgspec.Meta(pattern=r"^https://\S+$", max_length=2048)]
FileName = Annotated[str, msgspec.Meta(pattern=r"^[\w.-]{1,100}$", description="An uploaded file's name")]
MediaUrl = Annotated[
    str,
    msgspec.Meta(
        pattern=r"^(https://\S+|attachment://[\w.-]{1,100})$",
        max_length=2048,
        description="An https URL, or attachment://<name> for an uploaded file",
    ),
]
MessageText = Annotated[str, msgspec.Meta(min_length=1, max_length=MESSAGE_TEXT_MAX)]


class MessageMedia(Schema):
    url: MediaUrl
    description: Annotated[str, msgspec.Meta(max_length=MEDIA_DESCRIPTION_MAX)] | None = None
    spoiler: bool = False


class MessageButton(Schema, tag="button", tag_field="kind"):
    url: Annotated[str, msgspec.Meta(pattern=r"^(https?|discord)://\S+$", max_length=512)]
    label: Annotated[str, msgspec.Meta(min_length=1, max_length=BUTTON_LABEL_MAX)] | None = None
    emoji: Annotated[str, msgspec.Meta(min_length=1, max_length=100)] | None = None
    disabled: bool = False


class MessageThumbnail(Schema, tag="thumbnail", tag_field="kind"):
    media: MessageMedia


class MessageTextDisplay(Schema, tag="text", tag_field="kind"):
    text: MessageText


class MessageSection(Schema, tag="section", tag_field="kind"):
    texts: Annotated[list[MessageText], msgspec.Meta(min_length=1, max_length=SECTION_TEXTS_MAX)]
    accessory: MessageThumbnail | MessageButton


class MessageGallery(Schema, tag="gallery", tag_field="kind"):
    items: Annotated[list[MessageMedia], msgspec.Meta(min_length=1, max_length=GALLERY_ITEMS_MAX)]


class MessageFile(Schema, tag="file", tag_field="kind"):
    url: Annotated[str, msgspec.Meta(pattern=r"^attachment://[\w.-]{1,100}$")]
    spoiler: bool = False


class MessageSeparator(Schema, tag="separator", tag_field="kind"):
    divider: bool = True
    large: bool = False


class MessageRow(Schema, tag="row", tag_field="kind"):
    buttons: Annotated[list[MessageButton], msgspec.Meta(min_length=1, max_length=ROW_BUTTONS_MAX)]


MessagePiece = MessageTextDisplay | MessageSection | MessageGallery | MessageFile | MessageSeparator | MessageRow


class MessageContainer(Schema, tag="container", tag_field="kind"):
    children: Annotated[list[MessagePiece], msgspec.Meta(min_length=1, max_length=MESSAGE_COMPONENTS_MAX)]
    color: HexColor | None = None
    spoiler: bool = False


class MessageUpload(Schema):
    name: FileName
    data: Annotated[
        str,
        msgspec.Meta(
            max_length=MESSAGE_FILE_DATA_MAX,
            pattern=r"^data:[\w.+-]+/[\w.+-]+;base64,",
            description="The file as a base64 data URI",
        ),
    ]


class MessageSend(Schema):
    channel_id: Snowflake
    components: Annotated[
        list[MessageContainer | MessagePiece], msgspec.Meta(min_length=1, max_length=MESSAGE_COMPONENTS_MAX)
    ]
    username: Annotated[str, msgspec.Meta(min_length=1, max_length=WEBHOOK_NAME_MAX)] | None = None
    avatar_url: HttpsUrl | None = None
    files: Annotated[list[MessageUpload], msgspec.Meta(max_length=MESSAGE_FILES_MAX)] = []


class MessageSender(Schema):
    name: str
    avatar_url: str
    upload_limit: int


class MessageSent(Schema):
    channel_id: Snowflake
    message_id: Snowflake
    url: str


GiveawayStatus = Literal["scheduled", "running", "ended"]
EntryButtonStyle = Literal["blurple", "green", "grey", "red"]
MAX_GIVEAWAY_WINNERS = 50
MAX_GIVEAWAY_ROLES = 10
MAX_GIVEAWAY_ENTRIES = 100
MAX_GIVEAWAY_DAYS = 3650
MAX_GIVEAWAY_INVITES = 10_000
MAX_ENTRANT_CHANGES = 100
Prize = Annotated[str, msgspec.Meta(min_length=1, max_length=256)]
GiveawayText = Annotated[str, msgspec.Meta(max_length=2000)]
WinnerCount = Annotated[int, msgspec.Meta(ge=1, le=MAX_GIVEAWAY_WINNERS)]
Days = Annotated[int, msgspec.Meta(ge=0, le=MAX_GIVEAWAY_DAYS)]
InviteCount = Annotated[int, msgspec.Meta(ge=0, le=MAX_GIVEAWAY_INVITES)]
GiveawayRoles = Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_GIVEAWAY_ROLES)]
ButtonLabel = Annotated[str, msgspec.Meta(max_length=40)]
EmojiText = Annotated[str, msgspec.Meta(min_length=1, max_length=100)]
UnixMs = Annotated[int, msgspec.Meta(ge=0, description="Unix ms")]
GIVEAWAY_IMAGE_MAX_BYTES = 8 * 1024 * 1024
GIVEAWAY_IMAGE_DATA_MAX = len("data:image/jpeg;base64,") + -(-GIVEAWAY_IMAGE_MAX_BYTES // 3) * 4
GiveawayImage = Annotated[
    str,
    msgspec.Meta(
        max_length=GIVEAWAY_IMAGE_DATA_MAX,
        pattern=r"^data:image/(png|jpeg|gif|webp);base64,",
        description="A PNG, JPEG, GIF or WebP as a base64 data URI",
    ),
]


class BonusRole(Schema):
    role_id: Snowflake
    entries: Annotated[int, msgspec.Meta(ge=1, le=MAX_GIVEAWAY_ENTRIES)]


BonusRoles = Annotated[list[BonusRole], msgspec.Meta(max_length=MAX_GIVEAWAY_ROLES)]


class GiveawayCreate(Schema, kw_only=True):
    channel_id: Snowflake
    prize: Prize
    description: GiveawayText = ""
    winner_count: WinnerCount = 1
    starts_at: UnixMs | None = None  # None starts it now
    ends_at: UnixMs
    host_id: Snowflake | None = None  # None is whoever creates it
    required_role_ids: GiveawayRoles = []
    require_all_roles: bool = False
    blocked_role_ids: GiveawayRoles = []
    min_account_days: Days = 0
    min_member_days: Days = 0
    min_invites: InviteCount = 0
    bonus_roles: BonusRoles = []
    ping_role_id: Snowflake | None = None
    winner_role_id: Snowflake | None = None
    color: HexColor | None = None
    image_url: HttpsUrl | None = None
    image_data: GiveawayImage | None = None
    button_label: ButtonLabel = "Enter"
    button_emoji: EmojiText | None = None
    button_style: EntryButtonStyle = "blurple"


class GiveawayPatch(Schema):
    channel_id: Snowflake | UnsetType = UNSET
    prize: Prize | UnsetType = UNSET
    description: GiveawayText | UnsetType = UNSET
    winner_count: WinnerCount | UnsetType = UNSET
    starts_at: UnixMs | UnsetType = UNSET
    ends_at: UnixMs | UnsetType = UNSET
    host_id: Snowflake | UnsetType = UNSET
    required_role_ids: GiveawayRoles | UnsetType = UNSET
    require_all_roles: bool | UnsetType = UNSET
    blocked_role_ids: GiveawayRoles | UnsetType = UNSET
    min_account_days: Days | UnsetType = UNSET
    min_member_days: Days | UnsetType = UNSET
    min_invites: InviteCount | UnsetType = UNSET
    bonus_roles: BonusRoles | UnsetType = UNSET
    ping_role_id: Snowflake | None | UnsetType = UNSET
    winner_role_id: Snowflake | None | UnsetType = UNSET
    color: HexColor | None | UnsetType = UNSET
    image_url: HttpsUrl | None | UnsetType = UNSET
    image_data: GiveawayImage | UnsetType = UNSET
    button_label: ButtonLabel | UnsetType = UNSET
    button_emoji: EmojiText | None | UnsetType = UNSET
    button_style: EntryButtonStyle | UnsetType = UNSET


class GiveawaySummary(Schema):
    id: int
    status: GiveawayStatus
    prize: str
    channel_id: Snowflake
    entries: int
    winner_count: int
    starts_at: int  # Unix ms
    ends_at: int  # Unix ms
    ended_at: int | None  # Unix ms
    posted: bool


class GiveawayPage(Schema):
    items: list[GiveawaySummary]
    page: int
    pages: int
    total: int
    scheduled: int
    running: int
    ended: int


class Giveaway(GiveawaySummary):
    description: str
    message_url: str | None
    host: Person
    winners: list[Person]
    required_role_ids: list[Snowflake]
    require_all_roles: bool
    blocked_role_ids: list[Snowflake]
    min_account_days: int
    min_member_days: int
    min_invites: int
    bonus_roles: list[BonusRole]
    ping_role_id: Snowflake | None
    winner_role_id: Snowflake | None
    color: str | None
    image_url: str | None
    image_file: str | None
    image_src: str | None  # Uploaded image on Discord, once posted
    button_label: str
    button_emoji: str | None
    button_style: EntryButtonStyle
    created_at: int  # Unix ms


class Entrant(Schema):
    user: Person
    member: bool
    eligible: bool
    entries: int
    bonus: int
    role_bonus: int
    chance: float  # 0..1 of all eligible entries
    entered_at: int  # Unix ms
    winner: bool


class EntrantPage(Schema):
    items: list[Entrant]
    page: int
    pages: int
    total: int
    people: int
    eligible: int
    tickets: int


EntrantIds = Annotated[list[Snowflake], msgspec.Meta(min_length=1, max_length=MAX_ENTRANT_CHANGES)]


class EntrantBonus(Schema):
    user_ids: EntrantIds
    bonus: Annotated[int, msgspec.Meta(ge=0, le=MAX_GIVEAWAY_ENTRIES)]


class EntrantRemove(Schema):
    user_ids: EntrantIds


class Reroll(Schema):
    user_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_GIVEAWAY_WINNERS)] | None = (
        None  # None rerolls all
    )


MAX_STARBOARDS = 5
MAX_STARBOARD_EMOJIS = 5
MAX_STARBOARD_CHANNELS = 50
MAX_STARBOARD_ROLES = 25
MAX_STARBOARD_VOTES = 1000
MAX_STARBOARD_AGE_DAYS = 365

StarboardEmojis = Annotated[list[EmojiText], msgspec.Meta(max_length=MAX_STARBOARD_EMOJIS)]
StarboardChannels = Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_STARBOARD_CHANNELS)]
StarboardRoles = Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_STARBOARD_ROLES)]
Votes = Annotated[int, msgspec.Meta(ge=1, le=MAX_STARBOARD_VOTES)]
AgeDays = Annotated[int, msgspec.Meta(ge=1, le=MAX_STARBOARD_AGE_DAYS)]
ChannelMode = Literal["all", "only", "except"]


class Starboard(Schema):
    id: int
    channel_id: Snowflake
    enabled: bool
    emojis: list[str]
    downvote_emojis: list[str]
    threshold: int
    drop_below: int | None  # None keeps posts on the board whatever happens to their votes
    self_vote: bool
    allow_bots: bool
    channel_mode: ChannelMode
    channel_ids: list[Snowflake]
    blocked_role_ids: list[Snowflake]
    max_age_days: int | None
    follow_deletes: bool
    color: str | None
    posts: int


class StarboardCreate(Schema):
    channel_id: Snowflake
    emojis: StarboardEmojis = msgspec.field(default_factory=lambda: ["⭐"])
    threshold: Votes = 3


class StarboardPatch(Schema):
    channel_id: Snowflake | UnsetType = UNSET
    enabled: bool | UnsetType = UNSET
    emojis: StarboardEmojis | UnsetType = UNSET
    downvote_emojis: StarboardEmojis | UnsetType = UNSET
    threshold: Votes | UnsetType = UNSET
    drop_below: Votes | None | UnsetType = UNSET
    self_vote: bool | UnsetType = UNSET
    allow_bots: bool | UnsetType = UNSET
    channel_mode: ChannelMode | UnsetType = UNSET
    channel_ids: StarboardChannels | UnsetType = UNSET
    blocked_role_ids: StarboardRoles | UnsetType = UNSET
    max_age_days: AgeDays | None | UnsetType = UNSET
    follow_deletes: bool | UnsetType = UNSET
    color: HexColor | None | UnsetType = UNSET


MAX_PUNISHMENTS = 10
MAX_WARNINGS = 100
MAX_RULE_ROLES = 25
MAX_RULE_CHANNELS = 50
MAX_MEDIA_CHANNELS = 10
MAX_TIMEOUT_SECONDS = 28 * 24 * 3600
MAX_NATIVE_KEYWORDS = 1000
MAX_NATIVE_PATTERNS = 10
MAX_NATIVE_ALLOW = 1000
MAX_NATIVE_MENTIONS = 50
MAX_NATIVE_ROLES = 20
MAX_NATIVE_CHANNELS = 50
NATIVE_LIMITS = {"keyword": 6, "spam": 1, "preset": 1, "mention_spam": 1, "member_profile": 1}

RuleKind = Literal[
    "media",
    "invites",
    "masked_links",
    "new_members",
    "flood",
    "duplicates",
    "mention_flood",
    "file_flood",
    "ghost_pings",
    "caps",
    "emojis",
    "zalgo",
    "fonts",
    "repeated_chars",
    "lines",
    "invisible",
]
PunishAction = Literal["timeout", "kick", "ban"]
TimeoutSeconds = Annotated[int, msgspec.Meta(ge=60, le=MAX_TIMEOUT_SECONDS)]
NativeTrigger = Literal["keyword", "spam", "preset", "mention_spam", "member_profile"]
NativePreset = Literal["profanity", "sexual_content", "slurs"]
NativeName = Annotated[str, msgspec.Meta(min_length=1, max_length=100)]
NativeKeyword = Annotated[str, msgspec.Meta(min_length=1, max_length=60)]
NativePattern = Annotated[str, msgspec.Meta(min_length=1, max_length=260)]


class SquareRule(Schema):
    kind: RuleKind
    enabled: bool
    amount: int | None  # The rule's limit: messages, repeats, percent, minutes and so on, depending on the kind
    seconds: int | None
    channel_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_MEDIA_CHANNELS)]  # Media-only channels
    delete: bool
    warn: bool
    notify: bool
    exempt_role_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_RULE_ROLES)]
    exempt_channel_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_RULE_CHANNELS)]


class Punishment(Schema):
    warnings: Annotated[int, msgspec.Meta(ge=1, le=MAX_WARNINGS)]
    action: PunishAction
    seconds: TimeoutSeconds | None = None


class AutomodSettings(Schema):
    rules: list[SquareRule]
    punishments: list[Punishment]


class AutomodPatch(Schema):
    rules: Annotated[list[SquareRule], msgspec.Meta(max_length=len(get_args(RuleKind)))] | UnsetType = UNSET
    punishments: Annotated[list[Punishment], msgspec.Meta(max_length=MAX_PUNISHMENTS)] | UnsetType = UNSET


class NativeRule(Schema):
    id: Snowflake
    name: str
    trigger: NativeTrigger
    enabled: bool
    by_square: bool
    keywords: list[str]
    patterns: list[str]
    allow_list: list[str]
    presets: list[NativePreset]
    mention_limit: int | None
    raid_protection: bool
    block: bool
    block_message: str | None
    alert_channel_id: Snowflake | None
    timeout_seconds: int | None
    block_interaction: bool
    exempt_role_ids: list[Snowflake]
    exempt_channel_ids: list[Snowflake]


class NativeRuleCreate(Schema):
    trigger: NativeTrigger
    name: NativeName


class NativeRulePatch(Schema):
    name: NativeName | UnsetType = UNSET
    enabled: bool | UnsetType = UNSET
    keywords: Annotated[list[NativeKeyword], msgspec.Meta(max_length=MAX_NATIVE_KEYWORDS)] | UnsetType = UNSET
    patterns: Annotated[list[NativePattern], msgspec.Meta(max_length=MAX_NATIVE_PATTERNS)] | UnsetType = UNSET
    allow_list: Annotated[list[NativeKeyword], msgspec.Meta(max_length=MAX_NATIVE_ALLOW)] | UnsetType = UNSET
    presets: Annotated[list[NativePreset], msgspec.Meta(max_length=3)] | UnsetType = UNSET
    mention_limit: Annotated[int, msgspec.Meta(ge=1, le=MAX_NATIVE_MENTIONS)] | UnsetType = UNSET
    raid_protection: bool | UnsetType = UNSET
    block: bool | UnsetType = UNSET
    block_message: Annotated[str, msgspec.Meta(max_length=150)] | None | UnsetType = UNSET
    alert_channel_id: Snowflake | None | UnsetType = UNSET
    timeout_seconds: TimeoutSeconds | None | UnsetType = UNSET
    block_interaction: bool | UnsetType = UNSET
    exempt_role_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_NATIVE_ROLES)] | UnsetType = UNSET
    exempt_channel_ids: Annotated[list[Snowflake], msgspec.Meta(max_length=MAX_NATIVE_CHANNELS)] | UnsetType = UNSET


class AutomodTest(Schema):
    content: Annotated[str, msgspec.Meta(min_length=1, max_length=4000)]
    channel_id: Snowflake | None = None


class AutomodHit(Schema):
    source: Literal["discord", "square"]
    rule: str
    detail: str


class AutomodTestResult(Schema):
    hits: list[AutomodHit]
    skipped: list[str]  # Rules a typed message can't show, like flood or Discord's own word lists


class ModuleSettings(Schema):
    logs: bool
    tickets: bool
    invites: bool
    giveaways: bool
    starboard: bool
    autorole: bool


class ModulePatch(Schema):
    logs: bool | UnsetType = UNSET
    tickets: bool | UnsetType = UNSET
    invites: bool | UnsetType = UNSET
    giveaways: bool | UnsetType = UNSET
    starboard: bool | UnsetType = UNSET
    autorole: bool | UnsetType = UNSET


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
        can_moderate=member.guild_permissions.moderate_members,
    )


def _listed_channels(guild: discord.Guild) -> list[tuple[discord.abc.GuildChannel, str]]:
    return [(channel, kind) for channel in guild.channels if (kind := str(channel.type)) in _CHANNEL_KINDS]


def channels_out(guild: discord.Guild) -> list[Channel]:
    return [
        Channel(
            id=str(channel.id),
            name=channel.name,
            type=kind,
            parent_id=id_of(channel.category),
            position=channel.position,
        )
        for channel, kind in sorted(_listed_channels(guild), key=lambda listed: listed[0].position)
    ]


def bot_permissions_out(guild: discord.Guild) -> BotPermissions:
    me = guild.me
    return BotPermissions(
        guild=str(me.guild_permissions.value),
        channels={str(channel.id): str(channel.permissions_for(me).value) for channel, _ in _listed_channels(guild)},
        top_role=me.top_role.position,
        features=list(guild.features),
    )


def _option_out(option: discord.Option) -> CommandOption:
    return CommandOption(
        name=option.name,
        type=option.input_type.name,
        description=option.description,
        required=option.required,
        choices=[choice.name for choice in option.choices],
        channel_types=[kind for kind in map(str, option.channel_types) if kind in _CHANNEL_KINDS],
        min=option.min_value,
        max=option.max_value,
        autocomplete=bool(option.autocomplete),
    )


def _permissions(command: ApplicationCommand) -> str | None:
    while command.parent:
        command = command.parent
    bits = command.default_member_permissions
    return str(bits.value) if bits else None


def _install(command: ApplicationCommand) -> Literal["server", "both", "account"]:
    if check.bot_in_server in command.checks:
        return "server"
    while command.parent:
        command = command.parent
    types = command.integration_types or {discord.IntegrationType.guild_install}
    if discord.IntegrationType.user_install not in types:
        return "server"
    return "both" if discord.IntegrationType.guild_install in types else "account"


def _commands(cog: Cog) -> list[BotCommand]:
    found: list[BotCommand] = []
    for command in cog.get_commands():
        # Prefix commands and commands synced to set guilds are the owner's own tools
        if not isinstance(command, ApplicationCommand) or command.guild_ids:
            continue
        if isinstance(command, MessageCommand | UserCommand):
            found.append(
                BotCommand(
                    name=command.name,
                    kind="message" if isinstance(command, MessageCommand) else "user",
                    description=(inspect.getdoc(command.callback) or "").partition("\n")[0],
                    options=[],
                    permissions=_permissions(command),
                    install=_install(command),
                )
            )
            continue
        subs = command.walk_commands() if isinstance(command, SlashCommandGroup) else [command]
        found += [
            BotCommand(
                name=sub.qualified_name,
                kind="slash",
                description=sub.description,
                options=[_option_out(option) for option in sub.options],
                permissions=_permissions(sub),
                install=_install(sub),
            )
            for sub in subs
            if isinstance(sub, SlashCommand)
        ]
    return found


def commands_out(client: Client) -> list[CommandCategory]:
    cogs = sorted((cog for cog in client.cogs.values() if isinstance(cog, Cog)), key=lambda cog: cog.category_order)
    return [
        CommandCategory(name=cog.qualified_name, description=cog.description, module=cog.__cog_module__, commands=found)
        for cog in cogs
        if (found := _commands(cog))
    ]


def mentioned_channel_out(channel: discord.abc.GuildChannel) -> MentionedChannel | None:
    if (kind := str(channel.type)) not in _CHANNEL_KINDS:
        return None
    icon = channel.guild.icon
    return MentionedChannel(
        id=str(channel.id),
        name=channel.name,
        type=kind,
        guild_id=str(channel.guild.id),
        guild_name=channel.guild.name,
        guild_icon_url=icon.replace(size=64, static_format="webp").url if icon else None,
    )


def emojis_out(guild: discord.Guild) -> list[Emoji]:
    return [
        Emoji(id=str(emoji.id), name=emoji.name, animated=emoji.animated, usable=emoji.is_usable())
        for emoji in guild.emojis
    ]


def roles_out(guild: discord.Guild) -> list[Role]:
    return [
        Role(
            id=str(role.id),
            name=role.name,
            color=str(role.color) if role.color.value else None,
            position=role.position,
            managed=role.managed,
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


def person_of(user_id: int, user: discord.User | discord.Member | None) -> Person:
    if user:
        return _person_out(user)
    return Person(
        id=str(user_id),
        name=str(user_id),
        avatar_url=f"https://cdn.discordapp.com/embed/avatars/{(user_id >> 22) % 6}.png",
    )


def user_match(user: discord.User | discord.Member, member: bool) -> UserMatch:
    return UserMatch(
        id=str(user.id),
        name=user.display_name,
        username=user.name,
        avatar_url=user.display_avatar.replace(size=64, static_format="webp").url,
        bot=user.bot,
        member=member,
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
    # Local: `music/play.py` pulls in the player modules, which import this one
    from square.music.play import voice_error

    voice = member.voice
    in_channel = player is not None and voice is not None and voice.channel == player.channel
    refused = voice_error(member)
    return Viewer(
        dj=dj.is_dj(member, player),
        in_channel=in_channel,
        deafened=in_channel and (voice.deaf or voice.self_deaf),
        queue_lock=resolve.plain(member.guild, refused) if refused else None,
    )


_NOBODY = Viewer(dj=False, in_channel=False, deafened=False)


def player_shared(client: Client, guild: discord.Guild) -> PlayerState:
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
            viewer=_NOBODY,
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
        viewer=_NOBODY,
    )


def player_for(client: Client, guild: discord.Guild, member: discord.Member, shared: PlayerState) -> PlayerState:
    return msgspec.structs.replace(shared, viewer=_viewer(live_player(client, guild.id), member))


def player_out(client: Client, guild: discord.Guild, member: discord.Member) -> PlayerState:
    return player_for(client, guild, member, player_shared(client, guild))


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
    if isinstance(data, Playlist):
        return SearchResults(
            playlist=PlaylistInfo(name=data.name, track_count=len(data)),
            tracks=[_track(None, track) for track in data.tracks[:PLAYLIST_LIMIT]],
        )
    found = data if isinstance(data, list) else [data] if data else []
    return SearchResults(playlist=None, tracks=[_track(None, track) for track in found[:limit]])
