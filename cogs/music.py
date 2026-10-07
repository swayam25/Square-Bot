import asyncio
import datetime
import discord
import math
import re
import sonolink
from babel.dates import format_timedelta
from core import Client
from core.view import DesignerView
from db.funcs.dj import fetch_dj
from discord import SlashCommandGroup, ui
from discord.commands import option, slash_command
from discord.ext import commands, tasks
from music import dj, request, stay, store
from music.core import (
    LOOP_LABELS,
    SquarePlayer,
    fetch_node_info,
    fmt_time,
    get_player,
    loop_action,
    loop_emoji,
    register_nodes,
    requester_id,
    session_lock,
)
from music.dj import DJView
from music.filters import EQ_PRESETS
from music.history import HistoryListView, history_tracks
from music.play import (
    TrackPickerView,
    clean_query,
    enqueue,
    ensure_connected,
    is_link,
    resolve_and_enqueue,
    resolve_query,
    search_tracks,
    voice_error,
)
from music.player import (
    RELOCATE_DELAY,
    MusicContainer,
    cancel_vote,
    cleanup_guild,
    discard_stale,
    release_guild,
    render_player,
    repaint_deleted_card,
    request_skip,
    schedule_render,
    set_track_status,
    skip_or_stop,
    slash_log,
    start_lyrics,
    stop_player,
    stop_verb,
)
from music.queue import QueueListView
from music.utils import container, delete_quietly, get_source, music_log, reply, split_log_text
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from sonolink.models import Playlist
from utils import config
from utils.emoji import emoji
from utils.helpers import parse_duration

console = Console()


# Discord renders at most this many autocomplete choices, and caps each name and value at 100 characters.
AUTOCOMPLETE_LIMIT = 25
CHOICE_LIMIT = 100
# Seconds after the bot leaves voice before a player nothing tore down is treated as kicked.
KICK_GRACE = 2.0
FAILOVER_INTERVAL = 5.0
# Matches the five tracks a `/queue` and `/history` page shows.
PAGE_SIZE = 5


