import asyncio
import discord
import logging
import sonolink
from sonolink.models import Playable
from square.core import Client
from square.music import dj, request, store
from square.music import player as playback
from square.music import queue as queue_view
from square.music.core import SquarePlayer, fmt_time, loop_action, loop_emoji, requester_id, tag_requester
from square.music.errors import MusicError, QueueChanged
from square.music.filters import EQ_PRESETS
from square.music.history import history_tracks
from square.music.utils import music_log, split_log_text
from square.utils import config
from square.utils.emoji import Icon, emoji
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from square.music.play import Enqueued

VOLUME_RANGE = (0, 100)  # 0 is the dashboard's mute; /volume still asks for 1 - 100
CARD_GRACE = 2.0

log = logging.getLogger(__name__)
_painting: set[asyncio.Future] = set()  # Strong refs, or a repaint that outlives its control gets garbage collected


def require_player(
    guild: discord.Guild, member: discord.Member, *, need_track: bool = True, need_queue: bool = False
) -> SquarePlayer:
    if not member.voice or not member.voice.channel:
        raise MusicError("Join a voice channel first.")
    player = guild.voice_client if isinstance(guild.voice_client, SquarePlayer) else None
    bot_channel = guild.me.voice.channel if guild.me.voice else None
    if player is None or bot_channel is None or (need_track and not player.current):
        raise MusicError("Nothing is being played at the current moment.")
    if member.voice.channel != bot_channel:
        raise MusicError("You are not in my voice channel.")
    if need_queue and not len(player.queue):
        raise MusicError("Queue is empty.")
    return player


async def require_dj(member: discord.Member, player: SquarePlayer, *, track: Playable | None = None) -> None:
    if dj.is_dj(member, player) or (track is not None and requester_id(player, track) == member.id):
        return
    raise MusicError("Only a DJ can do that.")


def _queued(player: SquarePlayer, index: int, identifier: str | None) -> Playable:
    queue = player.queue
    if not 0 <= index < len(queue):
        raise MusicError(f"Track number must be between `1` and `{len(queue)}`.")
    track = queue[index]
    if identifier is not None and track.identifier != identifier:
        raise QueueChanged("The queue changed. Have another look and try again.")
    return track


async def _done(
    player: SquarePlayer,
    member: discord.Member,
    icon: Icon,
    action: str,
    *,
    color: int | None = None,
    render: bool = True,
) -> str:
    """
    Posts the public log line, repaints the card and returns the member's confirmation.

    Waits at most `CARD_GRACE` for Discord, since a few quick presses get card edits rate limited for seconds.
    """
    line = music_log(player.guild.id, f"{icon} {member.mention} {action}.", color=color)
    painting = asyncio.gather(line, *([playback.render_player(player.client, player.guild.id)] if render else []))
    finished, _ = await asyncio.wait({painting}, timeout=CARD_GRACE)
    if finished:
        painting.result()
    else:
        _painting.add(painting)
        painting.add_done_callback(_painted)
    return f"{icon} {action[0].upper()}{action[1:]}."


def _painted(painting: asyncio.Future) -> None:
    _painting.discard(painting)
    if not painting.cancelled() and (error := painting.exception()):
        log.error("Card repaint failed after its control had answered", exc_info=error)


async def set_paused(guild: discord.Guild, member: discord.Member, paused: bool | None = None) -> str:
    player = require_player(guild, member)
    await require_dj(member, player)
    if paused is None:
        paused = not player.paused
    elif paused == player.paused:
        raise MusicError("Player is already paused." if paused else "Player isn't paused.")
    if paused:
        await player.pause()
    else:
        await player.resume()
    return await _done(
        player, member, emoji.pause if paused else emoji.play, "paused the player" if paused else "resumed the player"
    )


async def stop(guild: discord.Guild, member: discord.Member) -> str:
    player = require_player(guild, member, need_track=False)
    await require_dj(member, player)
    action = f"{playback.stop_verb(guild.id)} the player"
    await asyncio.gather(
        music_log(guild.id, f"{emoji.stop} {member.mention} {action}."), playback.stop_player(player, guild)
    )
    return f"{emoji.stop} {action.capitalize()}."


