import asyncio
import datetime
import discord
import sonolink
import time
from core import Client
from core.view import DesignerView
from discord import ui
from music import dj, lyrics, request, store
from music.core import SquarePlayer, drop_session_lock, fmt_time, get_player, requester_id
from music.queue import QueueListView
from music.utils import get_source, music_interaction_check, music_log, reply, split_log_text
from pathlib import Path
from typing import Literal
from utils import config
from utils.emoji import emoji

_render_locks: dict[int, asyncio.Lock] = {}

# ~3.3 edits/5s worst case, inside Discord's ~5 edits/5s per-channel bucket.
_LYRICS_MIN_EDIT_INTERVAL = 1.5
_LYRICS_MAX_SLEEP = 5.0
# Lookahead, so an edit lands as the line is sung rather than after it.
_LYRICS_LEAD_MS = 450
_BAR_REFRESH_INTERVAL = 10.0

_SEEK_STEP_MS = 10_000
_ENQUEUE_RENDER_DELAY = 1.0
RELOCATE_DELAY = 2.0
_VOTE_TIMEOUT = 60.0
_VOTE_RESULT_LINGER = 5.0

# Each track costs three of the message's 40 components.
_UP_NEXT_LIMIT = 4
# Optional; the idle card falls back to text without it.
IDLE_GIF = Path("assets/idle.gif")


def idle_attachment() -> dict:
    """
    Returns the send kwargs that attach the idle artwork, or nothing when the asset is missing.

    A components v2 message can only show a local file through a component pointing at
    ``attachment://``, so the file has to ride along with the message that references it.
    """
    if not IDLE_GIF.is_file():
        return {}
    return {"file": discord.File(IDLE_GIF, filename=IDLE_GIF.name)}


def card_attachments(live: bool) -> dict:
    """
    Returns the edit kwargs that put the card's attachments into the shape the given state needs.

    Passing ``attachments=[]`` alongside a file replaces the set outright, which is what lets one
    edit carry the card between its resting and playing shapes instead of reposting it.

    Args:
        live (bool): Whether the card is being painted with a track on it.
    """
    kwargs: dict = {"attachments": []}
    if not live:
        kwargs |= idle_attachment()
    return kwargs


def _get_render_lock(guild_id: int) -> asyncio.Lock:
    """
    Returns the render lock for a guild, creating it on first access.

    Args:
        guild_id (int): The guild ID to retrieve the lock for.

    Returns:
        :class:`asyncio.Lock`: The lock associated with the guild.
    """
    if guild_id not in _render_locks:
        _render_locks[guild_id] = asyncio.Lock()
    return _render_locks[guild_id]


async def render_player(client: Client, guild_id: int, *, force_new: bool = False, wait: bool = False) -> None:
    """
    Renders the single persistent player message.

    Edits the player in place while it is still the latest message, otherwise deletes the stale player and posts a fresh one at the bottom of the channel.
    Skips silently if a render is already in progress for this guild, unless ``wait`` says otherwise.

    With nothing playing this renders the resting card for a bound request channel, and does
    nothing at all anywhere else.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to render the player for.
        force_new (bool): Always send a new player message instead of editing.
        wait (bool): Queue behind an in-flight render rather than dropping this one. A dropped
            lyrics frame is invisible, but a dropped teardown repaint freezes the card for good.
    """
    lock = _get_render_lock(guild_id)
    if lock.locked() and not wait:
        return
    player = get_player(client, guild_id)
    if not (player and player.connected and player.current) and not request.setup_mode(guild_id):
        return
    async with lock:
        # Everything below is read after the wait, not before it. A `wait=True` caller can sit on
        # this lock while playback stops, and an attachment set that disagrees with the shape the
        # view actually built is a 400, not a `NotFound` the send path below would absorb.
        channel = store.play_ch(guild_id)
        if not channel:
            return
        view = MusicView(client, guild_id)
        live = view.live
        bound = request.setup_mode(guild_id)
        if not live and not bound:
            return
        # A bound channel's card is fixed in place, so it is only ever edited.
        force_new = force_new and not bound
        state: Literal["idle", "live"] = "live" if live else "idle"
        play_msg, _ = store.play_msg(guild_id)
        # `/set music` mid-session leaves the free-form card behind in another channel. It cannot be
        # edited into the bound one, so it is deleted and replaced below instead.
        stale = play_msg is not None and play_msg.channel.id != channel.id
        if play_msg and not force_new and not stale:
            try:
                if store.card_state(guild_id) != state:
                    if isinstance(play_msg, discord.PartialMessage):
                        # Only a full message can change its attachments.
                        play_msg = await channel.fetch_message(play_msg.id)
                    edited = await play_msg.edit(view=view, **card_attachments(live))
                else:
                    edited = await play_msg.edit(view=view)
                store.play_msg(guild_id, edited or play_msg, view, "set")
                store.card_state(guild_id, state, "set")
                return
            except discord.NotFound:
                play_msg = None
        # Send new and delete old concurrently - both API calls happen in parallel
        coros: list = [channel.send(view=view, **(idle_attachment() if not live else {}))]
        if play_msg:
            coros.append(play_msg.delete())
        results = await asyncio.gather(*coros, return_exceptions=True)
        new_msg = results[0]
        if isinstance(new_msg, discord.Forbidden):
            store.play_msg(guild_id, mode="clear")
            store.card_state(guild_id, None, "set")
            return
        if isinstance(new_msg, BaseException):
            return
        store.play_msg(guild_id, new_msg, view, "set")
        store.card_state(guild_id, state, "set")
        store.chat_weight(guild_id, mode="clear")
        if request.setup_mode(guild_id):
            await request.bind_message(guild_id, new_msg.id)