class Music(commands.Cog):
    # Estimated on-screen chat lines an attachment/embed/sticker occupies - tall enough that one big block relocates the player on its own.
    block_lines = 10
    # Characters per rendered chat line, used to estimate wrapping of long messages.
    chars_per_line = 60
    # Relocate the player once this many estimated chat lines have stacked below it.
    relocate_lines = 10
    # Commands the whole channel hears the result of. DJ mode limits these, and every `/eq` filter, to DJs.
    dj_commands = {
        "autoplay",
        "clear-queue",
        "loop",
        "pause",
        "resume",
        "seek",
        "shuffle",
        "skip-to",
        "stop",
        "volume",
    }

    loop_modes = {
        "Disable": sonolink.QueueMode.NORMAL,
        "Track": sonolink.QueueMode.LOOP,
        "Queue": sonolink.QueueMode.LOOP_ALL,
    }

    def __init__(self, client: Client):
        self.client = client
        self._node_live: Live | None = None
        self._adopting: asyncio.Task | None = None
        self._staying: asyncio.Task | None = None
        self._down_nodes: set[str] = set()
        self._request_cooldown = commands.CooldownMapping.from_cooldown(2, 5.0, commands.BucketType.member)
        self._cooldown_warn = commands.CooldownMapping.from_cooldown(1, 15.0, commands.BucketType.member)
        register_nodes(client)

    # Console spinner helpers
    def _start_spinner(self, text: str):
        if self._node_live is None or not self._node_live.is_started:
            self._node_live = Live(
                Spinner("dots", text=f"[yellow]{text}[/]", style="yellow"),
                console=console,
                refresh_per_second=10,
                transient=False,
            )
            self._node_live.start()

    def _finish_spinner(self, text: Text):
        if self._node_live and self._node_live.is_started:
            self._node_live.update(text)
            self._node_live.stop()
            self._node_live = None
        else:
            console.print(text)

    @commands.Cog.listener()
    async def on_connect(self):
        await self.client.sonolink.start()
        if not self.failover.is_running():
            self.failover.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """Reloads the request channel bindings and takes their cards back over, then rejoins 24/7 channels."""
        if self._adopting and not self._adopting.done():
            return  # A resume re-fires this; two adoption sweeps would each post a card.
        await request.seed()
        await stay.seed()
        self._adopting = self.client.loop.create_task(request.adopt_all(self.client))
        self._join_stay_channels()

    def _join_stay_channels(self) -> None:
        """Sends the bot back into every 24/7 channel, unless a sweep is already doing that."""
        if self._staying and not self._staying.done():
            return
        self._staying = self.client.loop.create_task(stay.join_all(self.client))

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Drops the binding and stops playback when the request channel or the 24/7 channel is deleted."""
        guild = channel.guild
        if stay.is_stay_channel(guild.id, channel.id):
            await stay.unbind(guild.id)
            player = get_player(self.client, guild.id)
            if player:
                await stop_player(player, guild, force=True)
            return
        if not request.is_request_channel(guild.id, channel.id):
            return
        await request.unbind(guild.id)
        await release_guild(self.client, guild.id)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """Reposts the card when someone deletes it."""
        if payload.guild_id:
            await repaint_deleted_card(self.client, payload.guild_id, {payload.message_id})

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        """Reposts the card when a purge takes it along with everything else."""
        if payload.guild_id:
            await repaint_deleted_card(self.client, payload.guild_id, payload.message_ids)

    @commands.Cog.listener()
    async def on_sonolink_node_ready(self, event: sonolink.gateway.ReadyEvent):
        node = event.node
        _, latency = await fetch_node_info(node)
        text = Text()
        text.append("✓ Connected to Lavalink ", style="green")
        text.append(node.id, style="cyan")
        text.append("\n  ├ Latency", style="green")
        text.append(": ")
        text.append(latency, style="cyan")
        text.append("\n  ╰ Resumed", style="green")
        text.append(": ")
        text.append(str(event.resumed), style="cyan")
        self._finish_spinner(text)
        if event.resumed:
            await self._drop_failed_over(node)
        self._join_stay_channels()

    async def _drop_failed_over(self, node: sonolink.Node) -> None:
        """
        Destroys the players a resumed node still holds for guilds that failed over while it was down.

        Lavalink keeps a resumable session's players alive, so without this the old node would come
        back playing into the same voice connection as the node that took over.
        """
        try:
            held = await node.fetch_players()
        except Exception:
            return
        for info in held:
            player = get_player(self.client, info.guild_id)
            if player is not None and player._node is node:
                continue
            try:
                # The same call sonolink's own `move_to` makes on the node it leaves.
                await node._manager.destroy_player(session_id=node._resume_session, guild_id=str(info.guild_id))
            except Exception:
                pass

    @tasks.loop(seconds=FAILOVER_INTERVAL)
    async def failover(self):
        """
        Moves players off a node that has stayed down for a full tick onto a healthy one.

        Polled because a node that drops goes straight into reconnecting without firing
        `node_close`. The tick of grace spares the players a move when a node is back in seconds.
        """
        down = {node.id for node in self.client.sonolink.nodes if not node.is_connected}
        stranded, self._down_nodes = self._down_nodes & down, down
        if not stranded:
            return
        for player in [vc for vc in self.client.voice_clients if isinstance(vc, SquarePlayer)]:
            if player._node is None or player._node.id not in stranded:
                continue
            try:
                node = self.client.sonolink.get_best_node()
            except RuntimeError:
                return  # Nothing healthy to move to; sonolink keeps reconnecting the dead node.
            try:
                await player.move_to(node)
            except Exception as exc:
                console.print(f"[yellow]Failover to[/] [cyan]{node.id}[/] failed:", exc)
                continue
            await music_log(player.guild.id, f"{emoji.reload} Switched to a backup music server.")

    @commands.Cog.listener()
    async def on_sonolink_node_close(self, node: sonolink.Node):
        text = Text()
        text.append("✗ Disconnected from Lavalink ", style="red")
        text.append(node.id, style="cyan")
        self._finish_spinner(text)
        self._start_spinner("Reconnecting to Lavalink...")

    @commands.Cog.listener()
    async def on_sonolink_track_start(self, player: SquarePlayer, event: sonolink.gateway.TrackStartEvent):
        """
        Renders the card for the new track, relocating it to the bottom when any chat has landed under it.

        A track change is the one moment the card is worth re-sending cheaply: a single message below it is enough to
        trigger a fresh send, so the new track always announces itself at the bottom of the channel.
        With an untouched channel the card is edited in place as usual.
        """
        guild_id = player.guild.id
        track = player.current
        if track is None:
            return
        relocate = store.chat_weight(guild_id) > 0
        if relocate:
            pending = store.render_task(guild_id)
            if pending and not pending.done():
                # This render supersedes the scheduled relocation - let it not fire a second send right after.
                pending.cancel()
        await cancel_vote(guild_id)
        await asyncio.gather(
            render_player(self.client, guild_id, force_new=relocate), set_track_status(player), return_exceptions=True
        )
        start_lyrics(self.client, guild_id)

    @commands.Cog.listener()
    async def on_sonolink_track_end(self, player: SquarePlayer, event: sonolink.gateway.TrackEndEvent):
        if event.reason not in (sonolink.TrackEndReason.FINISHED, sonolink.TrackEndReason.LOAD_FAILED):
            return
        if player.current is None and not len(player.queue):
            guild = self.client.get_guild(player.guild.id)
            if guild:
                await stop_player(player, guild)

    @commands.Cog.listener()
    async def on_sonolink_track_exception(self, player: SquarePlayer, event: sonolink.gateway.TrackExceptionEvent):
        track = event.track
        reason = event.exception.message
        await music_log(
            player.guild.id,
            f"{emoji.error} Couldn't play [**{track.title}**]({track.uri}).{f'\n-# {reason[:200]}' if reason else ''}",
            color=config.color.red,
        )

    @commands.Cog.listener()
    async def on_sonolink_track_stuck(self, player: SquarePlayer, event: sonolink.gateway.TrackStuckEvent):
        """Skips a track that stopped sending audio, since Lavalink leaves it hanging."""
        track = event.track
        # A track that already moved on was handled by Lavalink, and skipping now would cost the next one.
        if player.current != track:
            return
        await music_log(
            player.guild.id,
            f"{emoji.error} [**{track.title}**]({track.uri}) got stuck, skipping it.",
            color=config.color.red,
        )
        await skip_or_stop(player, player.guild)

    @commands.Cog.listener()
    async def on_sonolink_player_disconnect(self, player: SquarePlayer, event: sonolink.PlayerDisconnectEvent):
        """Single cleanup funnel: fires for manual stops, inactivity, kicks, and node errors."""
        guild = self.client.get_guild(player.guild.id)
        if guild is None:
            cleanup_guild(self.client, player.guild.id)
            return
        if event.trigger is sonolink.DisconnectTriggerType.INACTIVITY:
            channel = player.channel
            await music_log(
                guild.id,
                f"{emoji.remove} Left {channel.mention if channel else 'the voice channel'} due to inactivity.",
                color=config.color.red,
            )
        await stop_player(player, guild, force=True)
        stay.schedule_rejoin(self.client, guild.id)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        """
        Keeps an open skip vote honest as listeners come, go, and deafen, since the threshold moves with them.

        Also follows the bot when it is moved or kicked, and tells the player when its channel empties or fills.
        """
        if member.id == self.client.user.id:
            await self._on_bot_voice_update(member.guild, after)
            return
        if member.bot:
            return
        deafened = (before.deaf or before.self_deaf) != (after.deaf or after.self_deaf)
        if before.channel == after.channel and not deafened:
            return
        player = get_player(self.client, member.guild.id)
        if not player or not player.connected or player.channel not in (before.channel, after.channel):
            return
        if before.channel != after.channel:
            # Sonolink only re-checks on track ends and the bot's own voice changes.
            player._check_inactivity()
        vote = store.skip_vote(member.guild.id)
        if vote:
            await vote.refresh()

    async def _on_bot_voice_update(self, guild: discord.Guild, after: discord.VoiceState) -> None:
        """Follows the bot into whatever channel it was moved to, unless it belongs in its 24/7 channel."""
        player = get_player(self.client, guild.id)
        if after.channel is None:
            if stay.channel_id(guild.id) is not None:
                stay.schedule_rejoin(self.client, guild.id)
            elif player and not getattr(player, "_square_stopped", False):
                self.client.loop.create_task(self._reap_kicked(guild, player))
            return
        if stay.channel_id(guild.id) not in (None, after.channel.id):
            channel = await stay.resolve(guild)
            if channel:
                if player:
                    await stay.move(player, channel)
                return
        if player and player.channel != after.channel:
            player.channel = after.channel
            await set_track_status(player)
            vote = store.skip_vote(guild.id)
            if vote:
                await vote.refresh()

    async def _reap_kicked(self, guild: discord.Guild, player: SquarePlayer) -> None:
        """Clears away a player whose bot was disconnected without anything tearing it down."""
        # Our own disconnects land here a beat before their teardown does, hence the grace.
        await asyncio.sleep(KICK_GRACE)
        async with session_lock(guild.id):
            if (
                get_player(self.client, guild.id) is player
                and guild.me.voice is None
                and not getattr(player, "_square_stopped", False)
            ):
                await discard_stale(self.client, guild)

    # Current voice
    def current_voice_channel(self, ctx: discord.ApplicationContext):
        if ctx.guild and ctx.guild.me.voice:
            return ctx.guild.me.voice.channel
        return None

    # Unloading cog
    def cog_unload(self):
        self.failover.cancel()
        if self._node_live and self._node_live.is_started:
            self._node_live.stop()
            self._node_live = None

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        request.forget(guild.id)
        stay.forget(guild.id)
        cleanup_guild(self.client, guild.id)

    # Ensures voice parameters
    async def ensure_voice(self, ctx: discord.ApplicationContext, *, need_queue: bool = False) -> SquarePlayer | None:
        """
        Checks all the voice parameters. `/play` connects instead, through :func:`ensure_connected`.

        Args:
            ctx (:class:`ApplicationContext`): The invoking command.
            need_queue (bool): Also refuse when nothing is queued.
        """

        def _err(text: str) -> DesignerView:
            return container(text, config.color.red)

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond(view=_err(f"{emoji.error} Join a voice channel first."), ephemeral=True)
            return None

        player = get_player(self.client, ctx.guild.id)
        bot_channel = self.current_voice_channel(ctx)

        if player is None or bot_channel is None or (not player.current and ctx.command.name != "stop"):
            await ctx.respond(
                view=_err(f"{emoji.error} Nothing is being played at the current moment."), ephemeral=True
            )
            return None
        if ctx.author.voice.channel != bot_channel:
            await ctx.respond(view=_err(f"{emoji.error} You are not in my voice channel."), ephemeral=True)
            return None

        name = ctx.command.qualified_name
        if (name in self.dj_commands or name.startswith("eq ")) and not await dj.require_dj(ctx, player):
            return None
        if need_queue and not len(player.queue):
            await ctx.respond(view=_err(f"{emoji.error} Queue is empty."), ephemeral=True)
            return None

        return player

    @staticmethod
    async def _queue_index(ctx: discord.ApplicationContext, player: SquarePlayer, track: str) -> int | None:
        """
        Reads a queue position from an autocomplete pick (`3. Title`) or a typed number.

        Returns:
            int | None: The zero-based index, or None after telling the member it's out of range.
        """
        match = re.match(r"\s*(\d+)", track)
        position = int(match[1]) if match else 0
        if 1 <= position <= len(player.queue):
            return position - 1
        await reply(
            ctx, f"{emoji.error} Track number must be between `1` and `{len(player.queue)}`.", color=config.color.red
        )
        return None

    @staticmethod
    async def _check_page(ctx: discord.ApplicationContext, page: int, items: int) -> bool:
        """Whether a list of `items` has the requested page, telling the member when it doesn't."""
        pages = max(1, math.ceil(items / PAGE_SIZE))
        if page <= pages:
            return True
        await reply(ctx, f"{emoji.error} Page must be between `1` and `{pages}`.", color=config.color.red)
        return False

    @staticmethod
    def _choice_name(author: str, title: str, tail: str) -> str:
        """Fits `author - title - tail` into an autocomplete choice name, trimming the title first."""
        room = max(3, CHOICE_LIMIT - len(author) - len(tail) - 6)  # " - " twice
        if len(title) > room:
            title = title[: room - 3] + "..."
        return f"{author} - {title} - {tail}"[:CHOICE_LIMIT]

    # Search autocomplete
    async def search(self, ctx: discord.AutocompleteContext):
        """Suggests tracks for a typed name, or shows what a pasted link points to."""
        value = ctx.value.strip()
        link = is_link(value)
        if link and len(value) > CHOICE_LIMIT:
            return []  # Too long to be a choice value, so Discord submits the link as typed.
        result = await search_tracks(self.client, clean_query(value) if link else value or "top tracks", retry=False)
        if result is None or result.is_error() or result.is_empty() or result.result is None:
            return []
        data = result.result
        if link and isinstance(data, Playlist):
            return [
                discord.OptionChoice(name=self._choice_name("Playlist", data.name, f"{len(data)} tracks"), value=value)
            ]
        found = data.tracks if isinstance(data, Playlist) else data if isinstance(data, list) else [data]
        choices = []
        for track in found[: 1 if link else AUTOCOMPLETE_LIMIT]:
            name = self._choice_name(track.author, track.title, "LIVE" if track.is_stream else fmt_time(track.length))
            if link:
                choice_value = value
            elif track.uri and len(track.uri) <= CHOICE_LIMIT:
                choice_value = track.uri
            else:
                choice_value = name
            choices.append(discord.OptionChoice(name=name, value=choice_value))
        return choices

    # Track autocomplete
    async def track_autocomplete(self, ctx: discord.AutocompleteContext):
        """Provides track indices for removal."""
        player = get_player(self.client, ctx.interaction.guild_id)
        if not player or not len(player.queue):
            return []
        result = []
        needle = ctx.value.lower()
        for i, track in enumerate(player.queue):
            entry = f"{i + 1}. {track.title}"[:100]
            if needle in entry.lower():
                result.append(entry)
                if len(result) == AUTOCOMPLETE_LIMIT:
                    break  # Discord shows 25; a long queue would build the rest for nothing.
        return result

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Clears a deferred command reply from a request channel once its answer lands."""
        if (
            after.guild
            and before.flags.loading
            and not after.flags.loading
            and after.interaction_metadata is not None
            and request.is_request_channel(after.guild.id, after.channel.id)
        ):
            await delete_quietly(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Handles a request channel's traffic, and tracks chat weight everywhere else.

        One listener rather than two: py-cord runs them concurrently, so a consumed request would
        otherwise still add chat weight and schedule a relocation for a message that is gone. The
        card in a request channel never moves, so nothing there is weighed at all.
        """
        if not message.guild:
            return
        in_request_channel = request.is_request_channel(message.guild.id, message.channel.id)
        if in_request_channel and message.interaction_metadata is not None:
            # A deferred reply waits for `on_message_edit`: deleting its placeholder breaks the answer.
            if not message.flags.loading:
                await delete_quietly(message)
            return
        if message.author.id == self.client.user.id:
            # Own messages never hide the card: log toasts self-delete in 5s and the card itself is exempt.
            return
        if in_request_channel:
            await self._handle_request(message)
            return
        self._track_chat_weight(message)

    async def _handle_request(self, message: discord.Message) -> None:
        """
        Treats a message in the request channel as a track to queue, then clears it away.

        Marked while it resolves, then deleted as soon as its outcome is posted, whether that is a
        toast or the picker for a typed name that matched several tracks. Anything that is not a
        request is simply removed.

        Args:
            message (:class:`Message`): The message posted in the bound request channel.
        """
        if message.type not in (discord.MessageType.default, discord.MessageType.reply) or (
            message.author.bot or message.webhook_id
        ):
            await delete_quietly(message)
            return
        guild_id = message.guild.id
        request.prime(self.client, guild_id)
        if self._request_cooldown.get_bucket(message).update_rate_limit():
            await delete_quietly(message)
            if not self._cooldown_warn.get_bucket(message).update_rate_limit():
                await music_log(
                    guild_id,
                    f"{emoji.error} {message.author.mention} slow down a moment.",
                    color=config.color.red,
                )
            return
        query = message.content.strip()
        if not query:
            await delete_quietly(message)
            await music_log(
                guild_id,
                f"{emoji.error} {message.author.mention} send a track name or a link to queue it.",
                color=config.color.red,
            )
            return
        err = voice_error(message.author)
        if err:
            await self._request_log(message, err, config.color.red)
            await delete_quietly(message)
            return
        try:
            await message.add_reaction(emoji.loading)
        except discord.HTTPException:
            pass  # No Add Reactions: the request still works, it just goes unmarked.
        data, err = await resolve_query(self.client, query)
        if err:
            await self._request_log(message, f"{err} (`{discord.utils.escape_markdown(query)[:80]}`)", config.color.red)
            await delete_quietly(message)
            return
        if not is_link(query) and isinstance(data, list) and len(data) > 1:
            # Nothing is connected yet: the picker resolves the player when a track is chosen.
            picker = TrackPickerView(self.client, message, data)
            picker.msg = await message.channel.send(view=picker)
            await delete_quietly(message)
            return
        player, err, connected_now = await ensure_connected(self.client, message.author)
        if err:
            await self._request_log(message, err, config.color.red)
            await delete_quietly(message)
            return
        try:
            result = await enqueue(self.client, player, data, message.author.id)
        except Exception:
            if connected_now:
                await stop_player(player, message.guild)
            await delete_quietly(message)
            raise
        log_emoji, text = split_log_text(result.content)
        await music_log(guild_id, f"{log_emoji} {message.author.mention} {text}".strip(), color=result.color)
        await delete_quietly(message)
        if not result.started:
            schedule_render(self.client, guild_id)

    @staticmethod
    async def _request_log(message: discord.Message, content: str, color: int | None) -> None:
        """Posts a request failure into the channel, addressed to whoever asked."""
        log_emoji, text = split_log_text(content)
        await music_log(message.guild.id, f"{log_emoji} {message.author.mention} {text}".strip(), color=color)

    def _track_chat_weight(self, message: discord.Message) -> None:
        """
        Relocates the player to the bottom once enough chat has stacked up to push it out of view.

        Each message adds its estimated on-screen height to the guild's chat weight; the player is only re-sent when the total crosses :attr:`relocate_lines` (a single image/embed/long message can cross it alone).
        Light chatter below the threshold leaves the card edited in place, keeping delete/send API calls rare while the lyrics loop is already editing heavily.
        The next track start relocates on any accumulated weight though, so chatter never outlives the track it was posted under.
        """
        play_msg, _ = store.play_msg(message.guild.id)
        if not play_msg or message.channel.id != play_msg.channel.id:
            return
        if store.chat_weight(message.guild.id, self._visual_lines(message), "add") < self.relocate_lines:
            return
        schedule_render(self.client, message.guild.id, delay=RELOCATE_DELAY, force_new=True)

    @classmethod
    def _visual_lines(cls, message: discord.Message) -> int:
        """Estimates how many on-screen chat lines a message occupies."""
        lines = 1
        if message.content:
            lines = sum(len(line) // cls.chars_per_line + 1 for line in message.content.splitlines()) or 1
        blocks = len(message.attachments) + len(message.embeds) + len(message.stickers)
        return lines + blocks * cls.block_lines

    @staticmethod
    async def _play_reply(ctx: discord.ApplicationContext, content: str, color: int | None, quiet: bool) -> None:
        """Answers `/play` ephemerally in a request channel, publicly anywhere else."""
        if quiet:
            await reply(ctx, content, color=color)
        else:
            await ctx.respond(view=container(content, color))

    async def _abandon_play(
        self, player: SquarePlayer, guild: discord.Guild, connected_now: bool, claimed: bool
    ) -> None:
        """Undoes what a failed `/play` set up, so the next one starts from a clean slate."""
        if connected_now:
            await stop_player(player, guild)
        elif claimed and not player.current:
            store.play_ch(guild.id, None, "set")

    # Play
    @slash_command(name="play")
    @option("query", description="Enter your track name/link or playlist link", autocomplete=search)
    async def play(self, ctx: discord.ApplicationContext, query: str):
        """Searches and plays a track from a given query."""
        bound = request.channel_id(ctx.guild.id)
        if bound is not None and ctx.channel.id != bound:
            await ctx.respond(
                view=container(f"{emoji.error} Play tracks from <#{bound}>.", config.color.red), ephemeral=True
            )
            return
        quiet = bound is not None
        await ctx.defer(ephemeral=quiet)
        if quiet:
            request.prime(self.client, ctx.guild.id)
        search = asyncio.create_task(resolve_query(self.client, query))
        player, err, connected_now = await ensure_connected(self.client, ctx.author)
        if err:
            search.cancel()
            await self._play_reply(ctx, err, config.color.red, quiet)
            return
        # Not keyed on `connected_now`: a 24/7 bot is already connected when a session starts.
        claimed = not quiet and store.play_ch(ctx.guild.id) is None
        if claimed:
            store.play_ch(ctx.guild.id, ctx.channel, "set")
        try:
            result = await resolve_and_enqueue(self.client, player, search, ctx.author.id)
        except Exception:
            await self._abandon_play(player, ctx.guild, connected_now, claimed)
            raise
        if not result.ok:
            await self._play_reply(ctx, result.content, result.color, quiet)
            await self._abandon_play(player, ctx.guild, connected_now, claimed)
            return
        if quiet:
            await slash_log(ctx, result.content, color=result.color, render=False)
        else:
            await ctx.respond(view=container(result.content, result.color))
        # Only a bound card lists what is up next, so only it changes when a track is queued.
        if not result.started and request.setup_mode(ctx.guild.id):
            schedule_render(self.client, ctx.guild.id)

    # Now playing
    @slash_command(name="now-playing")
    async def now_playing(self, ctx: discord.ApplicationContext):
        """Shows currently playing track."""
        player = await self.ensure_voice(ctx)
        duration: str = ""
        bar: str = ""
        if player:
            requester = ctx.guild.get_member(requester_id(player, player.current) or 0)
            if player.current.is_stream:
                duration = f"{emoji.live} LIVE"
            else:
                bar = MusicContainer.progress_bar(player)
                duration = datetime.timedelta(milliseconds=player.current.length)
                duration = format_timedelta(duration, locale="en")
            view = DesignerView(
                ui.Container(
                    ui.Section(
                        ui.TextDisplay(f"## [{player.current.title}]({player.current.uri})"),
                        ui.TextDisplay(
                            f"{emoji.user} **Requested By**: {requester.mention if requester else 'Unknown'}\n"
                            f"{emoji.mic} **Artist**: {get_source(player.current.source_name)['emoji']} {player.current.author}\n"
                            f"{emoji.duration} **Duration**: {duration}\n"
                            f"{emoji.voice} **Volume**: `{player.volume}%`\n"
                            f"{emoji.loop} **Loop**: {LOOP_LABELS[player.queue_mode]}\n"
                            f"{emoji.shuffle} **Shuffle**: {'Enabled' if player.shuffled else 'Disabled'}\n"
                            f"{emoji.autoplay} **Autoplay**: {'Enabled' if player.autoplay_on else 'Disabled'}\n"
                            f"{emoji.equalizer} **Equalizers**: {', '.join(EQ_PRESETS[name].label for name in player.presets) or 'None'}"
                            f"{f'\n\n {bar}' if bar else ''}"
                        ),
                        accessory=ui.Thumbnail(url=player.current.artwork) if player.current.artwork else None,
                    )
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # DJ
    @slash_command(name="dj")
    @discord.default_permissions(manage_guild=True)
    async def dj_settings(self, ctx: discord.ApplicationContext):
        """Manages who may use the playback controls."""
        enabled, role_ids = await fetch_dj(ctx.guild.id)
        await ctx.respond(view=DJView(ctx, enabled, role_ids), ephemeral=True)

    # Equalizer slash cmd group
    eq = SlashCommandGroup(name="eq", description="Equalizer commands.")

    async def _apply_preset(self, ctx: discord.ApplicationContext, name: str):
        """Turns a preset on, swapping out whichever active one drives the same filter."""
        player = await self.ensure_voice(ctx)
        if not player:
            return
        preset = EQ_PRESETS[name]
        replaced = [n for n in player.presets if n != name and EQ_PRESETS[n].slot == preset.slot]
        for n in replaced:
            del player.presets[n]
        player.presets[name] = preset.filters
        await player.apply_presets()
        swap = f", replacing **{EQ_PRESETS[replaced[0]].label}**" if replaced else ""
        await slash_log(ctx, f"{emoji.equalizer} Applied **{preset.label}** equalizer{swap}.")

    @eq.command(name="reset")
    async def reset(self, ctx: discord.ApplicationContext):
        """Resets the equalizer to default."""
        player = await self.ensure_voice(ctx)
        if player:
            player.presets.clear()
            await player.apply_presets()
            await slash_log(ctx, f"{emoji.equalizer} Reset equalizer to default settings.")

    async def filter_autocomplete(self, ctx: discord.AutocompleteContext):
        """Offers the active presets by name."""
        player = get_player(self.client, ctx.interaction.guild_id)
        if not player:
            return []
        needle = ctx.value.lower()
        return [
            discord.OptionChoice(name=EQ_PRESETS[n].label, value=n)
            for n in player.presets
            if needle in EQ_PRESETS[n].label.lower()
        ]

    @eq.command(name="remove")
    @option("name", description="Name of the equalizer to remove.", autocomplete=filter_autocomplete)
    async def remove_eq(self, ctx: discord.ApplicationContext, name: str):
        """Removes an equalizer by name."""
        player = await self.ensure_voice(ctx)
        if player:
            if name in player.presets:
                del player.presets[name]
                await player.apply_presets()
                await slash_log(ctx, f"{emoji.equalizer} Removed **{EQ_PRESETS[name].label}** equalizer.")
            else:
                await reply(ctx, f"{emoji.error} **{name}** equalizer not found.", color=config.color.red)

    @eq.command(name="bassboost")
    async def eq_bassboost(self, ctx: discord.ApplicationContext):
        """Boosts the low end."""
        await self._apply_preset(ctx, "bassboost")

    @eq.command(name="nightcore")
    async def eq_nightcore(self, ctx: discord.ApplicationContext):
        """Speeds the track up and raises its pitch."""
        await self._apply_preset(ctx, "nightcore")

    @eq.command(name="vaporwave")
    async def eq_vaporwave(self, ctx: discord.ApplicationContext):
        """Slows the track down and lowers its pitch."""
        await self._apply_preset(ctx, "vaporwave")

    @eq.command(name="8d")
    async def eq_8d(self, ctx: discord.ApplicationContext):
        """Pans the audio around your head. Best with headphones."""
        await self._apply_preset(ctx, "8d")

    @eq.command(name="karaoke")
    async def eq_karaoke(self, ctx: discord.ApplicationContext):
        """Strips out the lead vocals."""
        await self._apply_preset(ctx, "karaoke")

    @eq.command(name="soft")
    async def eq_soft(self, ctx: discord.ApplicationContext):
        """Mellows out the highs for a muffled, softer sound."""
        await self._apply_preset(ctx, "soft")

    @eq.command(name="tremolo")
    async def eq_tremolo(self, ctx: discord.ApplicationContext):
        """Makes the volume pulse."""
        await self._apply_preset(ctx, "tremolo")

    @eq.command(name="vibrato")
    async def eq_vibrato(self, ctx: discord.ApplicationContext):
        """Makes the pitch wobble."""
        await self._apply_preset(ctx, "vibrato")

    # Stop
    @slash_command(name="stop")
    async def stop(self, ctx: discord.ApplicationContext):
        """Stops the music and clears the queue."""
        await ctx.defer(ephemeral=True)
        player = await self.ensure_voice(ctx)
        if player:
            await asyncio.gather(
                slash_log(ctx, f"{emoji.stop} {stop_verb(ctx.guild.id).capitalize()} the player.", render=False),
                stop_player(player, ctx.guild),
            )

    # Seek
    @slash_command(name="seek")
    @option("duration", description="How far to jump, forwards or backwards. Ex: 10s, +1m, -30s, -1m20s etc....")
    async def seek(self, ctx: discord.ApplicationContext, duration: str):
        """Seeks forwards or backwards in the current track."""
        player = await self.ensure_voice(ctx)
        if player:
            if player.current.is_stream:
                await reply(ctx, f"{emoji.error} Can't seek a live stream.", color=config.color.red)
                return
            timedelta = parse_duration(duration, signed=True)
            offset_ms = timedelta.total_seconds() * 1000
            track_time = int(player.position + offset_ms)
            if track_time >= player.current.length:
                await self.skip(ctx=ctx)
                return
            track_time = max(0, track_time)
            await player.seek(track_time)
            start_lyrics(self.client, ctx.guild.id)
            await slash_log(
                ctx,
                f"{emoji.rewind if offset_ms < 0 else emoji.forward} Moved track to `{fmt_time(track_time)}`.",
            )

    # Skip
    @slash_command(name="skip")
    async def skip(self, ctx: discord.ApplicationContext):
        """Skips the current playing track, or opens a vote when you aren't a DJ."""
        player = await self.ensure_voice(ctx)
        if player:
            await request_skip(ctx, player)

    # Skip to
    @slash_command(name="skip-to")
    @option("track", description="Enter your track index number to skip", autocomplete=track_autocomplete)
    async def skip_to(self, ctx: discord.ApplicationContext, track: str):
        """Skips to a given track in the queue."""
        player = await self.ensure_voice(ctx, need_queue=True)
        if player:
            index = await self._queue_index(ctx, player, track)
            if index is not None:
                await ctx.defer(ephemeral=True)
                await player.skip_to(index)
                await slash_log(ctx, f"{emoji.skip} Skipped to track `{index + 1}`.", render=False)

    # Pause
    @slash_command(name="pause")
    async def pause(self, ctx: discord.ApplicationContext):
        """Pauses the player."""
        player = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                await reply(ctx, f"{emoji.error} Player is already paused.", color=config.color.red)
            else:
                await ctx.defer(ephemeral=True)
                await player.pause()
                await slash_log(ctx, f"{emoji.pause} Player paused.")

    # Resume
    @slash_command(name="resume")
    async def resume(self, ctx: discord.ApplicationContext):
        """Resumes the player."""
        player = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                await ctx.defer(ephemeral=True)
                await player.resume()
                await slash_log(ctx, f"{emoji.play} Player resumed.")
            else:
                await reply(ctx, f"{emoji.error} Player isn't paused.", color=config.color.red)

    # Volume
    @slash_command(name="volume")
    @option("volume", description="Enter your volume amount from 1 - 100", min_value=1, max_value=100)
    async def volume(self, ctx: discord.ApplicationContext, volume: int):
        """Changes the player's volume 1 - 100."""
        player = await self.ensure_voice(ctx)
        if player:
            await player.set_volume(volume)
            await slash_log(ctx, f"{emoji.voice} Volume changed to `{player.volume}%`.")

    # Queue
    @slash_command(name="queue")
    @option("page", description="Enter queue page number", default=1, required=False, min_value=1)
    async def queue(self, ctx: discord.ApplicationContext, page: int = 1):
        """Shows the player's queue."""
        player = await self.ensure_voice(ctx)
        if player and await self._check_page(ctx, page, len(player.queue)):
            await ctx.respond(view=QueueListView(client=self.client, source=ctx, page=page), ephemeral=True)

    # History
    @slash_command(name="history")
    @option("page", description="Enter history page number", default=1, required=False, min_value=1)
    async def history(self, ctx: discord.ApplicationContext, page: int = 1):
        """Shows the tracks played so far, newest first."""
        player = await self.ensure_voice(ctx)
        if player:
            tracks = history_tracks(player)
            if not tracks:
                await reply(ctx, f"{emoji.error} Nothing has been played yet.", color=config.color.red)
            elif await self._check_page(ctx, page, len(tracks)):
                await ctx.respond(view=HistoryListView(client=self.client, source=ctx, page=page), ephemeral=True)

    # Clear queue
    @slash_command(name="clear-queue")
    async def clear_queue(self, ctx: discord.ApplicationContext):
        """Clears the player's queue."""
        player = await self.ensure_voice(ctx, need_queue=True)
        if player:
            player.queue.clear()
            await slash_log(ctx, f"{emoji.success} Cleared the queue.", color=config.color.green)

    # Shuffle
    @slash_command(name="shuffle")
    async def shuffle(self, ctx: discord.ApplicationContext):
        """Toggle shuffle for the player's queue."""
        player = await self.ensure_voice(ctx, need_queue=True)
        if player:
            await ctx.defer(ephemeral=True)
            shuffled = player.toggle_shuffle()
            await slash_log(ctx, f"{emoji.shuffle} {'Enabled' if shuffled else 'Disabled'} shuffle.")

    # Autoplay
    @slash_command(name="autoplay")
    async def autoplay(self, ctx: discord.ApplicationContext):
        """Toggles autoplay."""
        player = await self.ensure_voice(ctx)
        if player:
            enabled = player.toggle_autoplay()
            await slash_log(ctx, f"{emoji.autoplay} {'Enabled' if enabled else 'Disabled'} autoplay.")

    # Loop
    @slash_command(name="loop")
    @option("mode", description="Enter loop mode", choices=list(loop_modes))
    async def loop(self, ctx: discord.ApplicationContext, mode: str):
        """Loops the current track or the whole queue."""
        player = await self.ensure_voice(ctx, need_queue=mode == "Queue")
        if player:
            await ctx.defer(ephemeral=True)
            player.queue_mode = self.loop_modes[mode]
            await slash_log(ctx, f"{loop_emoji(player.queue_mode)} {loop_action(player.queue_mode).capitalize()}.")

    # Remove
    @slash_command(name="remove")
    @option("track", description="Select the track to remove", autocomplete=track_autocomplete)
    async def remove(self, ctx: discord.ApplicationContext, track: str):
        """Removes a track from the player's queue with the given index."""
        player = await self.ensure_voice(ctx, need_queue=True)
        if player:
            index = await self._queue_index(ctx, player, track)
            if index is not None and await dj.require_dj(ctx, player, track=player.queue[index]):
                removed = player.queue.remove_at(index)
                await slash_log(ctx, f"{emoji.remove} Removed **{removed.title}**.", color=config.color.red)


def setup(client: Client):
    client.add_cog(Music(client))
