import asyncio
import discord
import lavalink
import time
from core import Client
from core.view import DesignerView
from discord import ui
from music import lyrics, recommend, store
from music.utils import music_interaction_check, music_log, reply, sources, to_log_text
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


def _get_render_lock(guild_id: int) -> asyncio.Lock:
    """
    Returns the render lock for a guild, creating it on first access.

    Parameters:
        guild_id (int): The guild ID to retrieve the lock for.

    Returns:
        asyncio.Lock: The lock associated with the guild.
    """
    if guild_id not in _render_locks:
        _render_locks[guild_id] = asyncio.Lock()
    return _render_locks[guild_id]


async def render_player(client: Client, guild_id: int, *, force_new: bool = False) -> None:
    """
    Renders the single persistent player message.

    Edits the player in place while it is still the latest message, otherwise deletes the stale player and posts a fresh one at the bottom of the channel.
    Skips silently if a render is already in progress for this guild.

    Parameters:
        client (Client): The Discord bot client.
        guild_id (int): The guild to render the player for.
        force_new (bool): Always send a new player message instead of editing.
    """
    lock = _get_render_lock(guild_id)
    if lock.locked():
        return
    player: lavalink.DefaultPlayer = client.lavalink.player_manager.get(guild_id)
    if not player or not player.is_connected or not player.current:
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

    Parameters:
        client (Client): The Discord bot client.
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
    Edits are throttled to one per `_LYRICS_MIN_EDIT_INTERVAL` seconds to stay clear of Discord rate limits, and nothing is edited while paused or when the line hasn't changed.
    Tracks without lyrics (and instrumental gaps) still get a bar-only refresh every `_BAR_REFRESH_INTERVAL` seconds.

    Parameters:
        client (Client): The Discord bot client.
        guild_id (int): The guild to update lyrics for.
    """
    player: lavalink.DefaultPlayer = client.lavalink.player_manager.get(guild_id)
    if not player or not player.current or player.current.stream:
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
        if not player.is_connected or not current or current.identifier != track.identifier:
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
    Releases all per-guild in-memory state: locks, scheduled tasks (lyrics, relocation, inactivity), and every store key.

    Cancels tasks first, then flushes the store so the guild entry is dropped entirely.
    A task is never cancelled from within itself (the inactivity task reaches here through `stop_player`), so the caller's own cleanup can finish.
    """
    _render_locks.pop(guild_id, None)
    recommend.cleanup(guild_id)
    for task_fn in (store.lyrics_task, store.render_task, store.inactivity_task):
        task = task_fn(guild_id)
        if task and task is not asyncio.current_task():
            task.cancel()
    store.flush_store(guild_id)


async def clear_player(guild_id: int) -> None:
    """
    Deletes the persistent player message and clears all per-guild state.

    Parameters:
        guild_id (int): The guild whose player message should be removed.
    """
    play_msg, _ = store.play_msg(guild_id)
    if play_msg:
        try:
            await play_msg.delete()
        except discord.HTTPException:
            pass
    cleanup_guild(guild_id)