def schedule_render(
    client: Client,
    guild_id: int,
    *,
    delay: float = _ENQUEUE_RENDER_DELAY,
    force_new: bool = False,
) -> None:
    """
    Renders the card after a short pause, coalescing a burst of changes into one edit.

    A render already waiting absorbs the rest, so five requests in a row cost one edit.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to render the player for.
        delay (float): Seconds to wait before rendering.
        force_new (bool): Send a new card rather than editing the existing one.
    """
    pending = store.render_task(guild_id)
    if pending and not pending.done():
        return

    async def _later() -> None:
        await asyncio.sleep(delay)
        await render_player(client, guild_id, force_new=force_new)

    store.render_task(guild_id, asyncio.create_task(_later()), "set")


async def repaint_deleted_card(client: Client, guild_id: int, deleted_ids: set[int]) -> None:
    """
    Reposts the card when it is deleted out from under a guild that still needs one.

    The lyrics ticker repaints a playing card every few seconds and would repost it by itself, but
    it holds still while paused and never runs at all for a stream, and a resting bound card has no
    ticker behind it either. Those are the cases that would otherwise sit there cardless.

    Waiting on the render lock is what tells a mod's delete apart from the bot's own: a relocation
    deletes the card it has just replaced, and by the time the lock frees the store already holds
    the replacement, so the ID no longer matches.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild the deleted messages belong to.
        deleted_ids (set[int]): The message IDs that were deleted.
    """
    play_msg, _ = store.play_msg(guild_id)
    if play_msg is None or play_msg.id not in deleted_ids:
        return  # Checked before taking a lock, since this runs for every delete in every guild.
    async with _get_render_lock(guild_id):
        play_msg, _ = store.play_msg(guild_id)
        if play_msg is None or play_msg.id not in deleted_ids:
            return
        store.play_msg(guild_id, mode="clear")
        store.card_state(guild_id, None, "set")
    await render_player(client, guild_id, wait=True)


def start_lyrics(client: Client, guild_id: int) -> None:
    """
    Starts (or restarts) the synced-lyrics updater task for a guild.

    Cancels any previous updater so only one loop runs per guild.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to update lyrics for.
    """
    task = store.lyrics_task(guild_id)
    if task:
        task.cancel()
    store.lyrics_task(guild_id, asyncio.create_task(_lyrics_loop(client, guild_id)), "set")


async def _lyrics_loop(client: Client, guild_id: int) -> None:
    """
    Re-renders the player card whenever the active lyric line changes, keeping the progress bar fresh in between.

    Fetches lyrics once per track (cached in the store), then sleeps until the next line boundary.
    Edits are throttled to one per :data:`_LYRICS_MIN_EDIT_INTERVAL` seconds to stay clear of Discord rate limits, and nothing is edited while paused or when the line hasn't changed.
    Tracks without lyrics (and instrumental gaps) still get a bar-only refresh every :data:`_BAR_REFRESH_INTERVAL` seconds.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to update lyrics for.
    """
    player = get_player(client, guild_id)
    if not player or not player.current or player.current.is_stream:
        return
    track = player.current
    cached = store.lyrics(guild_id)
    if cached and cached[0] == track.identifier:
        lines = cached[1]
    else:
        lines = await lyrics.fetch(track)
        store.lyrics(guild_id, track.identifier, lines, "set")
    last_idx: int | None = None
    last_edit = 0.0
    while True:
        current = player.current
        if not player.connected or not current or current.identifier != track.identifier:
            return
        if not lines:
            # No lyrics found: keep the progress bar moving with a slow tick.
            if not player.paused:
                await render_player(client, guild_id)
            await asyncio.sleep(_BAR_REFRESH_INTERVAL)
            continue
        idx, *_ = lyrics.window(lines, player.position + _LYRICS_LEAD_MS)
        if idx != last_idx:
            wait = _LYRICS_MIN_EDIT_INTERVAL - (time.monotonic() - last_edit)
            if wait > 0:
                await asyncio.sleep(wait)
                continue
            await render_player(client, guild_id)
            last_idx = idx
            last_edit = time.monotonic()
        elif not player.paused and time.monotonic() - last_edit >= _BAR_REFRESH_INTERVAL:
            await render_player(client, guild_id)
            last_edit = time.monotonic()
        next_ts = lines[idx + 1][0] if idx + 1 < len(lines) else None
        delay = (next_ts - _LYRICS_LEAD_MS - player.position) / 1000 if next_ts is not None else _LYRICS_MAX_SLEEP
        await asyncio.sleep(min(max(delay, 0.25), _LYRICS_MAX_SLEEP))


