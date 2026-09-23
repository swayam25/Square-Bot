import discord
from core import Client
from db.funcs.music import (
    fetch_all_music_channels,
    remove_music_channel,
    set_music_channel,
    set_music_message,
)
from music import store

# Messages swept from a request channel on startup. Bulk delete caps at 100, and anything older
# than that is history nobody is scrolling a request channel for.
PURGE_LIMIT = 100

# guild_id -> (channel_id, card_message_id or None)
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
    """Whether the guild has a music request channel bound."""
    return guild_id in _bindings


def channel_id(guild_id: int) -> int | None:
    """Returns the guild's bound request channel ID, or None when it has none."""
    binding = _bindings.get(guild_id)
    return binding[0] if binding else None


def message_id(guild_id: int) -> int | None:
    """Returns the ID of the card the guild's request channel currently holds, if any."""
    binding = _bindings.get(guild_id)
    return binding[1] if binding else None


def is_request_channel(guild_id: int, channel_id: int) -> bool:
    """
    Whether a channel is the guild's bound request channel.

    A plain dict lookup: this runs for every message the bot sees.
    """
    binding = _bindings.get(guild_id)
    return binding is not None and binding[0] == channel_id


async def bind(guild_id: int, channel_id: int) -> None:
    """
    Binds a request channel to a guild, dropping any card ID left from a previous binding.

    Args:
        guild_id (int): The guild to bind the channel for.
        channel_id (int): The channel that becomes the request channel.
    """
    await set_music_channel(guild_id, channel_id)
    _bindings[guild_id] = (channel_id, None)


async def bind_message(guild_id: int, msg_id: int | None) -> None:
    """
    Records which message holds the guild's card, so a restart adopts it instead of posting another.

    Args:
        guild_id (int): The guild whose card moved.
        msg_id (int | None): The card's new message ID.
    """
    binding = _bindings.get(guild_id)
    if not binding:
        return
    await set_music_message(guild_id, msg_id)
    _bindings[guild_id] = (binding[0], msg_id)


async def unbind(guild_id: int) -> None:
    """
    Drops the guild's request channel binding, returning it to the free-form player.

    Args:
        guild_id (int): The guild to unbind.
    """
    # Cache first. The DB write is an await, and `on_guild_channel_delete` reads the cache, so
    # leaving the binding up across it lets a delete land while the guild is still nominally bound.
    _bindings.pop(guild_id, None)
    await remove_music_channel(guild_id)


def forget(guild_id: int) -> None:
    """
    Drops the cached binding without touching the database.

    For when the row is already gone - the guild was left, or `/settings reset all` deleted it.
    """
    _bindings.pop(guild_id, None)


def prime(client: Client, guild_id: int) -> bool:
    """
    Re-seeds the player store from the binding, without a single API call.

    Teardown flushes the store, but a bound guild still has a card in its channel.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to re-seed.

    Returns:
        bool: True when the guild is bound and its channel resolved.
    """
    binding = _bindings.get(guild_id)
    if not binding:
        return False
    channel = client.get_channel(binding[0])
    if channel is None:
        return False
    store.play_ch(guild_id, channel, "set")
    existing, _ = store.play_msg(guild_id)
    if binding[1] and (existing is None or existing.id != binding[1]):
        # A partial is enough: an unknown card state makes the next render repost anyway.
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
    from music.player import MusicView, card_attachments, idle_attachment, release_guild

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
        return  # Already adopted; a resume re-fired this.
    store.play_ch(guild_id, channel, "set")
    view = MusicView(client, guild_id)
    state = "live" if view.live else "idle"
    msg = None
    if mid is not None:
        try:
            msg = await channel.fetch_message(mid)
            msg = await msg.edit(view=view, **card_attachments(view.live))
        except discord.NotFound, discord.Forbidden:
            msg = None
        except discord.HTTPException:
            return
    if msg is None:
        msg = await channel.send(view=view, **(idle_attachment() if state == "idle" else {}))
        await bind_message(guild_id, msg.id)
    store.card_state(guild_id, state, "set")
    store.play_msg(guild_id, msg, view, "set")
    await purge(channel, msg.id)


async def purge(channel: discord.TextChannel, keep_id: int) -> None:
    """
    Clears everything but the card out of a request channel.

    Toasts, pickers and requests all delete themselves, but a restart orphans whichever were in
    flight when the bot went down, so the channel is swept once on the way back up.

    Args:
        channel (:class:`TextChannel`): The bound request channel.
        keep_id (int): The player card, the one message that stays.
    """
    try:
        await channel.purge(limit=PURGE_LIMIT, check=lambda m: m.id != keep_id)
    except discord.HTTPException:
        pass  # Without Manage Messages the channel keeps its clutter; the card still works.


async def adopt_all(client: Client) -> None:
    """
    Adopts every bound guild's card, one at a time so a broken guild can't take the rest down.

    Args:
        client (:class:`Client`): The Discord bot client.
    """
    for guild_id in list(_bindings):
        try:
            await adopt(client, guild_id)
        except Exception:
            continue
