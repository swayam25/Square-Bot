import asyncio
import datetime
import discord
import sonolink
import time
from core import Client
from core.view import DesignerView
from discord import ui
from music import dj, lyrics, store
from music.core import SquarePlayer, fmt_time, get_player, requester_id
from music.queue import QueueListView
from music.utils import get_source, music_interaction_check, music_log, reply, split_log_text
from utils import config
from utils.emoji import emoji

# Per-guild asyncio locks - prevents concurrent render_player executions for the same guild.
_render_locks: dict[int, asyncio.Lock] = {}

# Minimum seconds between lyrics-driven message edits - ~3.3 edits/5s worst case, which stays under Discord's ~5 edits/5s per-channel bucket with headroom for other renders.
_LYRICS_MIN_EDIT_INTERVAL = 1.5
# Upper bound on lyrics loop sleep so seeks/pauses are picked up promptly.
_LYRICS_MAX_SLEEP = 5.0
# Lookahead applied to the playback position so the edit lands as the line is sung, compensating for the HTTP round trip of the message edit.
_LYRICS_LEAD_MS = 450
# Seconds between progress-bar-only refreshes (no lyrics, or long instrumental gaps).
_BAR_REFRESH_INTERVAL = 10.0
# How far the rewind/forward buttons jump.
_SEEK_STEP_MS = 10_000
# How long an open skip vote waits for the channel to make up its mind.
_VOTE_TIMEOUT = 60.0
# How long the settled vote stays up before it clears itself away, matching the music log toasts.
_VOTE_RESULT_LINGER = 5.0


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


async def render_player(client: Client, guild_id: int, *, force_new: bool = False) -> None:
    """
    Renders the single persistent player message.

    Edits the player in place while it is still the latest message, otherwise deletes the stale player and posts a fresh one at the bottom of the channel.
    Skips silently if a render is already in progress for this guild.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to render the player for.
        force_new (bool): Always send a new player message instead of editing.
    """
    lock = _get_render_lock(guild_id)
    if lock.locked():
        return
    player = get_player(client, guild_id)
    if not player or not player.connected or not player.current:
        return
    channel = store.play_ch(guild_id)
    if not channel:
        return
    async with lock:
        view = MusicView(client, guild_id)
        play_msg, _ = store.play_msg(guild_id)
        if play_msg and not force_new:
            try:
                await play_msg.edit(view=view)
                store.play_msg(guild_id, play_msg, view, "set")
                return
            except discord.NotFound:
                pass
        # Send new and delete old concurrently - both API calls happen in parallel
        coros: list = [channel.send(view=view)]
        if play_msg:
            coros.append(play_msg.delete())
        results = await asyncio.gather(*coros, return_exceptions=True)
        new_msg = results[0]
        if isinstance(new_msg, discord.Forbidden):
            store.play_msg(guild_id, mode="clear")
            return
        if isinstance(new_msg, BaseException):
            return
        store.play_msg(guild_id, new_msg, view, "set")
        store.chat_weight(guild_id, mode="clear")


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


def cleanup_guild(guild_id: int) -> None:
    """
    Releases all per-guild in-memory state: locks, scheduled tasks (lyrics, relocation), and every store key.

    Cancels tasks first, then flushes the store so the guild entry is dropped entirely.
    A task is never cancelled from within itself, so the caller's own cleanup can finish.
    """
    _render_locks.pop(guild_id, None)
    vote = store.skip_vote(guild_id)
    if vote:
        vote.stop()  # Cancels its expiry task; the card itself is only removed on the async paths.
    for task_fn in (store.lyrics_task, store.render_task):
        task = task_fn(guild_id)
        if task and task is not asyncio.current_task():
            task.cancel()
    store.flush_store(guild_id)


async def clear_player(guild_id: int) -> None:
    """
    Deletes the persistent player message and clears all per-guild state.

    Args:
        guild_id (int): The guild whose player message should be removed.
    """
    await cancel_vote(guild_id)
    play_msg, _ = store.play_msg(guild_id)
    if play_msg:
        try:
            await play_msg.delete()
        except discord.HTTPException:
            pass
    cleanup_guild(guild_id)


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
    await clear_player(guild.id)


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


class MusicView(DesignerView):
    """
    Persistent now-playing card with playback control buttons.

    Displays a :class:`MusicContainer` and two action rows: the first with pause/resume, stop, skip, loop cycle, and shuffle toggle; the second with an autoplay toggle.
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

    def build(self):
        self.clear_items()
        self.add_item(MusicContainer(self.player))
        is_stream = self.player.current.is_stream
        autoplay_on = self.player.autoplay is sonolink.AutoPlayMode.ENABLED
        rows = [
            [
                (emoji.back_white, "previous", not self.player.history),
                (emoji.rewind10s_white, "rewind", is_stream),
                (emoji.play_white if self.player.paused else emoji.pause_white, "pause", False),
                (emoji.forward10s_white, "forward", is_stream),
                (emoji.skip_white, "skip", False),
            ],
            [
                (
                    emoji.loop_white
                    if self.player.queue_mode is sonolink.QueueMode.NORMAL
                    else emoji.loop_one
                    if self.player.queue_mode is sonolink.QueueMode.LOOP
                    else emoji.loop,
                    "loop",
                    False,
                ),
                (
                    emoji.shuffle_white
                    if self.player.queue.shuffle_mode is not sonolink.ShuffleMode.PERSISTENT
                    else emoji.shuffle,
                    "shuffle",
                    False,
                ),
                (emoji.stop_white, "stop", False),
                (emoji.autoplay if autoplay_on else emoji.autoplay_white, "autoplay", False),
                (emoji.queue_white, "queue", False),
            ],
        ]
        for buttons in rows:
            self.add_item(row := ui.ActionRow())
            for btn_emoji, action, disabled in buttons:
                btn = ui.Button(emoji=btn_emoji, custom_id=action, style=discord.ButtonStyle.grey, disabled=disabled)
                btn.callback = getattr(self, f"{action}_callback")
                row.add_item(btn)

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
