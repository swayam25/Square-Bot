import asyncio
import datetime
import discord
import sonolink
from collections.abc import Awaitable
from discord import ui
from pathlib import Path
from square.core import Client
from square.core.view import DesignerView
from square.music import controls, dj, request, stay, store
from square.music.core import (
    SquarePlayer,
    drop_session_lock,
    fmt_time,
    get_player,
    loop_emoji,
    requester_id,
)
from square.music.errors import MusicError
from square.music.queue import QueueListView
from square.music.utils import delete_quietly, get_source, music_interaction_check, music_log, reply, split_log_text
from square.utils import config
from square.utils.emoji import Icon, emoji

_render_locks: dict[int, asyncio.Lock] = {}
# Renders asked for while one was in flight, and whether any of them wanted a new message. The one in flight draws
# again once it's done, because the state it drew may already be stale, e.g. a pause pressed mid-edit.
_rerender: dict[int, bool] = {}

_BAR_REFRESH_INTERVAL = 10.0
_SEEK_STEP_MS = 10_000
_ENQUEUE_RENDER_DELAY = 1.0
RELOCATE_DELAY = 2.0
DEFAULT_VOLUME = 100
_VOTE_TIMEOUT = 60.0
_VOTE_RESULT_LINGER = 5.0
_UP_NEXT_LIMIT = 4
IDLE_GIF = Path("idle.gif")


def idle_attachment() -> dict:
    if not IDLE_GIF.is_file():
        return {}
    return {"file": discord.File(IDLE_GIF, filename=IDLE_GIF.name)}


def has_idle_gif(message: discord.Message | discord.PartialMessage) -> bool | None:
    attachments = getattr(message, "attachments", None)
    if attachments is None:
        return None
    return any(attachment.filename == IDLE_GIF.name for attachment in attachments)


def idle_edit_attachments(message: discord.Message) -> dict:
    """
    Returns the edit kwargs that give a card the idle GIF, or nothing when it already has it.

    The GIF is never removed once attached. A components v2 message hides any attachment that no
    component points at, so it costs nothing while a track plays, and keeping it saves a ~1MB
    upload every time playback stops.

    Args:
        message (:class:`Message`): The card, as a full message.
    """
    if has_idle_gif(message):
        return {}
    # Passing `attachments=[]` alongside the file replaces the set outright.
    return {"attachments": [], **idle_attachment()}


def _get_render_lock(guild_id: int) -> asyncio.Lock:
    if guild_id not in _render_locks:
        _render_locks[guild_id] = asyncio.Lock()
    return _render_locks[guild_id]


async def render_player(client: Client, guild_id: int, *, force_new: bool = False, wait: bool = False) -> None:
    """
    Renders the single persistent player message.

    Edits the player in place while it is still the latest message, otherwise deletes the stale player and posts a fresh one at the bottom of the channel.
    A render asked for while another is in flight doesn't run beside it: the one in flight draws again once it's done,
    so a burst costs one extra edit and the card always ends on the latest state.

    With nothing playing this renders the resting card for a bound request channel, and does
    nothing at all anywhere else.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to render the player for.
        force_new (bool): Always send a new player message instead of editing.
        wait (bool): Queue behind an in-flight render as a render of its own, instead of folding into its redraw.
            For callers that need the card drawn by the time this returns.
    """
    client.dispatch("music_update", guild_id)
    lock = _get_render_lock(guild_id)
    if lock.locked() and not wait:
        _rerender[guild_id] = _rerender.get(guild_id, False) or force_new
        return
    player = get_player(client, guild_id)
    if not (player and player.connected and player.current) and not request.setup_mode(guild_id):
        return
    async with lock:
        while True:
            _rerender.pop(guild_id, None)
            await _render_card(client, guild_id, force_new)
            if guild_id not in _rerender:
                return
            force_new = _rerender[guild_id]


