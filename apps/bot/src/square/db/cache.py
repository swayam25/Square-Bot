from dataclasses import dataclass, field, fields
from square.db.schema import DJRoleTable, GuildTable, LogChannelTable
from square.modules import DEFAULT_MODULES, Module


@dataclass
class GuildSettings:
    modules: list[str] = field(default_factory=lambda: list(DEFAULT_MODULES))
    media_only_channel_id: int | None = None
    autorole: int | None = None
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


# Every guild's settings, loaded once at startup and kept in sync by the `db.funcs` setters, so events never wait on
# the database. Guilds without a row read the shared default.
_settings: dict[int, GuildSettings] = {}
_DEFAULT = GuildSettings()
_GUILD_COLUMNS = tuple(f.name for f in fields(GuildSettings) if f.name not in ("dj_roles", "log_channels"))


async def load() -> None:
    """Loads every guild's settings, log channels and DJ roles with one query each."""
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


def get(guild_id: int) -> GuildSettings:
    """
    A guild's settings. Read-only: change them through the `db.funcs` setters so the database stays in sync.

    Args:
        guild_id (int): The guild ID to read.
    """
    return _settings.get(guild_id, _DEFAULT)


def entry(guild_id: int) -> GuildSettings:
    """A guild's mutable settings entry, created if missing. Only for the `db.funcs` setters."""
    if (settings := _settings.get(guild_id)) is None:
        settings = _settings[guild_id] = GuildSettings()
    return settings


def drop(guild_id: int) -> None:
    """Forgets a guild whose row was deleted."""
    _settings.pop(guild_id, None)


def enabled(guild_id: int, module: Module) -> bool:
    """Whether a guild has the module turned on."""
    return module in get(guild_id).modules


def guild_ids_with_module(module: Module) -> set[int]:
    """IDs of every guild with the module turned on. Guilds without a row are left out, even for default modules."""
    return {guild_id for guild_id, settings in _settings.items() if module in settings.modules}


def log_channel(guild_id: int, log_type: str) -> int | None:
    """The channel a log type posts to, or None when it has none or logs are turned off."""
    return get(guild_id).log_channels.get(log_type) if enabled(guild_id, Module.LOGS) else None


def guild_ids_with_ticket_panel() -> set[int]:
    """IDs of every guild with an "Open a ticket" panel posted."""
    return {guild_id for guild_id, settings in _settings.items() if settings.ticket_panel_channel_id}


def guild_ids_with_log(log_type: str) -> set[int]:
    """IDs of every guild with logs on and a channel set for the log type."""
    return {
        guild_id
        for guild_id, settings in _settings.items()
        if log_type in settings.log_channels and Module.LOGS in settings.modules
    }
