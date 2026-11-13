import asyncio
import discord
import logging
import re
import sonolink
import time
from discord.ext import commands, tasks
from square.core import Client
from square.music import request, stay, store
from square.music.core import (
    SquarePlayer,
    fetch_node_info,
    get_player,
    session_lock,
)
from square.music.play import (
    TrackPickerView,
    enqueue,
    ensure_connected,
    is_link,
    resolve_query,
    voice_error,
)
from square.music.player import (
    RELOCATE_DELAY,
    cancel_vote,
    cleanup_guild,
    discard_stale,
    release_guild,
    render_player,
    repaint_deleted_card,
    schedule_render,
    set_track_status,
    skip_or_stop,
    start_progress,
    stop_player,
)
from square.music.utils import delete_quietly, music_log, split_log_text
from square.utils import config
from square.utils.emoji import emoji

log = logging.getLogger(__name__)
KICK_GRACE = 2.0
_reaping: set[asyncio.Task] = set()  # Strong refs: the loop only holds weak ones, so a sleeping task can be collected
FAILOVER_INTERVAL = 5.0


_NO_CAUSE = "All clients failed to load the item."


def _cause(message: str | None) -> str | None:
    if not message:
        return None
    line = re.sub(r"^\([^)]*\)\s*", "", message.strip()).split("\n", 1)[0].strip()
    return None if line == _NO_CAUSE else line[:200] or None


