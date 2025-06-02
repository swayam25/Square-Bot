import toml
from attr import dataclass
from typing import TypedDict

config_file_path = "./config.toml"

# Load the configuration file
with open(config_file_path) as f:
    data = toml.load(f)


# Bot configuration
owner_id: int = data["owner-id"]
owner_guild_ids: list[int] = data["owner-guild-ids"]
system_channel_id: int = data["system-channel-id"]
support_server_url: str = data["support-server-url"]
emoji_type: str = data["emoji"]
bot_token: str = data["bot-token"]
db_url: str = data["database-url"]


# Colors
@dataclass
class ColorConfig:
    theme: int
    error: int


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


# Spotify configuration
class SpotifyConfig(TypedDict):
    client_id: str
    client_secret: str


spotify: SpotifyConfig = data["spotify"]