async def seek(guild: discord.Guild, member: discord.Member, position_ms: int) -> str:
    player = require_player(guild, member)
    await require_dj(member, player)
    track = player.current
    if track.is_stream:
        raise MusicError("Can't seek a live stream.")
    if position_ms >= track.length:
        await playback.skip_or_stop(player, guild)
        return await _done(player, member, emoji.skip, "skipped the track", render=False)
    position_ms = max(0, position_ms)
    icon = emoji.rewind if position_ms < player.position else emoji.forward
    await player.seek(position_ms)
    playback.start_progress(player.client, guild.id)
    return await _done(player, member, icon, f"moved track to `{fmt_time(position_ms)}`")


async def seek_by(guild: discord.Guild, member: discord.Member, delta_ms: int) -> str:
    player = require_player(guild, member)
    return await seek(guild, member, int(player.position + delta_ms))


async def previous(guild: discord.Guild, member: discord.Member) -> str:
    player = require_player(guild, member)
    await require_dj(member, player)
    try:
        track = await player.previous()
    except sonolink.HistoryEmpty:
        raise MusicError("Nothing has been played yet.") from None
    return await _done(player, member, emoji.back, f"went back to [**{track.title}**]({track.uri})", render=False)


async def skip(guild: discord.Guild, member: discord.Member, *, channel: discord.abc.Messageable | None = None) -> str:
    player = require_player(guild, member)
    track = player.current
    if dj.is_dj(member, player) or requester_id(player, track) == member.id:
        confirmation = await _done(player, member, emoji.skip, "skipped the track", render=False)
        await playback.skip_or_stop(player, guild)
        return confirmation
    if member not in dj.listeners(player):
        raise MusicError("Undeafen to vote on a skip.")
    vote = store.skip_vote(guild.id)
    if vote and vote.track.identifier == track.identifier:
        return await vote.add_vote(member)
    await playback.cancel_vote(guild.id)
    vote = playback.VoteSkipView(player.client, player, member)
    # Claim the slot before the send, so a second member skipping in the same breath joins this vote instead of
    # posting a rival card that tallies votes nobody can see.
    store.skip_vote(guild.id, vote, "set")
    target = store.play_ch(guild.id) or channel or member.voice.channel
    play_msg, _ = store.play_msg(guild.id)
    # Only reply to the card when it lives in the channel being posted to, otherwise Discord rejects the reference.
    same_channel = play_msg is not None and play_msg.channel.id == getattr(target, "id", None)
    reference = play_msg.to_reference(fail_if_not_exists=False) if same_channel else None
    try:
        vote.msg = await target.send(view=vote, reference=reference)
    except discord.HTTPException:
        vote.stop()
        store.skip_vote(guild.id, mode="clear")
        raise MusicError("I can't post the skip vote in that channel.") from None
    player.client.dispatch("music_update", guild.id)
    return f"{emoji.skip} Started a vote to skip **{track.title}**."


async def jump(guild: discord.Guild, member: discord.Member, index: int, identifier: str | None = None) -> str:
    player = require_player(guild, member, need_queue=True)
    track = _queued(player, index, identifier)
    await require_dj(member, player)
    await player.skip_to(index)
    return await _done(player, member, emoji.play, f"skipped to [**{track.title}**]({track.uri})", render=False)


async def remove(guild: discord.Guild, member: discord.Member, index: int, identifier: str | None = None) -> str:
    player = require_player(guild, member, need_queue=True)
    track = _queued(player, index, identifier)
    await require_dj(member, player, track=track)
    player.queue.remove_at(index)
    queue_view.nudge_card(player, guild.id)
    return await _done(player, member, emoji.remove, f"removed **{track.title}**", color=config.color.red, render=False)