class Listeners:
    client: Client

    @commands.Cog.listener()
    async def on_connect(self):
        await self.client.sonolink.start()
        if not self.failover.is_running():
            self.failover.start()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._adopting and not self._adopting.done():
            return  # A resume re-fires this; two adoption sweeps would each post a card.
        await request.seed()
        await stay.seed()
        self._adopting = self.client.loop.create_task(request.adopt_all(self.client))
        self._join_stay_channels()

    def _join_stay_channels(self) -> None:
        if self._staying and not self._staying.done():
            return
        self._staying = self.client.loop.create_task(stay.join_all(self.client))

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
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
        if payload.guild_id:
            await repaint_deleted_card(self.client, payload.guild_id, {payload.message_id})

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if payload.guild_id:
            await repaint_deleted_card(self.client, payload.guild_id, payload.message_ids)

    @commands.Cog.listener()
    async def on_sonolink_node_ready(self, event: sonolink.gateway.ReadyEvent):
        node = event.node
        _, latency = await fetch_node_info(node)
        log.info("Node %s connected · %s%s", node.id, latency, " · resumed" if event.resumed else "")
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
                return
            try:
                await player.move_to(node)
            except Exception as exc:
                log.warning("Failover to node %s failed: %s", node.id, exc)
                continue
            await music_log(player.guild.id, f"{emoji.reload} Switched to a backup music server.")

    @commands.Cog.listener()
    async def on_sonolink_node_close(self, node: sonolink.Node):
        log.warning("Node %s disconnected, reconnecting", node.id)

    @commands.Cog.listener()
    async def on_sonolink_track_start(self, player: SquarePlayer, event: sonolink.gateway.TrackStartEvent):
        guild_id = player.guild.id
        if not await player.settle(event.track, time.monotonic()):
            return
        relocate = store.chat_weight(guild_id) > 0
        if relocate:
            pending = store.render_task(guild_id)
            if pending and not pending.done():
                pending.cancel()
        await cancel_vote(guild_id)
        await asyncio.gather(
            render_player(self.client, guild_id, force_new=relocate), set_track_status(player), return_exceptions=True
        )
        start_progress(self.client, guild_id)

    @commands.Cog.listener()
    async def on_sonolink_track_end(self, player: SquarePlayer, event: sonolink.gateway.TrackEndEvent):
        if event.reason not in (sonolink.TrackEndReason.FINISHED, sonolink.TrackEndReason.LOAD_FAILED):
            return
        if player.current is None and not len(player.queue):
            guild = self.client.get_guild(player.guild.id)
            if guild:
                await stop_player(player, guild)

    def _report_failure(self, guild_id: int, track: sonolink.models.Playable, reason: str | None) -> None:
        store.record_failure(guild_id, track.title, reason)
        self.client.dispatch("music_update", guild_id)

    @commands.Cog.listener()
    async def on_sonolink_track_exception(self, player: SquarePlayer, event: sonolink.gateway.TrackExceptionEvent):
        track = event.track
        reason = _cause(event.exception.message)
        self._report_failure(player.guild.id, track, reason)
        await music_log(
            player.guild.id,
            f"{emoji.error} Couldn't play [**{track.title}**]({track.uri}).{f'\n-# {reason}' if reason else ''}",
            color=config.color.red,
        )

    @commands.Cog.listener()
    async def on_sonolink_track_stuck(self, player: SquarePlayer, event: sonolink.gateway.TrackStuckEvent):
        track = event.track
        # A track that already moved on was handled by Lavalink, and skipping now would cost the next one.
        if player.current != track:
            return
        self._report_failure(player.guild.id, track, "It stopped sending audio, so it was skipped.")
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
            # Joining or leaving any channel changes whether the dashboard lets this member queue
            if before.channel != after.channel:
                self.client.dispatch("music_update", member.guild.id)
            return
        if before.channel != after.channel:
            # Sonolink only re-checks on track ends and the bot's own voice changes.
            player._check_inactivity()
        self.client.dispatch("music_update", member.guild.id)
        vote = store.skip_vote(member.guild.id)
        if vote:
            await vote.refresh()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles != after.roles and get_player(self.client, after.guild.id):
            self.client.dispatch("music_update", after.guild.id)

    async def _on_bot_voice_update(self, guild: discord.Guild, after: discord.VoiceState) -> None:
        player = get_player(self.client, guild.id)
        if after.channel is None:
            if stay.channel_id(guild.id) is not None:
                stay.schedule_rejoin(self.client, guild.id)
            elif player and not getattr(player, "_square_stopped", False):
                task = self.client.loop.create_task(self._reap_kicked(guild, player))
                _reaping.add(task)
                task.add_done_callback(_reaping.discard)
            return
        if stay.channel_id(guild.id) not in (None, after.channel.id):
            channel = await stay.resolve(guild)
            if channel:
                if player:
                    await stay.move(player, channel)
                return
        if player and player.channel != after.channel:
            player.channel = after.channel
            self.client.dispatch("music_update", guild.id)
            await set_track_status(player)
            vote = store.skip_vote(guild.id)
            if vote:
                await vote.refresh()

    async def _reap_kicked(self, guild: discord.Guild, player: SquarePlayer) -> None:
        # Our own disconnects land here a beat before their teardown does, hence the grace.
        await asyncio.sleep(KICK_GRACE)
        async with session_lock(guild.id):
            if (
                get_player(self.client, guild.id) is player
                and guild.me.voice is None
                and not getattr(player, "_square_stopped", False)
            ):
                await discard_stale(self.client, guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        request.forget(guild.id)
        stay.forget(guild.id)
        cleanup_guild(self.client, guild.id)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
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
            return
        if in_request_channel:
            await self._handle_request(message)
            return
        self._track_chat_weight(message)

    async def _handle_request(self, message: discord.Message) -> None:
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
            pass
        data, err = await resolve_query(self.client, query)
        if err:
            await self._request_log(message, f"{err} (`{discord.utils.escape_markdown(query)[:80]}`)", config.color.red)
            await delete_quietly(message)
            return
        if not is_link(query) and isinstance(data, list) and len(data) > 1:
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
        log_emoji, text = split_log_text(content)
        await music_log(message.guild.id, f"{log_emoji} {message.author.mention} {text}".strip(), color=color)

    def _track_chat_weight(self, message: discord.Message) -> None:
        play_msg, _ = store.play_msg(message.guild.id)
        if not play_msg or message.channel.id != play_msg.channel.id:
            return
        if store.chat_weight(message.guild.id, self._visual_lines(message), "add") < self.relocate_lines:
            return
        schedule_render(self.client, message.guild.id, delay=RELOCATE_DELAY, force_new=True)

    @classmethod
    def _visual_lines(cls, message: discord.Message) -> int:
        lines = 1
        if message.content:
            lines = sum(len(line) // cls.chars_per_line + 1 for line in message.content.splitlines()) or 1
        blocks = len(message.attachments) + len(message.embeds) + len(message.stickers)
        return lines + blocks * cls.block_lines