async def _render_card(client: Client, guild_id: int, force_new: bool) -> None:
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
    force_new = force_new and not bound
    play_msg, _ = store.play_msg(guild_id)
    # `/set music` mid-session leaves the free-form card behind in another channel. It cannot be
    # edited into the bound one, so it is deleted and replaced below instead.
    stale = play_msg is not None and play_msg.channel.id != channel.id
    if play_msg and not force_new and not stale:
        try:
            kwargs: dict = {}
            if not live and not store.card_gif(guild_id):
                if isinstance(play_msg, discord.PartialMessage):
                    play_msg = await channel.fetch_message(play_msg.id)
                kwargs = idle_edit_attachments(play_msg)
            edited = await play_msg.edit(view=view, **kwargs) or play_msg
            store.play_msg(guild_id, edited, view, "set")
            store.card_gif(guild_id, has_idle_gif(edited), "set")
            return
        except discord.NotFound:
            play_msg = None
    coros: list = [channel.send(view=view, **(idle_attachment() if not live else {}))]
    if play_msg:
        coros.append(play_msg.delete())
    results = await asyncio.gather(*coros, return_exceptions=True)
    new_msg = results[0]
    if isinstance(new_msg, discord.Forbidden):
        store.play_msg(guild_id, mode="clear")
        store.card_gif(guild_id, None, "set")
        return
    if isinstance(new_msg, BaseException):
        return
    store.play_msg(guild_id, new_msg, view, "set")
    store.card_gif(guild_id, has_idle_gif(new_msg), "set")
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

    The progress ticker repaints a playing card every few seconds and would repost it by itself, but
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
        return
    async with _get_render_lock(guild_id):
        play_msg, _ = store.play_msg(guild_id)
        if play_msg is None or play_msg.id not in deleted_ids:
            return
        store.play_msg(guild_id, mode="clear")
        store.card_gif(guild_id, None, "set")
    await render_player(client, guild_id, wait=True)


def start_progress(client: Client, guild_id: int) -> None:
    task = store.progress_task(guild_id)
    if task:
        task.cancel()
    store.progress_task(guild_id, asyncio.create_task(_progress_loop(client, guild_id)), "set")


async def _progress_loop(client: Client, guild_id: int) -> None:
    player = get_player(client, guild_id)
    if not player or not player.current or player.current.is_stream:
        return
    track = player.current.identifier
    while True:
        await asyncio.sleep(_BAR_REFRESH_INTERVAL)
        current = player.current
        if not player.connected or not current or current.identifier != track:
            return
        if not player.paused:
            await render_player(client, guild_id)


def _cancel_tasks(guild_id: int) -> None:
    vote = store.skip_vote(guild_id)
    if vote:
        vote.stop()
    for task_fn in (store.progress_task, store.render_task):
        task = task_fn(guild_id)
        if task and task is not asyncio.current_task():
            task.cancel()


def cleanup_guild(client: Client, guild_id: int) -> None:
    """
    Releases all per-guild in-memory state: locks, scheduled tasks (progress ticker, relocation), and every store key.

    Cancels tasks first, then flushes the store so the guild entry is dropped entirely. A bound
    guild keeps its card, so its binding is primed straight back into the store the flush emptied.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild_id (int): The guild to release.
    """
    lock = _render_locks.get(guild_id)
    if lock is not None and not lock.locked():
        del _render_locks[guild_id]
    _rerender.pop(guild_id, None)
    drop_session_lock(guild_id)
    _cancel_tasks(guild_id)
    gif = store.card_gif(guild_id)
    store.flush_store(guild_id)
    if request.prime(client, guild_id):
        store.card_gif(guild_id, gif, "set")
    client.dispatch("music_update", guild_id)


