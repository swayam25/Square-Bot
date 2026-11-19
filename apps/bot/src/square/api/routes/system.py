from litestar import get
from msgspec import UNSET
from square.api.schemas import BotEmoji, CommandCategory, commands_out
from square.core import Client
from square.utils.emoji import emoji, get_emoji_names


@get("/emojis", summary="Square's own emojis by name, custom ones once synced from /emoji", tags=["System"])
async def bot_emojis() -> dict[str, BotEmoji]:
    icons = {name: getattr(emoji, name) for name in get_emoji_names()}
    return {
        name: BotEmoji(name=icon.name, id=str(icon.id) if icon.id else UNSET, animated=icon.animated)
        for name, icon in icons.items()
    }


@get("/commands", summary="The bot's public commands by category, for the commands page", tags=["System"])
async def bot_commands(client: Client) -> list[CommandCategory]:
    return commands_out(client)