def _cancel_tasks(guild_id: int) -> None:
    """
    Stops the guild's scheduled work: the open skip vote, the lyrics ticker, and any pending relocation.

    A task is never cancelled from within itself, so the caller's own cleanup can finish.
    """
    vote = store.skip_vote(guild_id)
    if vote:
        vote.stop()  # Cancels its expiry task; the card itself is only removed on the async paths.
    for task_fn in (store.lyrics_task, store.render_task):
        task = task_fn(guild_id)
        if task and task is not asyncio.current_task():
            task.cancel()


def cleanup_guild(client: Client, guild_id: int) -> None:
    """
    Releases all per-guild in-memory state: locks, scheduled tasks (lyrics, relocation), and every store key.

    Cancels tasks first, then flushes the store so the guild entry is dropped entirely. A bound
    guild keeps its card, so its binding is primed straight back into the store the flush emptied.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to release.
    """
    lock = _render_locks.get(guild_id)
    if lock is not None and not lock.locked():
        del _render_locks[guild_id]  # Dropping a held one lets the next render run beside it.
    drop_session_lock(guild_id)
    _cancel_tasks(guild_id)
    state = store.card_state(guild_id)
    store.flush_store(guild_id)
    if request.prime(client, guild_id):  # No-op unless the guild has a request channel bound.
        # The card outlived the flush, in whatever shape the last render left it. Forgetting that
        # costs the next render a fetch and an attachment rewrite on an already-correct card.
        store.card_state(guild_id, state, "set")


async def clear_player(client: Client, guild_id: int) -> None:
    """
    Retires the persistent player message and clears all per-guild state.

    A bound channel's card is repainted to its resting state rather than deleted; it is that
    channel's only permanent message. Everywhere else the card is removed outright.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild whose player message should be retired.
    """
    await cancel_vote(guild_id)
    # Before the flush, which drops the channel and message the repaint needs.
    _cancel_tasks(guild_id)
    if request.setup_mode(guild_id):
        await render_player(client, guild_id, wait=True)
    else:
        play_msg, _ = store.play_msg(guild_id)
        if play_msg:
            try:
                await play_msg.delete()
            except discord.HTTPException:
                pass
    cleanup_guild(client, guild_id)


async def stop_player(player: SquarePlayer, guild: discord.Guild) -> None:
    """
    Clears the VC status, disconnects (destroying the lavalink-side player), and deletes the player card.

    Safe to call repeatedly: the disconnect fires :meth:`on_sonolink_player_disconnect`, which funnels back
    here, so a per-player guard makes every path after the first a no-op.

    Args:
        player (:class:`SquarePlayer`): The active player to stop.
        guild (:class:`Guild`): The guild to disconnect from.
    """
    if getattr(player, "_square_stopped", False):
        return
    player._square_stopped = True
    if guild.me.voice and guild.me.voice.channel:
        try:
            await guild.me.voice.channel.set_status(status=None)
        except discord.HTTPException:
            pass
    try:
        await player.disconnect(force=True)
    except Exception:
        pass  # Node may be unreachable; still clean up locally
    await clear_player(player.client, guild.id)


async def release_guild(client: Client, guild_id: int) -> None:
    """
    Tears a guild's session down once it has lost its request channel.

    Playback is stopped rather than handed back to the free-form player. The card lived in a
    channel that is being deleted, and guessing a new home for it would drop a player card into a
    channel nobody asked for. Callers unbind first, so the teardown takes the free-mode path and
    the database is already clear by the time this runs.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to release.
    """
    player = get_player(client, guild_id)
    guild = client.get_guild(guild_id)
    if player and guild:
        await stop_player(player, guild)
    else:
        cleanup_guild(client, guild_id)