async def clear_player(client: Client, guild_id: int) -> None:
    # Before the flush, which drops the channel and message the repaint needs.
    _cancel_tasks(guild_id)
    if request.setup_mode(guild_id):
        retire = render_player(client, guild_id, wait=True)
    else:
        play_msg, _ = store.play_msg(guild_id)
        retire = delete_quietly(play_msg) if play_msg else asyncio.sleep(0)
    await asyncio.gather(cancel_vote(guild_id), retire)
    cleanup_guild(client, guild_id)


async def set_track_status(player: SquarePlayer) -> None:
    if player.channel is None or player.current is None:
        return
    try:
        await player.channel.set_status(status=f"Playing **{player.current.title}**")
    except discord.HTTPException:
        pass


async def clear_status(player: SquarePlayer) -> None:
    guild = player.guild
    voice = guild.me.voice
    channel = voice.channel if voice else player.channel
    if channel is None:
        return
    if voice is None and (
        stay.channel_id(guild.id) is not None or not channel.permissions_for(guild.me).manage_channels
    ):
        return
    try:
        await channel.set_status(status=None)
    except discord.HTTPException:
        pass


def stop_verb(guild_id: int) -> str:
    return "stopped" if stay.channel_id(guild_id) is not None else "destroyed"


async def stop_player(player: SquarePlayer, guild: discord.Guild, *, force: bool = False) -> None:
    """
    Clears the VC status, disconnects (destroying the lavalink-side player), and deletes the player card.

    Safe to call repeatedly: the disconnect fires :meth:`on_sonolink_player_disconnect`, which funnels back
    here, so a per-player guard makes every path after the first a no-op.

    A guild with a 24/7 channel keeps its connection: playback is wound down by :func:`idle_player` instead.

    Args:
        player (:class:`SquarePlayer`): The active player to stop.
        guild (:class:`Guild`): The guild to disconnect from.
        force (bool): Disconnect even from a 24/7 channel, for when the player is already gone or
            the 24/7 channel is being dropped.
    """
    if getattr(player, "_square_stopped", False):
        return
    if not force and stay.channel_id(guild.id) is not None and guild.me.voice is not None:
        await idle_player(player, guild)
        return
    player._square_stopped = True
    await clear_status(player)
    try:
        await player.disconnect(force=True)
    except Exception:
        pass
    await clear_player(player.client, guild.id)


async def idle_player(player: SquarePlayer, guild: discord.Guild) -> None:
    if getattr(player, "_square_idling", False):
        return
    player._square_idling = True
    try:
        player.cancel_empty_timer()
        player.autoplay = sonolink.AutoPlayMode.DISABLED
        player._autoplay_handler._seeds.clear()
        player.queue.shuffle_mode = sonolink.ShuffleMode.DEFAULT
        had_filters = bool(player.presets)
        player.presets.clear()
        try:
            if had_filters:
                await player.apply_presets()  # Before the stop: it seeks, which needs a track.
            await player.stop(clear_queue=True, clear_history=True)
            if player.paused:
                await player.resume()
            if player.volume != DEFAULT_VOLUME:
                await player.set_volume(DEFAULT_VOLUME)
        except Exception:
            pass
        await asyncio.gather(clear_status(player), clear_player(player.client, guild.id))
    finally:
        player._square_idling = False


async def discard_stale(client: Client, guild: discord.Guild) -> None:
    """
    Throws away a voice client that outlived its connection, as one does when the bot is kicked.

    Sonolink only notices a kick through Lavalink's voice connection, so an idle player, or a kick
    that raced a move, lingers as the guild's voice client until something connects over it. It is
    flagged stopped before its disconnect: otherwise the disconnect event runs :func:`stop_player` on
    it, and that second disconnect destroys the guild's Lavalink player and leaves voice, taking down
    whatever connected in the meantime.

    Args:
        client (:class:`Client`): The Discord bot client.
        guild (:class:`Guild`): The guild to clear the stale voice client from.
    """
    stale = guild.voice_client
    if stale is None:
        return
    stale._square_stopped = True
    if isinstance(stale, SquarePlayer):
        await clear_status(stale)
    try:
        await stale.disconnect(force=True)
    except Exception:
        pass
    await clear_player(client, guild.id)


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
    try:
        await player.skip()
    except sonolink.QueueEmpty, sonolink.AutoPlaySeedMissing:
        await stop_player(player, guild)


