import json
import os
from attr import dataclass
from rich import print
from utils import config

custom_emoji_file_path = "./.cache/emoji.json"
if not any([config.emoji_type == "custom", config.emoji_type == "default"]):
    print(f"[red][bold]✗[/] Invalid emoji type in [cyan]{config.config_file_path}[/]: {config.emoji_type}[/]")
    print("[yellow][bold]![/] Please choose either [green]custom[/] or [green]default[/].[/]")
    exit(1)


# Emoji class to hold all the emojis used in the bot.
@dataclass
class Emoji:
    bullet: str = "•"
    bullet_red: str = "•"
    error: str = "❌"
    success: str = "✅"
    on: str = "🟢"
    off: str = "🔴"
    next_white: str = "⏭️"
    previous_white: str = "⏮️"
    start_white: str = "⏪"
    end_white: str = "⏩"

    settings: str = "⚙️"
    emoji: str = "😀"
    info: str = "ℹ️"
    mod: str = "🛠️"
    mass_mod: str = "👥"
    ticket: str = "🎫"

    mention: str = "🔔"
    id: str = "🆔"
    id_red: str = "🆔"
    user: str = "👤"
    user_red: str = "👤"
    bot: str = "🤖"
    description: str = "📝"
    description_red: str = "📝"
    description_white: str = "📝"
    media: str = "🖼️"
    media_red: str = "🖼️"
    date: str = "📅"
    date_red: str = "📅"
    role: str = "🔖"
    lock_white: str = "🔒"
    channel: str = "📺"
    channel_red: str = "📺"
    members: str = "👥"
    members_red: str = "👥"
    owner: str = "👑"
    owner_red: str = "👑"
    msg: str = "💬"
    msg_red: str = "💬"
    msg_edit: str = "✏️"
    msg_link: str = "🔗"
    link: str = "🔗"
    verification: str = "🛡️"
    join: str = "➕"
    join_red: str = "➕"
    leave: str = "➖"

    python: str = "🐍"
    ping: str = "🏓"
    server: str = "🖥️"
    server_red: str = "🖥️"
    lavalink: str = "🎵"

    pycord: str = "🐍"
    spotify: str = "🟢"
    youtube: str = "🔴"
    soundcloud: str = "🟠"

    music: str = "🎵"
    duration: str = "⏱️"
    duration_red: str = "⏱️"
    live: str = "🔴"
    play: str = "▶️"
    play_white: str = "▶️"
    pause: str = "⏸️"
    pause_white: str = "⏸️"
    seek: str = "⏩"
    skip: str = "⏭️"
    skip_white: str = "⏭️"
    stop: str = "⏹️"
    stop_white: str = "⏹️"
    volume: str = "🔊"
    shuffle: str = "🔀"
    shuffle_white: str = "🔀"
    loop: str = "🔁"
    loop_one: str = "🔂"
    loop_white: str = "🔁"
    equalizer: str = "🎛️"
    empty_bar: str = "⬜"
    filled_bar: str = "🟥"

    restart: str = "🔄"
    shutdown: str = "🔴"
    console: str = "🖥️"
    upload: str = "📤"
    bin_white: str = "🗑️"

    @staticmethod
    def from_json(file_path: str) -> "Emoji":
        try:
            with open(file_path, encoding="utf8") as emoji_file:
                emoji_data: dict[str, str] = dict(json.load(emoji_file))

            # Validate keys
            missing_keys = [key for key in Emoji.__annotations__.keys() if key not in emoji_data]
            with open(file_path, "w", encoding="utf8") as f:
                new_data = emoji_data.copy()
                for key in emoji_data:
                    if key not in Emoji.__annotations__.keys():
                        new_data.pop(key, None)
                json.dump(new_data, f, indent=4)

            if missing_keys:
                print(f"[red][bold]✗[/] Missing keys in emoji JSON: [cyan]{','.join(missing_keys)}[/][/]")
                exit(1)

            # Create Emoji instance
            return Emoji(**{key: emoji_data.get(key, "") for key in Emoji.__annotations__.keys()})

        except FileNotFoundError:
            print(
                f"[red][bold]✗[/] Custom emoji file not found: {file_path}[/]",
                "[yellow][bold]![/] Make sure to run [cyan]/emoji upload[/] command and upload emojis to the bot.[/]",
                "[yellow][bold]![/] Try manually running [cyan]/emoji sync[/] to create required config files.[/]",
                "[yellow][bold]![/] Read the README.md for more information on how to set up custom emojis.[/]",
                f"[yellow][bold]![/] If you want to use default emojis, change the emoji type in [cyan]{config.config_file_path}[/] to [green]default[/].[/]",
            )
            exit(1)

    @staticmethod
    def create_custom_emoji_config(emojis: dict) -> dict:
        os.makedirs(os.path.dirname(custom_emoji_file_path), exist_ok=True)
        with open(custom_emoji_file_path, "w", encoding="utf8") as emoji_file:
            missing_keys = [key for key in Emoji.__annotations__.keys() if key not in emojis]
            extra_keys = [emojis[key] for key in emojis if key not in Emoji.__annotations__.keys()]
            if missing_keys:
                return {"status": "error", "missing_keys": missing_keys}
            else:
                emojis = {key: emojis[key] for key in Emoji.__annotations__.keys()}
                json.dump(emojis, emoji_file, ensure_ascii=False, indent=4)
                msg = {"status": "success"}
                if extra_keys:
                    msg["extra_keys"] = extra_keys
                return msg


emoji = Emoji.from_json(custom_emoji_file_path) if config.emoji_type == "custom" else Emoji()
