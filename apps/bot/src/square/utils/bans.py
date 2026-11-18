import asyncio
import discord
import re
from square.utils.helpers import fmt_user

CHOICE_LIMIT = 25
# Autocomplete has 3 seconds to answer, so a first load that runs longer finishes for the next keystroke
LOAD_WAIT = 2.0
_MENTION_OR_ID = re.compile(r"<@!?(\d+)>|(\d+)")

# Ban lists per guild, filled on first use and kept current by `remember` and `forget` from the ban events
_lists: dict[int, dict[int, discord.User]] = {}
_loading: dict[int, asyncio.Task[list[discord.User]]] = {}


async def banned_users(guild: discord.Guild) -> list[discord.User]:
    """The full list straight from Discord, which also refreshes the cache."""
    users = {entry.user.id: entry.user async for entry in guild.bans(limit=None)}
    _lists[guild.id] = users
    return list(users.values())


def remember(guild_id: int, user: discord.User) -> None:
    if (users := _lists.get(guild_id)) is not None:
        users[user.id] = user


def forget(guild_id: int, user_id: int) -> None:
    if (users := _lists.get(guild_id)) is not None:
        users.pop(user_id, None)


def parse_id(text: str) -> int | None:
    if found := _MENTION_OR_ID.fullmatch(text.strip()):
        return int(found.group(1) or found.group(2))
    return None


def find(users: list[discord.User], text: str) -> discord.User | None:
    """Matches a mention, an ID or a username, then a global name only when exactly one banned user has it."""
    text = text.strip()
    if (user_id := parse_id(text)) is not None:
        return next((user for user in users if user.id == user_id), None)
    name = text.removeprefix("@").lower()
    if user := next((user for user in users if user.name.lower() == name), None):
        return user
    named = [user for user in users if user.global_name and user.global_name.lower() == name]
    return named[0] if len(named) == 1 else None


def find_cached(guild_id: int, text: str) -> discord.User | None:
    users = _lists.get(guild_id)
    return find(list(users.values()), text) if users else None


async def lookup(guild: discord.Guild, text: str) -> discord.User | None:
    """
    Asks Discord, so a cache that missed a ban never refuses a real one.

    An ID or mention costs one request. Only a name needs the whole ban list.
    """
    if (user_id := parse_id(text)) is not None:
        try:
            return (await guild.fetch_ban(discord.Object(user_id))).user
        except discord.NotFound:
            return None
    return find(await banned_users(guild), text)


async def _cached(guild: discord.Guild) -> list[discord.User] | None:
    if (users := _lists.get(guild.id)) is not None:
        return list(users.values())
    task = _loading.get(guild.id)
    if task is None:
        task = _loading[guild.id] = asyncio.create_task(banned_users(guild))
        task.add_done_callback(lambda _: _loading.pop(guild.id, None))
    try:
        return await asyncio.wait_for(asyncio.shield(task), LOAD_WAIT)
    except TimeoutError, discord.HTTPException:
        return None


async def autocomplete(ctx: discord.AutocompleteContext) -> list[discord.OptionChoice]:
    """
    Banned users whose username, global name or ID contains what's typed so far.

    Members without Ban Members get nothing, so the list never leaks to them.
    """
    guild = ctx.interaction.guild
    if guild is None or not ctx.interaction.permissions.ban_members:
        return []
    if (users := await _cached(guild)) is None:
        return []
    typed = (ctx.value or "").strip().removeprefix("@").lower()
    matches = [
        user
        for user in users
        if typed in user.name.lower() or typed in (user.global_name or "").lower() or typed in str(user.id)
    ]
    return [discord.OptionChoice(name=fmt_user(user)[:100], value=str(user.id)) for user in matches[:CHOICE_LIMIT]]
