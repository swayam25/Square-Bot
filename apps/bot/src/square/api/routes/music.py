"""
The music player: what's playing, and every control the Discord card and commands have.

Any member of the server may look. Each control then applies the Discord rules through `square.music.controls`:
being in the bot's voice channel, DJ mode and roles, requester rights and skip votes.
"""

import discord
import msgspec
import sonolink
from collections.abc import Awaitable
from litestar import Request, Response, Router, get, post
from litestar.di import Provide
from litestar.exceptions import ServiceUnavailableException
from litestar.openapi import ResponseSpec
from litestar.params import Parameter
from square.api import resolve
from square.api.auth import provide_member, provide_member_guild
from square.api.schemas import (
    Loop,
    PlayerState,
    Problem,
    QueueState,
    Schema,
    SearchResults,
    Snowflake,
    Track,
    history_out,
    live_player,
    player_out,
    queue_out,
    search_out,
)
from square.core import Client
from square.music import controls
from square.music.controls import VOLUME_RANGE
from square.music.errors import MusicError, QueueChanged
from square.music.filters import EQ_PRESETS
from square.music.play import clean_query, is_link, search_tracks
from square.music.utils import music_log, split_log_text
from typing import Annotated

REFUSED = {
    409: ResponseSpec(
        data_container=Problem, description="The queue changed since it was read", generate_examples=False
    ),
    422: ResponseSpec(data_container=Problem, description="The bot refused the control", generate_examples=False),
}
_LOOP: dict[Loop, sonolink.QueueMode] = {
    "off": sonolink.QueueMode.NORMAL,
    "track": sonolink.QueueMode.LOOP,
    "queue": sonolink.QueueMode.LOOP_ALL,
}

Index = Annotated[int, msgspec.Meta(ge=0)]
SEARCH_LIMIT = 10


class Done(Schema):
    message: str  # The same confirmation a slash command shows, readable outside Discord


class EqPreset(Schema):
    name: str
    label: str


class Paused(Schema):
    paused: bool


class Seek(Schema):
    position_ms: Annotated[int, msgspec.Meta(ge=0)]


class Volume(Schema):
    volume: Annotated[int, msgspec.Meta(ge=VOLUME_RANGE[0], le=VOLUME_RANGE[1])]


class LoopMode(Schema):
    mode: Loop


class Toggle(Schema):
    enabled: bool


class EqToggle(Schema):
    preset: str
    enabled: bool


class QueuedTrack(Schema):
    """A queued track, by its position and the identifier the dashboard saw there, so a stale view can't hit another."""

    index: Index
    identifier: str


class QueueMove(QueuedTrack):
    to: Index


class PlayQuery(Schema):
    query: Annotated[str, msgspec.Meta(min_length=1, max_length=500)]  # A track name, or a track or playlist link


class Requester(Schema):
    user_id: Snowflake


async def _done(guild: discord.Guild, action: Awaitable[str]) -> Done:
    return Done(message=resolve.plain(guild, await action))


@get("/player", summary="What's playing right now. `/live` pushes the same shape as it changes")
async def music_player(client: Client, guild: discord.Guild) -> PlayerState:
    return player_out(client, guild)


@get("/queue", summary="The upcoming tracks. `/live` pushes the same shape as it changes")
async def music_queue(client: Client, guild: discord.Guild) -> QueueState:
    return queue_out(client, guild)


@get("/history", summary="Tracks played this session, newest first")
async def music_history(client: Client, guild: discord.Guild) -> list[Track]:
    return history_out(live_player(client, guild.id))


@get("/search", summary="Search for tracks, or see what a link points to")
async def search_music(
    client: Client,
    guild: discord.Guild,  # Asked for so membership is checked
    q: Annotated[str, Parameter(min_length=1, max_length=500, description="A track name, or a track or playlist link")],
) -> SearchResults:
    link = is_link(q)
    # No retries across nodes: this runs as the member types, so a slow node should cost one attempt, not all of them
    result = await search_tracks(client, clean_query(q) if link else q, retry=False)
    if result is None or result.is_error():
        raise ServiceUnavailableException("Search isn't available right now")
    if result.is_empty() or result.result is None:
        return SearchResults(playlist=None, tracks=[])
    return search_out(result.result, 1 if link else SEARCH_LIMIT)


@post(
    "/play",
    summary="Search for a query and queue it, joining the member's voice channel",
    status_code=200,
    responses=REFUSED,
)
async def play_query(client: Client, guild: discord.Guild, member: discord.Member, data: PlayQuery) -> Done:
    result = await controls.play(client, guild, member, data.query, channel=None)
    icon, text = split_log_text(result.content)
    await music_log(guild.id, f"{icon} {member.mention} {text}".strip(), color=result.color)
    return Done(message=resolve.plain(guild, result.content))


@post("/history/replay", summary="Queue a played track again", status_code=200, responses=REFUSED)
async def replay_track(guild: discord.Guild, member: discord.Member, data: QueuedTrack) -> Done:
    return await _done(guild, controls.replay(guild, member, data.index, data.identifier))


@get("/eq-presets", summary="The equalizer presets, in the order the dashboard should list them")
async def eq_presets(guild: discord.Guild) -> list[EqPreset]:  # Asked for so membership is checked
    return [EqPreset(name=name, label=preset.label) for name, preset in EQ_PRESETS.items()]


@post("/pause", summary="Pause or resume", status_code=200, responses=REFUSED)
async def pause_player(guild: discord.Guild, member: discord.Member, data: Paused) -> Done:
    return await _done(guild, controls.set_paused(guild, member, data.paused))


@post("/stop", summary="Stop the player", status_code=200, responses=REFUSED)
async def stop_player(guild: discord.Guild, member: discord.Member) -> Done:
    return await _done(guild, controls.stop(guild, member))