async def skip_or_stop(player: SquarePlayer, guild: discord.Guild) -> None:
    """Skips to the next track, tearing the player down when nothing is left to play."""
    try:
        await player.skip()
    except sonolink.QueueEmpty, sonolink.AutoPlaySeedMissing:
        await stop_player(player, guild)


async def cancel_vote(guild_id: int) -> None:
    """Closes the guild's open skip vote and removes its message, for when the track it targeted is gone."""
    vote = store.skip_vote(guild_id)
    if not vote:
        return
    vote.stop()
    store.skip_vote(guild_id, mode="clear")
    await vote.discard()


async def request_skip(source: discord.ApplicationContext | discord.Interaction, player: SquarePlayer) -> None:
    """
    Skips the track for a DJ or the member who requested it, and opens a listener vote for everyone else.

    A second member asking to skip joins the open vote instead of starting a competing one.

    Args:
        source (:class:`ApplicationContext` | :class:`Interaction`): The invoking command or button press.
        player (:class:`SquarePlayer`): The active player for the guild.
    """
    is_command = isinstance(source, discord.ApplicationContext)
    member = source.author if is_command else source.user
    guild = source.guild
    track = player.current
    interaction = source.interaction if is_command else source
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=is_command)
    if await dj.is_dj(member, player) or requester_id(player, track) == member.id:
        if is_command:
            await reply(source, f"{emoji.skip} Skipped the track.")
        await music_log(guild.id, f"{emoji.skip} {member.mention} skipped the track.")
        await skip_or_stop(player, guild)
        return
    if member not in dj.listeners(player):
        await reply(source, f"{emoji.error} Undeafen to vote on a skip.", color=config.color.red)
        return
    vote = store.skip_vote(guild.id)
    if vote and vote.track.identifier == track.identifier:
        await vote.add_vote(source, member)
        return
    await cancel_vote(guild.id)
    vote = VoteSkipView(source.bot if is_command else source.client, player, member)
    # Claim the slot before the send, so a second member skipping in the same breath joins this vote instead of
    # posting a rival card that tallies votes nobody can see.
    store.skip_vote(guild.id, vote, "set")
    channel = store.play_ch(guild.id) or source.channel
    play_msg, _ = store.play_msg(guild.id)
    # Only reply to the card when it lives in the channel being posted to, otherwise Discord rejects the reference.
    same_channel = play_msg is not None and play_msg.channel.id == channel.id
    reference = play_msg.to_reference(fail_if_not_exists=False) if same_channel else None
    try:
        vote.msg = await channel.send(view=vote, reference=reference)
    except discord.HTTPException:
        # No card, no vote: drop it rather than leave a slot and an expiry task nothing can ever resolve.
        vote.stop()
        store.skip_vote(guild.id, mode="clear")
        await reply(source, f"{emoji.error} I can't post the skip vote in that channel.", color=config.color.red)
        return
    # A button press was acked silently, but a command's deferred ephemeral needs filling in or it hangs on "thinking".
    if is_command:
        await reply(source, f"{emoji.skip} Started a vote to skip **{track.title}**.")


async def slash_log(
    ctx: discord.ApplicationContext,
    content: str,
    *,
    color: int | None = None,
    render: bool = True,
) -> None:
    """
    Acknowledges a state-changing slash command ephemerally and logs it publicly.

    Sends an ephemeral confirmation to the invoker, optionally re-renders the player card, and posts a public log line with the user mention prepended.

    Args:
        ctx (:class:`ApplicationContext`): The slash command context.
        content (str): The confirmation/log message (leading emoji is stripped for the log line).
        color (int | None): Optional accent color applied to both the reply and the log.
        render (bool): Whether to re-render the player card after the action.
    """
    await reply(ctx, content, color=color)
    if render:
        await render_player(ctx.bot, ctx.guild.id)
    log_emoji, text = split_log_text(content)
    await music_log(ctx.guild.id, f"{log_emoji} {ctx.author.mention} {text}".strip(), color=color)


