import discord
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CUSTOM_EMOJI_FILE_PATH = Path(".cache/emoji.json")
EMOJI_DIR = Path("emojis")


class Icon(discord.PartialEmoji):
    def __init__(self, default: str):
        super().__init__(name=default)
        self.default = default

    def set(self, value: str | None) -> None:
        parsed = discord.PartialEmoji.from_str(value if value and value.strip() else self.default)
        self.name, self.id, self.animated = parsed.name, parsed.id, parsed.animated


class Emoji:
    """
    Every emoji the bot uses. Add a line here and a same-named file in `emojis/`, then sync from `/emoji`.

    Mass moderation builds some names at runtime (`owner` + `_red`/`_orange`/`_green`), so a text search can't prove
    an emoji unused.
    """

    bullet = Icon("•")
    bullet_red = Icon("•")
    success = Icon("✅")
    error = Icon("❌")
    on = Icon("🟢")
    next_white = Icon("⏭️")
    previous_white = Icon("⏮️")
    start_white = Icon("⏪")
    end_white = Icon("⏩")
    up_white = Icon("⬆️")
    down_white = Icon("⬇️")
    bottom_right = Icon("↪️")
    loading = Icon("⏳")
    loading_white = Icon("⏳")
    copy_white = Icon("📋")

    settings = Icon("⚙️")
    info = Icon("ℹ️")
    mod = Icon("🔨")
    mod_red = Icon("🔨")
    mass_mod = Icon("👥")
    ticket = Icon("🎫")
    ticket_white = Icon("🎫")
    ticket_red = Icon("🎫")
    claim = Icon("✋")
    claim_white = Icon("✋")
    lock_red = Icon("🔒")
    unlock_white = Icon("🔓")
    user_add_white = Icon("➕")
    user_remove_white = Icon("➖")
    transcript_white = Icon("📄")
    messages_red = Icon("💬")
    support_red = Icon("🛟")

    mention = Icon("🔔")
    id = Icon("🆔")
    id_red = Icon("🆔")
    id_green = Icon("🆔")
    user = Icon("👤")
    user_white = Icon("👤")
    user_red = Icon("👤")
    user_green = Icon("👤")
    user_orange = Icon("👤")
    profile_white = Icon("👔")
    crown = Icon("👑")
    perms = Icon("🔐")
    perms_white = Icon("🔐")
    bot = Icon("🤖")
    keyboard = Icon("⌨️")
    keyboard_red = Icon("⌨️")
    description = Icon("📝")
    description_red = Icon("📝")
    description_green = Icon("📝")
    description_orange = Icon("📝")
    img = Icon("🖼️")
    date = Icon("📅")
    role = Icon("🔖")
    role_red = Icon("🔖")
    role_green = Icon("🔖")
    voice = Icon("🔊")
    voice_red = Icon("🔊")
    invite = Icon("🔗")
    invite_red = Icon("🔗")
    joins_green = Icon("📥")
    fake = Icon("⚠️")
    lock_white = Icon("🔒")
    channel = Icon("📺")
    channel_red = Icon("📺")
    category = Icon("📂")
    category_red = Icon("📂")
    members = Icon("👥")
    members_red = Icon("👥")
    members_green = Icon("👥")
    owner = Icon("👑")
    owner_red = Icon("👑")
    owner_green = Icon("👑")
    owner_orange = Icon("👑")
    verification = Icon("🛡️")
    add = Icon("➕")
    add_red = Icon("➕")
    remove = Icon("➖")
    server = Icon("🖥️")
    server_red = Icon("🖥️")
    boost = Icon("🚀")

    ping = Icon("🏓")
    more = Icon("⚙️")
    more_white = Icon("⚙️")

    spotify = Icon("🟢")
    youtube = Icon("🔴")
    soundcloud = Icon("🟠")

    music = Icon("🎵")
    music_white = Icon("🎵")
    mic = Icon("🎤")
    duration = Icon("⏱️")
    duration_white = Icon("⏱️")
    duration_red = Icon("⏱️")
    duration_green = Icon("⏱️")
    duration_orange = Icon("⏱️")
    live = Icon("🔴")
    play = Icon("▶️")
    play_white = Icon("▶️")
    autoplay = Icon("💡")
    autoplay_white = Icon("💡")
    pause = Icon("⏸️")
    pause_white = Icon("⏸️")
    rewind = Icon("⏪")
    rewind10s_white = Icon("⏪")
    forward = Icon("⏩")
    forward10s_white = Icon("⏩")
    back = Icon("⏮️")
    back_white = Icon("⏮️")
    skip = Icon("⏭️")
    skip_white = Icon("⏭️")
    stop = Icon("⏹️")
    stop_white = Icon("⏹️")
    shuffle = Icon("🔀")
    shuffle_white = Icon("🔀")
    loop = Icon("🔁")
    loop_one = Icon("🔂")
    loop_white = Icon("🔁")
    queue_white = Icon("🎶")
    equalizer = Icon("🎛️")
    empty_bar = Icon("░")
    filled_bar = Icon("█")
    still_bar = Icon("█")

    reload = Icon("🔄")
    reload_white = Icon("🔄")
    sync_white = Icon("🔄")
    shutdown = Icon("🔴")
    console = Icon("🖥️")
    console_green = Icon("🖥️")
    bin_red = Icon("🗑️")
    bin_green = Icon("🗑️")
    bin_white = Icon("🗑️")


emoji = Emoji()
_icons: dict[str, Icon] = {name: icon for name, icon in vars(Emoji).items() if isinstance(icon, Icon)}


def get_emoji_names() -> list[str]:
    return list(_icons)


def create_custom_emoji_config(emojis: dict[str, str]) -> dict:
    CUSTOM_EMOJI_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    default_emoji_keys = [name for name in _icons if not emojis.get(name, "").strip()]
    extra_keys = [name for name in emojis if name not in _icons]
    final_emojis = {
        name: emojis[name] if name not in default_emoji_keys else icon.default for name, icon in _icons.items()
    }

    with open(CUSTOM_EMOJI_FILE_PATH, "w", encoding="utf8") as emoji_file:
        json.dump(final_emojis, emoji_file, ensure_ascii=False, indent=4)

    msg: dict = {"status": "success"}
    if default_emoji_keys:
        msg["default_emojis_used"] = default_emoji_keys
    if extra_keys:
        msg["extra_keys_ignored"] = extra_keys
    return msg


def update_emoji(name: str, value: str | None) -> None:
    """
    Points one emoji at `value` in place, or back to its default when it's None.

    A sync resets an emoji before deleting it and sets the new one once uploaded, so views drawn mid-sync never send a
    deleted emoji's ID.
    """
    if icon := _icons.get(name):
        icon.set(value)


def reload_emoji() -> None:
    try:
        with open(CUSTOM_EMOJI_FILE_PATH, encoding="utf8") as emoji_file:
            saved: dict[str, str] = dict(json.load(emoji_file))
    except FileNotFoundError:
        log.warning(
            "Custom emoji file %s not found, using default emojis. Sync them from /emoji",
            CUSTOM_EMOJI_FILE_PATH,
        )
        saved = {}
    else:
        known = {name: value for name, value in saved.items() if name in _icons}
        if len(known) != len(saved):
            with open(CUSTOM_EMOJI_FILE_PATH, "w", encoding="utf8") as emoji_file:
                json.dump(known, emoji_file, ensure_ascii=False, indent=4)

    for name, icon in _icons.items():
        icon.set(saved.get(name))


reload_emoji()