async def stop_player(player: lavalink.DefaultPlayer, guild: discord.Guild) -> None:
    """
    Stops playback, clears the VC status, disconnects from voice, and deletes the player card.

    Parameters:
        player (DefaultPlayer): The active Lavalink player to stop.
        guild (Guild): The guild to disconnect from.
    """
    try:
        await player.stop()
    except Exception:
        pass  # Node may be unreachable; still disconnect and clean up locally
    if guild.me.voice and guild.me.voice.channel:
        await guild.me.voice.channel.set_status(status=None)
    if guild.voice_client:
        await guild.voice_client.disconnect(force=True)
    await clear_player(guild.id)


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

    Parameters:
        ctx (ApplicationContext): The slash command context.
        content (str): The confirmation/log message (leading emoji is stripped for the log line).
        color (int | None): Optional accent color applied to both the reply and the log.
        render (bool): Whether to re-render the player card after the action.
    """
    await reply(ctx, content, color=color)
    if render:
        await render_player(ctx.bot, ctx.guild.id)
    await music_log(ctx.guild.id, f"{ctx.author.mention} {to_log_text(content)}", color=color)


class MusicContainer(ui.Container):
    """
    Renders the currently playing track as a Discord container component.

    Displays the track title (linked), artist, requester mention, and a position/duration progress bar (fully filled with a LIVE badge for streams).
    When synced lyrics are cached for the current track, a previous/current/next line window is appended with the current line in bold.

    Parameters:
        player (DefaultPlayer): The active Lavalink player with a current track set.
    """

    def __init__(self, player: lavalink.DefaultPlayer):
        super().__init__()
        requester = f"<@{player.current.requester}>"
        info = (
            f"{emoji.user} **Requested By**: {requester if requester else 'Unknown'}\n"
            f"{emoji.mic} **Artist**: {sources.get(player.current.source_name, sources['_'])['emoji']} {player.current.author}"
        )
        self.items = [
            ui.Section(
                ui.TextDisplay(f"## [{player.current.title}]({player.current.uri})"),
                ui.TextDisplay(info),
                accessory=ui.Thumbnail(url=player.current.artwork_url),
            )
        ]
        lyrics_text = self._lyrics_text(player)
        if lyrics_text:
            self.items.append(ui.TextDisplay(lyrics_text))
        self.items.append(ui.TextDisplay(self._progress_bar(player)))

    @staticmethod
    def _progress_bar(player: lavalink.DefaultPlayer, bar_length: int = 10) -> str:
        """Builds the position/duration progress bar line. Streams get a fully filled bar with a LIVE badge."""
        if player.current.stream:
            return f"{emoji.live} **LIVE** {emoji.filled_bar * bar_length}"
        filled = min(bar_length, int(bar_length * player.position // float(player.current.duration)))
        return (
            f"`{lavalink.format_time(player.position)}` "
            f"{emoji.filled_bar * filled}{emoji.empty_bar * (bar_length - filled)} "
            f"`{lavalink.format_time(player.current.duration)}`"
        )

    @staticmethod
    def _lyrics_text(player: lavalink.DefaultPlayer) -> str | None:
        """
        Builds the three-line synced lyrics block for the current playback position.

        Returns None when no lyrics are cached for the current track.
        """
        cached = store.lyrics(int(player.guild_id))
        if not cached or cached[0] != player.current.identifier or not cached[1]:
            return None
        _, prev, current, upcoming = lyrics.window(cached[1], player.position + _LYRICS_LEAD_MS)

        def fmt(line: str) -> str:
            return discord.utils.escape_markdown(line) if line else "♪"

        return f"-# {fmt(prev)}\n**{fmt(current)}**\n-# {fmt(upcoming)}"


class MusicView(DesignerView):
    """
    Persistent now-playing card with playback control buttons.

    Displays a `MusicContainer` and two action rows: the first with pause/resume, stop, skip, loop cycle, and shuffle toggle; the second with an autoplay toggle.
    The view has no timeout and re-checks interaction eligibility on every button press.

    Parameters:
        client (Client): The bot client used to fetch the player and send follow-up logs.
        guild_id (int): The guild this player card belongs to.
    """

    def __init__(self, client: Client, guild_id: int):
        super().__init__(timeout=None)
        self.client = client
        self.guild_id = guild_id
        self.player: lavalink.DefaultPlayer = client.lavalink.player_manager.get(guild_id)
        self.interaction_check = lambda interaction: music_interaction_check(
            player=self.player, interaction=interaction, view=self
        )
        self.build()

    def build(self):
        self.clear_items()
        self.add_item(MusicContainer(self.player))
        self.add_item(row := ui.ActionRow())
        for btn_emoji, action in [
            (emoji.play_white if self.player.paused else emoji.pause_white, "pause"),
            (emoji.stop_white, "stop"),
            (emoji.skip_white, "skip"),
            (
                emoji.loop_white
                if self.player.loop == self.player.LOOP_NONE
                else emoji.loop_one
                if self.player.loop == self.player.LOOP_SINGLE
                else emoji.loop,
                "loop",
            ),
            (emoji.shuffle_white if not self.player.shuffle else emoji.shuffle, "shuffle"),
        ]:
            btn = ui.Button(emoji=btn_emoji, custom_id=action, style=discord.ButtonStyle.grey)
            btn.callback = getattr(self, f"{action}_callback")
            row.add_item(btn)
        autoplay_on = store.autoplay(self.guild_id)
        autoplay_btn = ui.Button(emoji=emoji.autoplay if autoplay_on else emoji.autoplay_white, custom_id="autoplay")
        autoplay_btn.callback = self.autoplay_callback
        self.add_item(ui.ActionRow(autoplay_btn))

    async def pause_callback(self, interaction: discord.Interaction):
        await self.player.set_pause(not self.player.paused)
        await interaction.response.defer()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{interaction.user.mention} {'paused' if self.player.paused else 'resumed'} the player.",
        )

    async def stop_callback(self, interaction: discord.Interaction):
        guild: discord.Guild = self.client.get_guild(int(interaction.guild_id))
        await interaction.response.defer()
        await music_log(interaction.guild_id, f"{interaction.user.mention} destroyed the player.")
        await stop_player(self.player, guild)

    async def skip_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.player.skip()
        await music_log(interaction.guild_id, f"{interaction.user.mention} skipped the track.")

    async def loop_callback(self, interaction: discord.Interaction):
        if self.player.loop == self.player.LOOP_NONE:
            self.player.set_loop(1)
            mode = "Track"
        elif self.player.loop == self.player.LOOP_SINGLE and self.player.queue:
            self.player.set_loop(2)
            mode = "Queue"
        else:
            self.player.set_loop(0)
            mode = "Disable"
        await interaction.response.defer()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{interaction.user.mention} {'enabled' if mode != 'Disable' else 'disabled'} {mode} loop.",
        )

    async def shuffle_callback(self, interaction: discord.Interaction):
        if not self.player.queue:
            await reply(interaction, f"{emoji.error} Queue is empty.", color=config.color.red)
            return
        self.player.set_shuffle(not self.player.shuffle)
        await interaction.response.defer()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{interaction.user.mention} {'enabled' if self.player.shuffle else 'disabled'} shuffle.",
        )

    async def autoplay_callback(self, interaction: discord.Interaction):
        enabled = store.autoplay(interaction.guild_id)
        store.autoplay(interaction.guild_id, not enabled, "set")
        await interaction.response.defer()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            interaction.guild_id,
            f"{interaction.user.mention} {'enabled' if not enabled else 'disabled'} autoplay.",
        )