class MusicContainer(ui.Container):
    """
    Renders the currently playing track as a Discord container component.

    Displays the track title (linked), artist, requester mention, and a position/duration progress bar (fully filled with a LIVE badge for streams).
    When synced lyrics are cached for the current track, a previous/current/next line window is appended with the current line in bold.

    Args:
        player (:class:`SquarePlayer`): The active player with a current track set.
    """

    def __init__(self, player: SquarePlayer):
        super().__init__()
        rid = requester_id(player, player.current)
        info = (
            f"{emoji.user} **Requested By**: {f'<@{rid}>' if rid else 'Unknown'}\n"
            f"{emoji.mic} **Artist**: {get_source(player.current.source_name)['emoji']} {player.current.author}"
        )
        self.items = [
            ui.Section(
                ui.TextDisplay(f"## [{player.current.title}]({player.current.uri})"),
                ui.TextDisplay(info),
                accessory=ui.Thumbnail(url=player.current.artwork),
            )
        ]
        lyrics_text = self._lyrics_text(player)
        if lyrics_text:
            self.items.append(ui.TextDisplay(lyrics_text))
        self.items.append(ui.TextDisplay(self._progress_bar(player)))

    @staticmethod
    def _progress_bar(player: SquarePlayer, bar_length: int = 10) -> str:
        """Builds the position/duration progress bar line. Streams get a fully filled bar with a LIVE badge."""
        if player.current.is_stream:
            return f"{emoji.live} **LIVE** {emoji.filled_bar * bar_length}"
        filled = min(bar_length, int(bar_length * player.position // float(player.current.length)))
        return (
            f"`{fmt_time(player.position)}` "
            f"{emoji.filled_bar * filled}{emoji.empty_bar * (bar_length - filled)} "
            f"`{fmt_time(player.current.length)}`"
        )

    @staticmethod
    def _lyrics_text(player: SquarePlayer) -> str | None:
        """
        Builds the three-line synced lyrics block for the current playback position.

        Returns None when no lyrics are cached for the current track.
        """
        cached = store.lyrics(player.guild.id)
        if not cached or cached[0] != player.current.identifier or not cached[1]:
            return None
        _, prev, current, upcoming = lyrics.window(cached[1], player.position + _LYRICS_LEAD_MS)

        def fmt(line: str) -> str:
            return discord.utils.escape_markdown(line) if line else "♪"

        return f"-# {fmt(prev)}\n**{fmt(current)}**\n-# {fmt(upcoming)}"


class UpNextContainer(ui.Container):
    """
    Renders the next few queued tracks, each with a button that jumps straight to it.

    Stays on the card when the queue is empty, so it doesn't grow and shrink as the queue drains.

    Args:
        player (:class:`SquarePlayer`): The active player.
        view (:class:`MusicView`): The card this container belongs to, which owns the callbacks.
    """

    def __init__(self, player: SquarePlayer, view: MusicView):
        super().__init__()
        # Indexed, not `queue.tracks`: that property copies the whole queue, and this runs on every
        # paint, which the lyrics ticker drives every couple of seconds.
        queue = player.queue
        total = len(queue)
        self.add_item(ui.TextDisplay(f"### {emoji.skip} Up Next"))
        if total:
            for index in range(min(total, _UP_NEXT_LIMIT)):
                track = queue[index]
                btn = ui.Button(
                    emoji=emoji.play_white,
                    style=discord.ButtonStyle.grey,
                    custom_id=f"up_next_play_{index}",
                )
                btn.callback = lambda i, ident=track.identifier: view.play_now_callback(i, ident)
                self.add_item(
                    ui.Section(
                        ui.TextDisplay(
                            f"`{index + 1}.` [**{track.title}** by **{track.author}**]({track.uri}) "
                            f"[`{fmt_time(track.length)}`]"
                        ),
                        accessory=btn,
                    )
                )
            # duration_until ignores loop mode, unlike total_duration, which reports inf while looping.
            runtime = fmt_time(queue.duration_until(total))
            remaining = total - _UP_NEXT_LIMIT
            self.add_item(ui.TextDisplay(f"-# {f'+{remaining} more • ' if remaining > 0 else ''}`{runtime}` total"))
        elif player.autoplay is sonolink.AutoPlayMode.ENABLED:
            self.add_item(ui.TextDisplay(f"-# {emoji.autoplay} Nothing queued. Autoplay takes over when this ends."))
        else:
            self.add_item(ui.TextDisplay("-# Nothing up next. Queue something to keep the music going."))


class IdleContainer(ui.Container):
    """
    Renders the resting card shown when nothing is playing.

    Only bound request channels see this; a free-form card is deleted on teardown instead.

    Args:
        guild_id (int): The guild the card belongs to, used to word the hint.
    """

    def __init__(self, guild_id: int):
        super().__init__()
        self.add_item(ui.TextDisplay("## Nothing is being played"))
        if IDLE_GIF.is_file():
            self.add_item(ui.MediaGallery(discord.MediaGalleryItem(url=f"attachment://{IDLE_GIF.name}")))
        if request.setup_mode(guild_id):
            hint = "Send a track name or a link in this channel to queue it."
        else:
            hint = "Run `/play` to queue a track."
        self.add_item(ui.TextDisplay(hint))


class MusicView(DesignerView):
    """
    Persistent player card: the track, the next few queued tracks, and the transport controls.

    With nothing playing it falls back to an :class:`IdleContainer` and disables every control,
    which is the resting state of a bound request channel's card.
    The view has no timeout and re-checks interaction eligibility on every button press.

    Args:
        client (:class:`Client`): The bot client used to fetch the player and send follow-up logs.
        guild_id (int): The guild this player card belongs to.
    """

    def __init__(self, client: Client, guild_id: int):
        super().__init__(timeout=None)
        self.client = client
        self.guild_id = guild_id
        self.player = get_player(client, guild_id)
        self.interaction_check = lambda interaction: music_interaction_check(
            player=self.player, interaction=interaction, view=self
        )
        self.build()

    @property
    def live(self) -> bool:
        """Whether there is a player with a track on it, as opposed to a resting card."""
        return bool(self.player and self.player.connected and self.player.current)

    def build(self):
        self.clear_items()
        if self.live:
            self.add_item(MusicContainer(self.player))
            if request.setup_mode(self.guild_id):
                self.add_item(UpNextContainer(self.player, self))
        else:
            self.add_item(IdleContainer(self.guild_id))
        for buttons in self._rows():
            self.add_item(row := ui.ActionRow())
            for btn_emoji, action, disabled in buttons:
                btn = ui.Button(
                    emoji=btn_emoji,
                    custom_id=action,
                    style=discord.ButtonStyle.grey,
                    disabled=disabled or not self.live,
                )
                btn.callback = getattr(self, f"{action}_callback")
                row.add_item(btn)

    def _rows(self) -> list[list[tuple[str, str, bool]]]:
        """Builds the transport button table, falling back to resting states when nothing is playing."""
        player = self.player if self.live else None
        is_stream = bool(player and player.current.is_stream)
        queue_mode = player.queue_mode if player else sonolink.QueueMode.NORMAL
        shuffled = bool(player and player.queue.shuffle_mode is sonolink.ShuffleMode.PERSISTENT)
        autoplay_on = bool(player and player.autoplay is sonolink.AutoPlayMode.ENABLED)
        return [
            [
                (emoji.back_white, "previous", not (player and player.history)),
                (emoji.rewind10s_white, "rewind", is_stream),
                (emoji.play_white if player and player.paused else emoji.pause_white, "pause", False),
                (emoji.forward10s_white, "forward", is_stream),
                (emoji.skip_white, "skip", False),
            ],
            [
                (
                    emoji.loop_white
                    if queue_mode is sonolink.QueueMode.NORMAL
                    else emoji.loop_one
                    if queue_mode is sonolink.QueueMode.LOOP
                    else emoji.loop,
                    "loop",
                    False,
                ),
                (emoji.shuffle if shuffled else emoji.shuffle_white, "shuffle", False),
                (emoji.stop_white, "stop", False),
                (emoji.autoplay if autoplay_on else emoji.autoplay_white, "autoplay", False),
                (emoji.queue_white, "queue", False),
            ],
        ]

    async def pause_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await dj.require_dj(interaction, self.player):
            return
        if self.player.paused:
            await self.player.resume()
        else:
            await self.player.pause()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{emoji.pause if self.player.paused else emoji.play} {interaction.user.mention} "
            f"{'paused' if self.player.paused else 'resumed'} the player.",
        )

    async def stop_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await dj.require_dj(interaction, self.player):
            return
        guild: discord.Guild = self.client.get_guild(int(interaction.guild_id))
        await music_log(interaction.guild_id, f"{emoji.stop} {interaction.user.mention} destroyed the player.")
        await stop_player(self.player, guild)

    async def skip_callback(self, interaction: discord.Interaction):
        await request_skip(interaction, self.player)

    async def previous_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await dj.require_dj(interaction, self.player):
            return
        try:
            track = await self.player.previous()
        except sonolink.HistoryEmpty:
            await reply(interaction, f"{emoji.error} Nothing has been played yet.", color=config.color.red)
            return
        await music_log(
            interaction.guild_id,
            f"{emoji.back} {interaction.user.mention} went back to [**{track.title}**]({track.uri}).",
        )

    async def rewind_callback(self, interaction: discord.Interaction):
        await self._seek_by(interaction, -_SEEK_STEP_MS)

    async def forward_callback(self, interaction: discord.Interaction):
        await self._seek_by(interaction, _SEEK_STEP_MS)

    async def _seek_by(self, interaction: discord.Interaction, delta_ms: int) -> None:
        """Nudges playback by ``delta_ms``, skipping when the jump would land past the end of the track."""
        await interaction.response.defer()
        if not await dj.require_dj(interaction, self.player):
            return
        track = self.player.current
        if not track or track.is_stream:
            return
        target = self.player.position + delta_ms
        if target >= track.length:
            await skip_or_stop(self.player, self.client.get_guild(interaction.guild_id))
            return
        target = max(0, target)
        await self.player.seek(target)
        start_lyrics(self.client, interaction.guild_id)
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{emoji.forward if delta_ms > 0 else emoji.rewind} {interaction.user.mention} "
            f"moved track to `{fmt_time(target)}`.",
        )

    async def queue_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=QueueListView(self.client, interaction), ephemeral=True)

    async def play_now_callback(self, interaction: discord.Interaction, identifier: str) -> None:
        """Jumps straight to one of the previewed tracks, for a DJ or whoever queued it."""
        await interaction.response.defer()
        queue = self.player.queue
        # By identifier, not by the position the button was drawn at: `/queue` can reorder or drop
        # a track without repainting the card, and a stale index would skip to the wrong one.
        index = next((i for i in range(len(queue)) if queue[i].identifier == identifier), None)
        if index is None:
            await render_player(self.client, interaction.guild_id)
            return
        track = queue[index]
        if not await dj.require_dj(interaction, self.player, track=track):
            return
        await self.player.skip_to(index)
        await music_log(
            interaction.guild_id,
            f"{emoji.play} {interaction.user.mention} skipped to [**{track.title}**]({track.uri}).",
        )

    async def loop_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await dj.require_dj(interaction, self.player):
            return
        if self.player.queue_mode is sonolink.QueueMode.NORMAL:
            self.player.queue_mode = sonolink.QueueMode.LOOP
            mode = "Track"
        elif self.player.queue_mode is sonolink.QueueMode.LOOP and len(self.player.queue):
            self.player.queue_mode = sonolink.QueueMode.LOOP_ALL
            mode = "Queue"
        else:
            self.player.queue_mode = sonolink.QueueMode.NORMAL
            mode = "Disable"
        loop_emoji = emoji.loop_white if mode == "Disable" else emoji.loop_one if mode == "Track" else emoji.loop
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{loop_emoji} {interaction.user.mention} "
            f"{f'enabled {mode.lower()}' if mode != 'Disable' else 'disabled'} loop.",
        )

    async def shuffle_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await dj.require_dj(interaction, self.player):
            return
        if not len(self.player.queue):
            await reply(interaction, f"{emoji.error} Queue is empty.", color=config.color.red)
            return
        shuffled = self.player.queue.shuffle_mode is sonolink.ShuffleMode.PERSISTENT
        self.player.queue.shuffle_mode = sonolink.ShuffleMode.DEFAULT if shuffled else sonolink.ShuffleMode.PERSISTENT
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{emoji.shuffle} {interaction.user.mention} {'disabled' if shuffled else 'enabled'} shuffle.",
        )

    async def autoplay_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await dj.require_dj(interaction, self.player):
            return
        enabled = self.player.autoplay is sonolink.AutoPlayMode.ENABLED
        self.player.autoplay = sonolink.AutoPlayMode.DISABLED if enabled else sonolink.AutoPlayMode.ENABLED
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{emoji.autoplay} {interaction.user.mention} {'enabled' if not enabled else 'disabled'} autoplay.",
        )


