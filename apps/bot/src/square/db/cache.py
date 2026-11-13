from dataclasses import dataclass, field, fields
from square.db.schema import AutoroleUserTable, DJRoleTable, GuildTable, LogChannelTable
from square.modules import DEFAULT_MODULES, Module


@dataclass
class GuildSettings:
    modules: list[str] = field(default_factory=lambda: list(DEFAULT_MODULES))
    media_only_channel_id: int | None = None
    autorole_ids: list[int] = field(default_factory=list)
    autorole_bot_ids: list[int] = field(default_factory=list)
    autorole_split: bool = False
    dj_mode: bool = False
    music_channel_id: int | None = None
    music_message_id: int | None = None
    music_stay_channel_id: int | None = None
    invite_fake_days: int = 7
    ticket_category_id: int | None = None
    ticket_support_role_ids: list[int] = field(default_factory=list)
    ticket_panel_channel_id: int | None = None
    ticket_panel_message_id: int | None = None
    ticket_max_open: int = 1
    ticket_confirm_close: bool = True
    dj_roles: list[int] = field(default_factory=list)
    log_channels: dict[str, int] = field(default_factory=dict)
    autorole_users: dict[int, list[int]] = field(default_factory=dict)


_settings: dict[int, GuildSettings] = {}
_DEFAULT = GuildSettings()
_GUILD_COLUMNS = tuple(
    f.name for f in fields(GuildSettings) if f.name not in ("dj_roles", "log_channels", "autorole_users")
)


async def load() -> None:
    _settings.clear()
    for row in await GuildTable.all().values("guild_id", *_GUILD_COLUMNS):
        guild_id = row.pop("guild_id")
        _settings[guild_id] = GuildSettings(**row)
    for guild_id, log_type, channel_id in await LogChannelTable.all().values_list(
        "guild__guild_id", "log_type", "channel_id"
    ):
        entry(guild_id).log_channels[log_type] = channel_id
    for guild_id, role_id in await DJRoleTable.all().values_list("guild__guild_id", "role_id"):
        entry(guild_id).dj_roles.append(role_id)
    for guild_id, user_id, role_ids in await AutoroleUserTable.all().values_list(
        "guild__guild_id", "user_id", "role_ids"
    ):
        entry(guild_id).autorole_users[user_id] = role_ids


def get(guild_id: int) -> GuildSettings:
    """
    A guild's settings. Read-only: change them through the `db.funcs` setters so the database stays in sync.

    Args:
        guild_id (int): The guild ID to read.
    """
    return _settings.get(guild_id, _DEFAULT)


def entry(guild_id: int) -> GuildSettings:
    if (settings := _settings.get(guild_id)) is None:
        settings = _settings[guild_id] = GuildSettings()
    return settings


def drop(guild_id: int) -> None:
    _settings.pop(guild_id, None)


def enabled(guild_id: int, module: Module) -> bool:
    return module in get(guild_id).modules


def guild_ids_with_module(module: Module) -> set[int]:
    return {guild_id for guild_id, settings in _settings.items() if module in settings.modules}


def log_channel(guild_id: int, log_type: str) -> int | None:
    return get(guild_id).log_channels.get(log_type) if enabled(guild_id, Module.LOGS) else None


def guild_ids_with_ticket_panel() -> set[int]:
    return {guild_id for guild_id, settings in _settings.items() if settings.ticket_panel_channel_id}


def guild_ids_with_log(log_type: str) -> set[int]:
    return {
        guild_id
        for guild_id, settings in _settings.items()
        if log_type in settings.log_channels and Module.LOGS in settings.modules
    }
