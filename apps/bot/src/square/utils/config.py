import msgspec
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse, urlunparse

CONFIG_FILE_PATH = Path("config.toml")


class _Colors(msgspec.Struct, forbid_unknown_fields=True):
    theme: str
    green: str
    red: str
    orange: str


class ApiConfig(msgspec.Struct, rename="kebab", forbid_unknown_fields=True, frozen=True, kw_only=True):
    host: str = "127.0.0.1"
    port: Annotated[int, msgspec.Meta(ge=1, le=65535)] = 8080
    secret: Annotated[str, msgspec.Meta(min_length=32)]
    docs: bool = False


class StorageConfig(msgspec.Struct, rename="kebab", forbid_unknown_fields=True, frozen=True):
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str | None = None


class LavalinkConfig(msgspec.Struct, forbid_unknown_fields=True, frozen=True):
    host: str
    port: int
    password: str
    secure: bool
    regions: list[str] | None = None


class _Config(msgspec.Struct, rename="kebab", forbid_unknown_fields=True, kw_only=True):
    owner_id: int
    owner_guild_ids: list[int]
    system_channel_id: int
    dashboard_url: str
    bot_token: str
    database_url: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: bool = False
    colors: _Colors
    api: ApiConfig | None = None
    storage: StorageConfig
    lavalink: list[LavalinkConfig] | LavalinkConfig


def _load() -> _Config:
    try:
        with open(CONFIG_FILE_PATH, "rb") as file:
            return msgspec.toml.decode(file.read(), type=_Config)
    except FileNotFoundError:
        raise SystemExit(f"{CONFIG_FILE_PATH} not found. Run `just init` to create it.") from None
    except msgspec.ValidationError as e:
        raise SystemExit(f"Invalid {CONFIG_FILE_PATH}: {e}") from None


def _override_host(url: str, variable: str) -> str:
    host_override = os.getenv(variable)
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
dashboard_url: str = _config.dashboard_url.rstrip("/")
bot_token: str = _config.bot_token
db_url: str = _override_host(_config.database_url, "DB_HOST")
log_level: str = _config.log_level
log_file: bool = _config.log_file

color = ColorConfig(
    **{key: int(value.lstrip("#"), 16) for key, value in msgspec.structs.asdict(_config.colors).items()}
)

# Docker sets this, since the API has to listen beyond the container's own loopback there
api: ApiConfig | None = (
    msgspec.structs.replace(_config.api, host=host) if _config.api and (host := os.getenv("API_HOST")) else _config.api
)
storage: StorageConfig = msgspec.structs.replace(
    _config.storage, endpoint=_override_host(_config.storage.endpoint, "STORAGE_HOST")
)
lavalink: list[LavalinkConfig] = _config.lavalink if isinstance(_config.lavalink, list) else [_config.lavalink]