class VoteSkipView(DesignerView):
    """
    Public skip vote, opened when a member without DJ rights asks to skip someone else's track.

    The button doubles as the tally, and a DJ pressing it settles the vote outright.

    Args:
        client (:class:`Client`): The Discord bot client.
        player (:class:`SquarePlayer`): The active player for the guild.
        starter (:class:`Member`): The member who opened the vote, counted as its first vote.
    """

    def __init__(self, client: Client, player: SquarePlayer, starter: discord.Member):
        # The deadline is ours rather than the view's own timeout, which pycord refreshes on every press - including
        # ones it rejects. A window anyone can extend by mashing the button is not one the card can count down to.
        super().__init__(timeout=None)
        self.client = client
        self.player = player
        self.guild_id = player.guild.id
        self.track = player.current
        self.starter = starter
        self.voters: set[int] = {starter.id}
        self.msg: discord.Message | None = None
        self.expires_at = discord.utils.utcnow() + datetime.timedelta(seconds=_VOTE_TIMEOUT)
        self.rendered: tuple[int, int] = (len(self.voters), dj.votes_needed(len(dj.listeners(player))))
        self.deadline = asyncio.create_task(self._expire())
        self.interaction_check = lambda interaction: music_interaction_check(
            player=self.player, interaction=interaction, view=self
        )
        self.build()

    async def _expire(self) -> None:
        """Closes the vote once :attr:`expires_at` passes, however many times the button was pressed meanwhile."""
        await discord.utils.sleep_until(self.expires_at)
        await self.on_timeout()

    def stop(self) -> None:
        super().stop()
        # Never cancel from inside the deadline itself, so an expiring vote can finish tidying up.
        if self.deadline is not asyncio.current_task():
            self.deadline.cancel()

    @property
    def needed(self) -> int:
        """Votes the tally currently has to reach, recomputed so members joining or leaving move the bar."""
        return dj.votes_needed(len(dj.listeners(self.player)))

    def build(self):
        self.clear_items()
        btn = ui.Button(
            label=f"{len(self.voters)}/{self.needed}",
            emoji=emoji.skip_white,
            style=discord.ButtonStyle.grey,
        )
        btn.callback = self.vote_callback
        self.add_item(
            ui.Container(
                ui.Section(
                    ui.TextDisplay("## Vote Skip"),
                    ui.TextDisplay(
                        f"[**{self.track.title}**]({self.track.uri})\n"
                        f"-# Skip requested by {self.starter.mention} [ends {discord.utils.format_dt(self.expires_at, 'R')}]"
                    ),
                    accessory=btn,
                ),
            )
        )

    async def add_vote(self, source: discord.ApplicationContext | discord.Interaction, member: discord.Member) -> None:
        """
        Counts a member's vote and carries the skip once enough listeners agree.

        Args:
            source (:class:`ApplicationContext` | :class:`Interaction`): The command or press the vote came from.
            member (:class:`Member`): The voting member.
        """
        if member.id in self.voters:
            await reply(source, f"{emoji.error} You already voted to skip.", color=config.color.red)
            return
        self.voters.add(member.id)
        if len(self.voters) >= self.needed:
            await reply(source, f"{emoji.skip} Vote passed.")
            await self.resolve()
            return
        await reply(source, f"{emoji.success} Vote counted `{len(self.voters)}/{self.needed}`.")
        await self.render()

    async def render(self) -> None:
        """Pushes the current tally onto the card, skipping the edit when the numbers on it haven't moved."""
        state = (len(self.voters), self.needed)
        if state == self.rendered or not self.msg:
            return
        self.rendered = state
        self.build()
        try:
            await self.msg.edit(view=self)
        except discord.HTTPException:
            pass

    async def refresh(self) -> None:
        """
        Re-evaluates the vote after the voice channel's membership changed.

        Members who left stop counting, both as voters and toward the threshold, so a vote carries the moment
        whoever is still listening already agrees. An emptied channel drops the vote outright.
        """
        if self.is_finished():
            return
        listening = dj.listeners(self.player)
        if not listening:
            self.stop()
            self.release()
            await self.discard()
            return
        self.voters &= {member.id for member in listening}
        if self.voters and len(self.voters) >= self.needed:
            await self.resolve()
            return
        await self.render()

    async def vote_callback(self, interaction: discord.Interaction):
        # Same deadline applies here: the DJ lookup and the tally edit are both round trips.
        await interaction.response.defer()
        if await dj.is_dj(interaction.user, self.player):
            await self.resolve()
            return
        if interaction.user not in dj.listeners(self.player):
            await reply(interaction, f"{emoji.error} Undeafen to vote on a skip.", color=config.color.red)
            return
        await self.add_vote(interaction, interaction.user)

    async def resolve(self) -> None:
        """Closes the vote, settles its card in place, and skips the track."""
        if self.is_finished():
            # Two presses can land either side of the DJ lookup; only the first gets to advance the queue.
            return
        self.stop()
        self.release()
        await self.settle(f"{emoji.skip} {self.starter.mention} vote skipped **{self.track.title}**.")
        guild = self.client.get_guild(self.guild_id)
        if guild:
            await skip_or_stop(self.player, guild)

    async def settle(self, outcome: str, *, color: int | None = None) -> None:
        """Turns the vote card into its outcome, then clears it away a few seconds later."""
        if not self.msg:
            return
        self.clear_items()
        self.add_item(ui.Container(ui.TextDisplay(outcome), color=color))
        try:
            await self.msg.edit(view=self)
            await self.msg.delete(delay=_VOTE_RESULT_LINGER)
        except discord.HTTPException:
            pass
        self.msg = None

    def release(self) -> None:
        """Gives up the guild's vote slot, but only while this view still holds it."""
        if store.skip_vote(self.guild_id) is self:
            store.skip_vote(self.guild_id, mode="clear")

    async def discard(self) -> None:
        """Removes the vote message outright, for when the track it targeted is already gone."""
        if self.msg:
            try:
                await self.msg.delete()
            except discord.HTTPException:
                pass
            self.msg = None

    async def on_timeout(self) -> None:
        self.stop()
        self.release()
        await self.settle(f"{emoji.error} {self.starter.mention}'s skip vote expired.", color=config.color.red)
