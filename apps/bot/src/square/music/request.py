import discord
from square.core import Client
from square.db.funcs.music import (
    fetch_all_music_channels,
    remove_music_channel,
    set_music_channel,
    set_music_message,
)
from square.music import store

PURGE_LIMIT = 100

# Kept out of `music/store.py`, whose keys `flush_store` wipes on every teardown.
_bindings: dict[int, tuple[int, int | None]] = {}


async def seed() -> None:
    """
    Rebuilds the binding cache from the database.

    Called on every ready, including resumes, so it replaces the dict wholesale rather than merging.
    The fetch comes first: clearing before it would leave every guild looking unbound for the
    length of the query, which is long enough for a request channel to stop behaving like one.
    """
    bindings = await fetch_all_music_channels()
    _bindings.clear()
    _bindings.update(bindings)


def setup_mode(guild_id: int) -> bool:
    return guild_id in _bindings


def channel_id(guild_id: int) -> int | None:
    binding = _bindings.get(guild_id)
    return binding[0] if binding else None


def message_id(guild_id: int) -> int | None:
    binding = _bindings.get(guild_id)
    return binding[1] if binding else None


def is_request_channel(guild_id: int, channel_id: int) -> bool:
    binding = _bindings.get(guild_id)
    return binding is not None and binding[0] == channel_id


async def bind(guild_id: int, channel_id: int) -> None:
    await set_music_channel(guild_id, channel_id)
    _bindings[guild_id] = (channel_id, None)


async def bind_message(guild_id: int, msg_id: int | None) -> None:
    binding = _bindings.get(guild_id)
    if not binding:
        return
    await set_music_message(guild_id, msg_id)
    _bindings[guild_id] = (binding[0], msg_id)


async def unbind(guild_id: int) -> None:
    # Cache first. The DB write is an await, and `on_guild_channel_delete` reads the cache, so
    # leaving the binding up across it lets a delete land while the guild is still nominally bound.
    _bindings.pop(guild_id, None)
    await remove_music_channel(guild_id)


def forget(guild_id: int) -> None:
    _bindings.pop(guild_id, None)


def prime(client: Client, guild_id: int) -> bool:
    binding = _bindings.get(guild_id)
    if not binding:
        return False
    channel = client.get_channel(binding[0])
    if channel is None:
        return False
    store.play_ch(guild_id, channel, "set")
    existing, _ = store.play_msg(guild_id)
    if binding[1] and (existing is None or existing.id != binding[1]):
        store.play_msg(guild_id, channel.get_partial_message(binding[1]), None, "set")
    return True


async def adopt(client: Client, guild_id: int) -> None:
    """
    Takes ownership of a bound guild's existing card, or posts one when there isn't a usable one.

    Editing re-arms the buttons, since every send and edit stores the view against the message ID.
    Not `client.add_view`: the custom IDs are generic words like `pause`, so a view registered
    without a message ID would swallow every guild's presses.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild whose card should be adopted.
    """
    from square.music.player import MusicView, has_idle_gif, idle_attachment, idle_edit_attachments, release_guild

    binding = _bindings.get(guild_id)
    if not binding:
        return
    cid, mid = binding
    channel = client.get_channel(cid)
    if channel is None:
        try:
            channel = await client.fetch_channel(cid)
        except discord.NotFound, discord.Forbidden:
            await unbind(guild_id)
            await release_guild(client, guild_id)
            return
        except discord.HTTPException:
            return
    existing, _ = store.play_msg(guild_id)
    if existing is not None and mid is not None and existing.id == mid:
        return
    store.play_ch(guild_id, channel, "set")
    view = MusicView(client, guild_id)
    msg = None
    if mid is not None:
        try:
            msg = await channel.fetch_message(mid)
            msg = await msg.edit(view=view, **({} if view.live else idle_edit_attachments(msg)))
        except discord.NotFound, discord.Forbidden:
            msg = None
        except discord.HTTPException:
            return
    if msg is None:
        msg = await channel.send(view=view, **({} if view.live else idle_attachment()))
        await bind_message(guild_id, msg.id)
    store.card_gif(guild_id, has_idle_gif(msg), "set")
    store.play_msg(guild_id, msg, view, "set")
    await purge(channel, msg.id)


async def purge(channel: discord.TextChannel, keep_id: int) -> None:
    try:
        await channel.purge(limit=PURGE_LIMIT, check=lambda m: m.id != keep_id)
    except discord.HTTPException:
        pass


async def adopt_all(client: Client) -> None:
    for guild_id in list(_bindings):
        try:
            await adopt(client, guild_id)
        except Exception:
            continue
