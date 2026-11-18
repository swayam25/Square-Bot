import discord
import re
import time
from square.utils.helpers import fmt_user

AUTOCOMPLETE_TTL = 30
CHOICE_LIMIT = 25
_MENTION_OR_ID = re.compile(r"<@!?(\d+)>|(\d+)")

_cache: dict[int, tuple[float, list[discord.User]]] = {}


async def banned_users(guild: discord.Guild) -> list[discord.User]:
    users = [entry.user async for entry in guild.bans(limit=None)]
    _cache[guild.id] = (time.monotonic(), users)
    return users


def find(users: list[discord.User], text: str) -> discord.User | None:
    """Matches a mention, an ID or a username, then a global name only when exactly one banned user has it."""
    text = text.strip()
    if found := _MENTION_OR_ID.fullmatch(text):
        user_id = int(found.group(1) or found.group(2))
        return next((user for user in users if user.id == user_id), None)
    name = text.removeprefix("@").lower()
    if user := next((user for user in users if user.name.lower() == name), None):
        return user
    named = [user for user in users if user.global_name and user.global_name.lower() == name]
    return named[0] if len(named) == 1 else None


async def autocomplete(ctx: discord.AutocompleteContext) -> list[discord.OptionChoice]:
    """
    Banned users whose username, global name or ID contains what's typed so far.

    The ban list is reused for `AUTOCOMPLETE_TTL` seconds, since Discord asks again on every keystroke. Members
    without Ban Members get nothing, so the list never leaks to them.
    """
    guild = ctx.interaction.guild
    if guild is None or not ctx.interaction.permissions.ban_members:
        return []
    cached = _cache.get(guild.id)
    try:
        users = cached[1] if cached and time.monotonic() - cached[0] < AUTOCOMPLETE_TTL else await banned_users(guild)
    except discord.HTTPException:
        return []
    typed = (ctx.value or "").strip().removeprefix("@").lower()
    matches = [
        user
        for user in users
        if typed in user.name.lower() or typed in (user.global_name or "").lower() or typed in str(user.id)
    ]
    return [discord.OptionChoice(name=fmt_user(user)[:100], value=str(user.id)) for user in matches[:CHOICE_LIMIT]]