@post("/skip", summary="Skip, or vote to skip for members who aren't DJs", status_code=200, responses=REFUSED)
async def skip_track(guild: discord.Guild, member: discord.Member) -> Done:
    return await _done(guild, controls.skip(guild, member))


@post("/previous", summary="Go back to the last track", status_code=200, responses=REFUSED)
async def previous_track(guild: discord.Guild, member: discord.Member) -> Done:
    return await _done(guild, controls.previous(guild, member))


@post("/seek", summary="Jump to a position in the track", status_code=200, responses=REFUSED)
async def seek_track(guild: discord.Guild, member: discord.Member, data: Seek) -> Done:
    return await _done(guild, controls.seek(guild, member, data.position_ms))


@post("/volume", summary="Set the volume", status_code=200, responses=REFUSED)
async def set_volume(guild: discord.Guild, member: discord.Member, data: Volume) -> Done:
    return await _done(guild, controls.set_volume(guild, member, data.volume))


@post("/loop", summary="Loop nothing, the track or the queue", status_code=200, responses=REFUSED)
async def set_loop(guild: discord.Guild, member: discord.Member, data: LoopMode) -> Done:
    return await _done(guild, controls.set_loop(guild, member, _LOOP[data.mode]))


@post("/shuffle", summary="Turn shuffle on or off", status_code=200, responses=REFUSED)
async def set_shuffle(guild: discord.Guild, member: discord.Member, data: Toggle) -> Done:
    return await _done(guild, controls.set_shuffle(guild, member, data.enabled))


@post("/autoplay", summary="Turn autoplay on or off", status_code=200, responses=REFUSED)
async def set_autoplay(guild: discord.Guild, member: discord.Member, data: Toggle) -> Done:
    return await _done(guild, controls.set_autoplay(guild, member, data.enabled))


@post("/eq", summary="Turn an equalizer preset on or off", status_code=200, responses=REFUSED)
async def set_eq(guild: discord.Guild, member: discord.Member, data: EqToggle) -> Done:
    return await _done(guild, controls.set_eq(guild, member, data.preset, data.enabled))


@post("/eq/reset", summary="Turn every equalizer preset off", status_code=200, responses=REFUSED)
async def reset_eq(guild: discord.Guild, member: discord.Member) -> Done:
    return await _done(guild, controls.reset_eq(guild, member))


@post("/queue/jump", summary="Play a queued track now", status_code=200, responses=REFUSED)
async def jump_to_track(guild: discord.Guild, member: discord.Member, data: QueuedTrack) -> Done:
    return await _done(guild, controls.jump(guild, member, data.index, data.identifier))


@post("/queue/remove", summary="Remove a queued track", status_code=200, responses=REFUSED)
async def remove_track(guild: discord.Guild, member: discord.Member, data: QueuedTrack) -> Done:
    return await _done(guild, controls.remove(guild, member, data.index, data.identifier))


@post("/queue/move", summary="Move a queued track", status_code=200, responses=REFUSED)
async def move_track(guild: discord.Guild, member: discord.Member, data: QueueMove) -> Done:
    return await _done(guild, controls.move(guild, member, data.index, data.to, data.identifier))


@post("/queue/clear", summary="Clear the queue", status_code=200, responses=REFUSED)
async def clear_queue(guild: discord.Guild, member: discord.Member) -> Done:
    return await _done(guild, controls.clear_queue(guild, member))


@post("/queue/reverse", summary="Reverse the queue", status_code=200, responses=REFUSED)
async def reverse_queue(guild: discord.Guild, member: discord.Member) -> Done:
    return await _done(guild, controls.reverse_queue(guild, member))


@post("/queue/sort", summary="Sort the queue, shortest first", status_code=200, responses=REFUSED)
async def sort_queue(guild: discord.Guild, member: discord.Member) -> Done:
    return await _done(guild, controls.sort_queue(guild, member))


@post("/queue/dedupe", summary="Remove duplicate tracks from the queue", status_code=200, responses=REFUSED)
async def dedupe_queue(guild: discord.Guild, member: discord.Member) -> Done:
    return await _done(guild, controls.dedupe_queue(guild, member))


@post("/queue/remove-requester", summary="Remove every track one member queued", status_code=200, responses=REFUSED)
async def remove_requester_tracks(guild: discord.Guild, member: discord.Member, data: Requester) -> Done:
    return await _done(guild, controls.remove_requested_by(guild, member, int(data.user_id)))


def _refused(request: Request, exc: MusicError) -> Response[Problem]:
    client: Client | None = request.app.state.client
    guild = client.get_guild(int(request.path_params["guild_id"])) if client else None
    detail = resolve.plain(guild, str(exc)) if guild else str(exc)
    return Response(Problem(detail=detail), status_code=409 if isinstance(exc, QueueChanged) else 422)


router = Router(
    "/guilds/{guild_id:str}/music",
    tags=["Music"],
    dependencies={
        "guild": Provide(provide_member_guild, sync_to_thread=False),
        "member": Provide(provide_member, sync_to_thread=False),
    },
    exception_handlers={MusicError: _refused},
    route_handlers=[
        music_player,
        music_queue,
        music_history,
        search_music,
        play_query,
        replay_track,
        eq_presets,
        pause_player,
        stop_player,
        skip_track,
        previous_track,
        seek_track,
        set_volume,
        set_loop,
        set_shuffle,
        set_autoplay,
        set_eq,
        reset_eq,
        jump_to_track,
        remove_track,
        move_track,
        clear_queue,
        reverse_queue,
        sort_queue,
        dedupe_queue,
        remove_requester_tracks,
    ],
)