async def move(guild: discord.Guild, member: discord.Member, index: int, to: int, identifier: str | None = None) -> str:
    player = require_player(guild, member, need_queue=True)
    track = _queued(player, index, identifier)
    if not 0 <= to < len(player.queue):
        raise MusicError(f"Track number must be between `1` and `{len(player.queue)}`.")
    await require_dj(member, player)
    player.queue.move(index, to)
    queue_view.nudge_card(player, guild.id)
    return await _done(player, member, emoji.shuffle, f"moved **{track.title}** to `#{to + 1}`", render=False)


async def clear_queue(guild: discord.Guild, member: discord.Member) -> str:
    player = require_player(guild, member, need_queue=True)
    await require_dj(member, player)
    player.queue.clear()
    return await _done(player, member, emoji.success, "cleared the queue", color=config.color.green)


async def reverse_queue(guild: discord.Guild, member: discord.Member) -> str:
    player = require_player(guild, member, need_queue=True)
    await require_dj(member, player)
    player.queue.reverse()
    queue_view.nudge_card(player, guild.id)
    return await _done(player, member, emoji.shuffle, "reversed the queue", render=False)


async def sort_queue(guild: discord.Guild, member: discord.Member) -> str:
    player = require_player(guild, member, need_queue=True)
    await require_dj(member, player)
    player.queue.sort(key=lambda track: track.length)
    queue_view.nudge_card(player, guild.id)
    return await _done(player, member, emoji.shuffle, "sorted the queue by duration", render=False)


async def dedupe_queue(guild: discord.Guild, member: discord.Member) -> str:
    player = require_player(guild, member, need_queue=True)
    await require_dj(member, player)
    if (removed := player.queue.dedupe()) == 0:
        raise MusicError("No duplicate tracks found in the queue.")
    queue_view.nudge_card(player, guild.id)
    return await _done(player, member, emoji.remove, f"removed `{removed}` duplicate tracks", render=False)


async def remove_requested_by(guild: discord.Guild, member: discord.Member, user_id: int) -> str:
    player = require_player(guild, member, need_queue=True)
    await require_dj(member, player)
    removed = player.queue.remove([user_id], key=lambda track: requester_id(player, track))
    if removed == 0:
        raise MusicError(f"No tracks found requested by <@{user_id}> in the queue.")
    queue_view.nudge_card(player, guild.id)
    return await _done(
        player, member, emoji.remove, f"removed `{removed}` tracks requested by <@{user_id}>", render=False
    )


async def set_volume(guild: discord.Guild, member: discord.Member, volume: int) -> str:
    player = require_player(guild, member)
    await require_dj(member, player)
    low, high = VOLUME_RANGE
    if not low <= volume <= high:
        raise MusicError(f"Volume must be between `{low}` and `{high}`.")
    await player.set_volume(volume)
    return await _done(player, member, emoji.voice, f"changed volume to `{player.volume}%`")


async def set_loop(guild: discord.Guild, member: discord.Member, mode: sonolink.QueueMode) -> str:
    player = require_player(guild, member, need_queue=mode is sonolink.QueueMode.LOOP_ALL)
    await require_dj(member, player)
    player.queue_mode = mode
    return await _done(player, member, loop_emoji(mode), loop_action(mode))


def next_loop(player: SquarePlayer) -> sonolink.QueueMode:
    if player.queue_mode is sonolink.QueueMode.NORMAL:
        return sonolink.QueueMode.LOOP
    if player.queue_mode is sonolink.QueueMode.LOOP and len(player.queue):
        return sonolink.QueueMode.LOOP_ALL
    return sonolink.QueueMode.NORMAL


async def set_shuffle(guild: discord.Guild, member: discord.Member, enabled: bool | None = None) -> str:
    player = require_player(guild, member, need_queue=True)
    await require_dj(member, player)
    if enabled is None or enabled != player.shuffled:
        player.toggle_shuffle()
    return await _done(player, member, emoji.shuffle, f"{'enabled' if player.shuffled else 'disabled'} shuffle")


