import asyncio
import datetime
import discord
import math
import re
import sonolink
from babel.dates import format_timedelta
from discord import ui
from discord.commands import option, slash_command
from discord.ext import commands
from sonolink.models import Playlist
from square.cogs.music.eq import Equalizer
from square.cogs.music.listeners import Listeners
from square.cogs.music.settings import MusicPage
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView
from square.music import dj, request, store
from square.music.core import (
    LOOP_LABELS,
    SquarePlayer,
    fmt_time,
    get_player,
    loop_action,
    loop_emoji,
    register_nodes,
    requester_id,
)
from square.music.filters import EQ_PRESETS
from square.music.history import HistoryListView, history_tracks
from square.music.play import clean_query, ensure_connected, is_link, resolve_and_enqueue, resolve_query, search_tracks
from square.music.player import (
    MusicContainer,
    request_skip,
    schedule_render,
    slash_log,
    start_lyrics,
    stop_player,
    stop_verb,
)
from square.music.queue import QueueListView
from square.music.utils import container, get_source, reply
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import parse_duration

# Discord renders at most this many autocomplete choices, and caps each name and value at 100 characters.
AUTOCOMPLETE_LIMIT = 25
CHOICE_LIMIT = 100
# Matches the five tracks a `/queue` and `/history` page shows.
PAGE_SIZE = 5


class Music(
    Listeners,
    Equalizer,
    Cog,
    name="Music",
    description="Wanna chill? Just play music & enjoy.",
    emoji=emoji.music,
    order=6,
):
    settings_pages = (MusicPage,)
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
        self._adopting: asyncio.Task | None = None
        self._staying: asyncio.Task | None = None
        self._down_nodes: set[str] = set()
        self._request_cooldown = commands.CooldownMapping.from_cooldown(2, 5.0, commands.BucketType.member)
        self._cooldown_warn = commands.CooldownMapping.from_cooldown(1, 15.0, commands.BucketType.member)
        register_nodes(client)

    # Current voice
    def current_voice_channel(self, ctx: discord.ApplicationContext):
        if ctx.guild and ctx.guild.me.voice:
            return ctx.guild.me.voice.channel
        return None

    # Unloading cog
    def cog_unload(self):
        self.failover.cancel()

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