async def cancel_vote(guild_id: int) -> None:
    vote = store.skip_vote(guild_id)
    if not vote:
        return
    vote.stop()
    store.skip_vote(guild_id, mode="clear")
    await vote.discard()


async def slash_log(
    ctx: discord.ApplicationContext,
    content: str,
    *,
    color: int | None = None,
    render: bool = True,
) -> None:
    log_emoji, text = split_log_text(content)
    log = music_log(ctx.guild.id, f"{log_emoji} {ctx.author.mention} {text}".strip(), color=color)
    await asyncio.gather(
        reply(ctx, content, color=color), log, *([render_player(ctx.bot, ctx.guild.id)] if render else [])
    )


class MusicContainer(ui.Container):
    def __init__(self, player: SquarePlayer):
        super().__init__()
        rid = requester_id(player, player.current)
        info = (
            f"{emoji.user} **Requested By**: {f'<@{rid}>' if rid else 'Unknown'}\n"
            f"{emoji.mic} **Artist**: {get_source(player.current.source_name)['emoji']} {player.current.author}"
        )
        texts = [ui.TextDisplay(f"## [{player.current.title}]({player.current.uri})"), ui.TextDisplay(info)]
        artwork = player.current.artwork
        self.items = [ui.Section(*texts, accessory=ui.Thumbnail(url=artwork))] if artwork else texts
        self.items.append(ui.TextDisplay(self.progress_bar(player)))

    @staticmethod
    def progress_bar(player: SquarePlayer, bar_length: int = 10) -> str:
        active = str(emoji.still_bar if player.paused else emoji.filled_bar)
        if player.current.is_stream:
            return f"{emoji.live} **LIVE** {active * bar_length}"
        length = player.current.length
        filled = min(bar_length, int(bar_length * player.position // length)) if length else 0
        return (
            f"`{fmt_time(player.position)}` "
            f"{active * filled}{str(emoji.empty_bar) * (bar_length - filled)} "
            f"`{fmt_time(player.current.length)}`"
        )


class UpNextContainer(ui.Container):
    def __init__(self, player: SquarePlayer, view: MusicView):
        super().__init__()
        # Indexed, not `queue.tracks`: that property copies the whole queue, and this runs on every
        # paint, which the progress ticker drives every few seconds.
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
        elif player.autoplay_on:
            self.add_item(ui.TextDisplay(f"-# {emoji.autoplay} Nothing queued. Autoplay takes over when this ends."))
        else:
            self.add_item(ui.TextDisplay("-# Nothing up next. Queue something to keep the music going."))


class IdleContainer(ui.Container):
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

    def _rows(self) -> list[list[tuple[Icon, str, bool]]]:
        player = self.player if self.live else None
        is_stream = bool(player and player.current.is_stream)
        queue_mode = player.queue_mode if player else sonolink.QueueMode.NORMAL
        shuffled = bool(player and player.shuffled)
        autoplay_on = bool(player and player.autoplay_on)
        return [
            [
                (emoji.back_white, "previous", not (player and player.history)),
                (emoji.rewind10s_white, "rewind", is_stream),
                (emoji.play_white if player and player.paused else emoji.pause_white, "pause", False),
                (emoji.forward10s_white, "forward", is_stream),
                (emoji.skip_white, "skip", False),
            ],
            [
                (loop_emoji(queue_mode), "loop", False),
                (emoji.shuffle if shuffled else emoji.shuffle_white, "shuffle", False),
                (emoji.stop_white, "stop", False),
                (emoji.autoplay if autoplay_on else emoji.autoplay_white, "autoplay", False),
                (emoji.queue_white, "queue", False),
            ],
        ]

    async def _control(self, interaction: discord.Interaction, action: Awaitable[str], *, confirm: bool = False):
        try:
            confirmation = await action
        except MusicError as exc:
            await reply(interaction, f"{emoji.error} {exc}", color=config.color.red)
            return
        if confirm:
            await reply(interaction, confirmation)

    async def pause_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._control(interaction, controls.set_paused(interaction.guild, interaction.user))

    async def stop_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._control(interaction, controls.stop(interaction.guild, interaction.user))

    async def skip_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._control(
            interaction, controls.skip(interaction.guild, interaction.user, channel=interaction.channel), confirm=True
        )

    async def previous_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._control(interaction, controls.previous(interaction.guild, interaction.user))

    async def rewind_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._control(interaction, controls.seek_by(interaction.guild, interaction.user, -_SEEK_STEP_MS))

    async def forward_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._control(interaction, controls.seek_by(interaction.guild, interaction.user, _SEEK_STEP_MS))

    async def queue_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=QueueListView(self.client, interaction), ephemeral=True)

    async def play_now_callback(self, interaction: discord.Interaction, identifier: str) -> None:
        await interaction.response.defer()
        queue = self.player.queue
        # By identifier, not by the position the button was drawn at: `/queue` can reorder or drop
        # a track without repainting the card, and a stale index would skip to the wrong one.
        index = next((i for i in range(len(queue)) if queue[i].identifier == identifier), None)
        if index is None:
            await render_player(self.client, interaction.guild_id)
            return
        await self._control(interaction, controls.jump(interaction.guild, interaction.user, index, identifier))

    async def loop_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        mode = controls.next_loop(self.player)
        await self._control(interaction, controls.set_loop(interaction.guild, interaction.user, mode))

    async def shuffle_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._control(interaction, controls.set_shuffle(interaction.guild, interaction.user))

    async def autoplay_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._control(interaction, controls.set_autoplay(interaction.guild, interaction.user))


class VoteSkipView(DesignerView):
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
        await discord.utils.sleep_until(self.expires_at)
        await self.on_timeout()

    def stop(self) -> None:
        super().stop()
        # Never cancel from inside the deadline itself, so an expiring vote can finish tidying up.
        if self.deadline is not asyncio.current_task():
            self.deadline.cancel()

    @property
    def needed(self) -> int:
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

    async def add_vote(self, member: discord.Member) -> str:
        if member.id in self.voters:
            raise MusicError("You already voted to skip.")
        self.voters.add(member.id)
        if len(self.voters) >= self.needed:
            await self.resolve()
            return f"{emoji.skip} Vote passed."
        self.client.dispatch("music_update", self.guild_id)
        await self.render()
        return f"{emoji.success} Vote counted `{len(self.voters)}/{self.needed}`."

    async def render(self) -> None:
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
        self.client.dispatch("music_update", self.guild_id)
        await self.render()

    async def vote_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if dj.is_dj(interaction.user, self.player):
            await self.resolve()
            return
        if interaction.user not in dj.listeners(self.player):
            await reply(interaction, f"{emoji.error} Undeafen to vote on a skip.", color=config.color.red)
            return
        try:
            await reply(interaction, await self.add_vote(interaction.user))
        except MusicError as exc:
            await reply(interaction, f"{emoji.error} {exc}", color=config.color.red)

    async def resolve(self) -> None:
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
        if store.skip_vote(self.guild_id) is self:
            store.skip_vote(self.guild_id, mode="clear")
            self.client.dispatch("music_update", self.guild_id)

    async def discard(self) -> None:
        if self.msg:
            await delete_quietly(self.msg)
            self.msg = None

    async def on_timeout(self) -> None:
        self.stop()
        self.release()
        await self.settle(f"{emoji.error} {self.starter.mention}'s skip vote expired.", color=config.color.red)