async def set_autoplay(guild: discord.Guild, member: discord.Member, enabled: bool | None = None) -> str:
    player = require_player(guild, member)
    await require_dj(member, player)
    if enabled is None or enabled != player.autoplay_on:
        await player.toggle_autoplay()
    return await _done(player, member, emoji.autoplay, f"{'enabled' if player.autoplay_on else 'disabled'} autoplay")


async def set_eq(guild: discord.Guild, member: discord.Member, name: str, enabled: bool) -> str:
    player = require_player(guild, member)
    await require_dj(member, player)
    if (preset := EQ_PRESETS.get(name)) is None:
        raise MusicError(f"**{name}** isn't an equalizer.")
    if not enabled:
        if name not in player.presets:
            raise MusicError(f"**{preset.label}** equalizer isn't on.")
        del player.presets[name]
        await player.apply_presets()
        return await _done(player, member, emoji.equalizer, f"removed **{preset.label}** equalizer")
    replaced = [other for other in player.presets if other != name and EQ_PRESETS[other].slot == preset.slot]
    for other in replaced:
        del player.presets[other]
    player.presets[name] = preset.filters
    await player.apply_presets()
    swap = f", replacing **{EQ_PRESETS[replaced[0]].label}**" if replaced else ""
    return await _done(player, member, emoji.equalizer, f"applied **{preset.label}** equalizer{swap}")


async def reset_eq(guild: discord.Guild, member: discord.Member) -> str:
    player = require_player(guild, member)
    await require_dj(member, player)
    player.presets.clear()
    await player.apply_presets()
    return await _done(player, member, emoji.equalizer, "reset equalizer to default settings")


async def play(
    client: Client, guild: discord.Guild, member: discord.Member, query: str, *, channel: discord.abc.Messageable | None
) -> Enqueued:
    # Local: `music/play.py` imports `music/player.py`, which imports this module
    from square.music.play import ensure_connected, resolve_and_enqueue, resolve_query

    bound = request.channel_id(guild.id) is not None
    if bound:
        request.prime(client, guild.id)
    search = asyncio.create_task(resolve_query(client, query))
    player, err, connected_now = await ensure_connected(client, member)
    if err or player is None:
        search.cancel()
        raise MusicError(_without_emoji(err or "I couldn't join your voice channel."))
    # Not keyed on `connected_now`: a 24/7 bot is already connected when a session starts
    claimed = not bound and store.play_ch(guild.id) is None
    if claimed:
        store.play_ch(guild.id, channel or member.voice.channel, "set")
    try:
        result = await resolve_and_enqueue(client, player, search, member.id)
    except Exception:
        await _abandon_play(player, guild, connected_now, claimed)
        raise
    if not result.ok:
        await _abandon_play(player, guild, connected_now, claimed)
        raise MusicError(_without_emoji(result.content))
    if not result.started and request.setup_mode(guild.id):
        playback.schedule_render(client, guild.id)
    return result


def _without_emoji(line: str) -> str:
    text = split_log_text(line)[1]
    return text[:1].upper() + text[1:]


async def _abandon_play(player: SquarePlayer, guild: discord.Guild, connected_now: bool, claimed: bool) -> None:
    if connected_now:
        await playback.stop_player(player, guild)
    elif claimed and not player.current:
        store.play_ch(guild.id, None, "set")


async def replay(guild: discord.Guild, member: discord.Member, index: int, identifier: str | None = None) -> str:
    player = require_player(guild, member)
    played = history_tracks(player)
    if not 0 <= index < len(played):
        raise MusicError("Nothing has been played yet." if not played else "That track isn't in the history anymore.")
    track = played[index]
    if identifier is not None and track.identifier != identifier:
        raise QueueChanged("The history changed. Have another look and try again.")
    player.queue.put(tag_requester(player.client, track, member.id))
    queue_view.nudge_card(player, guild.id)
    return await _done(player, member, emoji.reload, f"queued [**{track.title}**]({track.uri}) again", render=False)
