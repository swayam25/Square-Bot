import json
import os
from attr import dataclass
from rich import print

custom_emoji_file_path = "./.cache/emoji.json"


# Emoji class to hold all the emojis used in the bot.
@dataclass
class Emoji:
    bullet: str = "•"
    bullet_red: str = "•"
    success: str = "✅"
    error: str = "❌"
    on: str = "🟢"
    off: str = "🔴"
    next_white: str = "⏭️"
    previous_white: str = "⏮️"
    start_white: str = "⏪"
    end_white: str = "⏩"
    up_white: str = "⬆️"
    down_white: str = "⬇️"
    bottom_right: str = "↪️"
    upvote: str = "👍"
    downvote: str = "👎"
    loading: str = "⏳"
    loading_white: str = "⏳"
    copy_white: str = "📋"

    settings: str = "⚙️"
    info: str = "ℹ️"
    mod: str = "🛠️"
    mass_mod: str = "👥"
    ticket: str = "🎫"
    fun: str = "🤣"

    mention: str = "🔔"
    id: str = "🆔"
    id_red: str = "🆔"
    user: str = "👤"
    user_white: str = "👤"
    user_red: str = "👤"
    profile_white: str = "👔"
    crown: str = "👑"
    perms: str = "🔐"
    perms_white: str = "🔐"
    bot: str = "🤖"
    bot_white: str = "🤖"
    emoji: str = "😀"
    keyboard: str = "⌨️"
    description: str = "📝"
    description_red: str = "📝"
    description_white: str = "📝"
    img: str = "🖼️"
    img_red: str = "🖼️"
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
    server: str = "🖥️"
    server_red: str = "🖥️"
    boost: str = "🚀"

    coin: str = "🪙"
    dice: str = "🎲"
    numbers: str = "🔢"
    sparkles: str = "✨"
    dog: str = "🐶"

    python: str = "🐍"
    ping: str = "🏓"
    memory: str = "📈"
    storage: str = "💾"
    tasks: str = "📊"
    cpu: str = "📡"
    lavalink: str = "🌋"
    lavalink_white: str = "🌋"
    more: str = "⚙️"
    more_white: str = "⚙️"

    pycord: str = "🐍"
    spotify: str = "🟢"
    youtube: str = "🔴"
    soundcloud: str = "🟠"
    reddit: str = "🔴"

    music: str = "🎵"
    mic: str = "🎤"
    duration: str = "⏱️"
    duration_white: str = "⏱️"
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

    reload: str = "🔄"
    reload_white: str = "🔄"
    shutdown: str = "🔴"
    console: str = "🖥️"
    console_green: str = "🖥️"
    bin_red: str = "🗑️"
    bin_white: str = "🗑️"

    @staticmethod
    def from_json(file_path: str) -> Emoji:
        """Load custom emojis and fall back to default emojis for missing ones."""
        default_emoji = Emoji()

        try:
            with open(file_path, encoding="utf8") as emoji_file:
                emoji_data: dict[str, str] = dict(json.load(emoji_file))

            # Clean up the JSON file by removing invalid keys
            with open(file_path, "w", encoding="utf8") as f:
                new_data = emoji_data.copy()
                for key in emoji_data:
                    if key not in Emoji.__annotations__.keys():
                        new_data.pop(key, None)
                json.dump(new_data, f, indent=4)

            # Create emoji instance: use custom emojis where available, default otherwise
            emoji_data_final = {}
            for key in Emoji.__annotations__.keys():
                if key in emoji_data and emoji_data[key].strip():
                    emoji_data_final[key] = emoji_data[key]
                else:
                    emoji_data_final[key] = getattr(default_emoji, key)

            return Emoji(**emoji_data_final)

        except FileNotFoundError:
            print(f"[yellow]! Custom emoji file not found: {file_path}[/]")
            print("[yellow]! Falling back to default emojis. Use [cyan]/emoji upload[/] to add custom emojis.[/]")
            return default_emoji

    @staticmethod
    def get_emoji_names() -> list[str]:
        """Get a list of all emoji names defined in the Emoji class."""
        return list(Emoji.__annotations__.keys())

    @staticmethod
    def create_custom_emoji_config(emojis: dict) -> dict:
        os.makedirs(os.path.dirname(custom_emoji_file_path), exist_ok=True)
        default_emoji = Emoji()

        with open(custom_emoji_file_path, "w", encoding="utf8") as emoji_file:
            # Find keys that don't have custom emojis (will use defaults)
            default_emoji_keys = []
            extra_keys = [key for key in emojis if key not in Emoji.__annotations__.keys()]

            # Create final emoji config: use provided emojis, fill missing ones with defaults
            final_emojis = {}
            for key in Emoji.__annotations__.keys():
                if key in emojis and emojis[key].strip():
                    final_emojis[key] = emojis[key]
                else:
                    final_emojis[key] = getattr(default_emoji, key)
                    default_emoji_keys.append(key)

            json.dump(final_emojis, emoji_file, ensure_ascii=False, indent=4)

            msg = {"status": "success"}
            if default_emoji_keys:
                msg["default_emojis_used"] = default_emoji_keys
            if extra_keys:
                msg["extra_keys_ignored"] = extra_keys
            return msg


def get_emoji_instance() -> Emoji:
    """Get the emoji instance with custom emojis and default fallback."""
    return Emoji.from_json(custom_emoji_file_path)


emoji = get_emoji_instance()
