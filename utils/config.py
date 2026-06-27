import os
import toml
from attr import dataclass
from typing import TypedDict
from urllib.parse import urlparse, urlunparse

config_file_path = "./config.toml"

# Load the configuration file
with open(config_file_path) as f:
    data = toml.load(f)


# Bot configuration
owner_id: int = data["owner-id"]
owner_guild_ids: list[int] = data["owner-guild-ids"]
system_channel_id: int = data["system-channel-id"]
support_server_url: str = data["support-server-url"]
bot_token: str = data["bot-token"]


def _resolve_db_url(url: str) -> str:
    """Override the database host with the `DB_HOST` env var if set.

    Lets `config.toml` stay on the production host (`db`) while local
    development connects to the published port via `DB_HOST=localhost`.
    """
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


db_url: str = _resolve_db_url(data["database-url"])


# Colors
@dataclass
class ColorConfig:
    theme: int
    green: int
    red: int
    orange: int


def colors() -> ColorConfig:
    """Returns the color configuration."""
    color = data["colors"]
    for key, value in color.items():
        color[key] = int(value.replace("#", ""), 16)
    return ColorConfig(**color)


color = colors()


# Lavalink configuration
class LavalinkConfig(TypedDict):
    host: str
    port: int
    password: str
    secure: bool


lavalink: LavalinkConfig = data["lavalink"]
