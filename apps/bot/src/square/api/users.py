import asyncio
import discord
import time
from square.api.schemas import Person, person_of
from square.core import Client

_TTL = 6 * 60 * 60
_MAX = 2000
_fetched: dict[int, tuple[float, discord.User | None]] = {}


async def find_user(client: Client, guild: discord.Guild, user_id: int) -> discord.User | discord.Member | None:
    if user := guild.get_member(user_id) or client.get_user(user_id):
        return user
    if (hit := _fetched.get(user_id)) and time.monotonic() - hit[0] < _TTL:
        return hit[1]
    try:
        user = await client.fetch_user(user_id)
    except discord.NotFound:
        user = None
    except discord.HTTPException:
        return None
    _fetched.pop(user_id, None)
    if len(_fetched) >= _MAX:
        _fetched.pop(next(iter(_fetched)))
    _fetched[user_id] = (time.monotonic(), user)
    return user


async def people_of(client: Client, guild: discord.Guild, user_ids: list[int]) -> list[Person]:
    users = await asyncio.gather(*(find_user(client, guild, user_id) for user_id in user_ids))
    return [person_of(user_id, user) for user_id, user in zip(user_ids, users, strict=True)]
