import msgspec
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, NotRequired, TypedDict
from urllib.parse import urlparse, urlunparse

CONFIG_FILE_PATH = Path("config.toml")


class LavalinkConfig(TypedDict):
    host: str
    port: int
    password: str
    secure: bool
    regions: NotRequired[list[str]]


class _Colors(msgspec.Struct, forbid_unknown_fields=True):
    theme: str
    green: str
    red: str
    orange: str


class ApiConfig(msgspec.Struct, rename="kebab", forbid_unknown_fields=True, frozen=True):
    secret: Annotated[str, msgspec.Meta(min_length=32)]
    host: str = "127.0.0.1"
    port: Annotated[int, msgspec.Meta(ge=1, le=65535)] = 8080
    docs: bool = False


class _Config(msgspec.Struct, rename="kebab", forbid_unknown_fields=True):
    owner_id: int
    owner_guild_ids: list[int]
    system_channel_id: int
    support_server_url: str
    dashboard_url: str
    bot_token: str
    database_url: str
    colors: _Colors
    lavalink: list[LavalinkConfig] | LavalinkConfig
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: bool = False
    api: ApiConfig | None = None


def _load() -> _Config:
    try:
        with open(CONFIG_FILE_PATH, "rb") as file:
            return msgspec.toml.decode(file.read(), type=_Config)
    except FileNotFoundError:
        raise SystemExit(
            f"{CONFIG_FILE_PATH} not found. Copy config.example.toml to config.toml and fill it in."
        ) from None
    except msgspec.ValidationError as e:
        raise SystemExit(f"Invalid {CONFIG_FILE_PATH}: {e}") from None


def _resolve_db_url(url: str) -> str:
    host_override = os.getenv("DB_HOST")
    if not host_override:
        return url
    parsed = urlparse(url)
    userinfo, _, hostport = parsed.netloc.rpartition("@")
    _, sep, port = hostport.partition(":")
    new_netloc = f"{host_override}{sep}{port}"
    if userinfo:
        new_netloc = f"{userinfo}@{new_netloc}"
    return urlunparse(parsed._replace(netloc=new_netloc))


@dataclass(frozen=True)
class ColorConfig:
    theme: int
    green: int
    red: int
    orange: int


_config = _load()

owner_id: int = _config.owner_id
owner_guild_ids: list[int] = _config.owner_guild_ids
system_channel_id: int = _config.system_channel_id
support_server_url: str = _config.support_server_url
dashboard_url: str = _config.dashboard_url.rstrip("/")
bot_token: str = _config.bot_token
db_url: str = _resolve_db_url(_config.database_url)
log_level: str = _config.log_level
log_file: bool = _config.log_file
api: ApiConfig | None = _config.api

color = ColorConfig(
    **{key: int(value.lstrip("#"), 16) for key, value in msgspec.structs.asdict(_config.colors).items()}
)

lavalink: list[LavalinkConfig] = _config.lavalink if isinstance(_config.lavalink, list) else [_config.lavalink]
