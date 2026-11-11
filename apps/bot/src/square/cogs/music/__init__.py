import asyncio
import discord
import math
import re
import sonolink
from collections.abc import Awaitable
from discord import ui
from discord.commands import option, slash_command
from discord.ext import commands
from sonolink.models import Playlist
from square import imaging
from square.cogs.music.eq import Equalizer
from square.cogs.music.listeners import Listeners
from square.cogs.music.settings import MusicPage
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView
from square.imaging import assets
from square.imaging.templates import now_playing as track_card
from square.music import controls, request
from square.music.core import (
    LOOP_LABELS,
    SquarePlayer,
    fmt_time,
    get_player,
    register_nodes,
    requester_id,
)
from square.music.errors import MusicError
from square.music.filters import EQ_PRESETS
from square.music.history import HistoryListView, history_tracks
from square.music.play import clean_query, is_link, search_tracks
from square.music.player import slash_log
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
        self.failover.stop()

    # Ensures voice parameters
    async def ensure_voice(self, ctx: discord.ApplicationContext) -> SquarePlayer | None:
        """
        The player, for commands that only show it.

        Controls, `/play` included, go through :mod:`square.music.controls` instead.

        Args:
            ctx (:class:`ApplicationContext`): The invoking command.
        """
        try:
            return controls.require_player(ctx.guild, ctx.author)
        except MusicError as exc:
            await reply(ctx, f"{emoji.error} {exc}", color=config.color.red)
            return None

    async def _control(self, ctx: discord.ApplicationContext, action: Awaitable[str]) -> None:
        """Runs a control for a slash command and answers privately with how it went."""
        await ctx.defer(ephemeral=True)
        try:
            await reply(ctx, await action)
        except MusicError as exc:
            await reply(ctx, f"{emoji.error} {exc}", color=config.color.red)

    @staticmethod
    def _queue_index(track: str) -> int:
        """
        Reads a queue position from an autocomplete pick (`3. Title`) or a typed number, as a zero-based index.

        Anything unreadable comes back as -1, which the control refuses with the valid range.
        """
        match = re.match(r"\s*(\d+)", track)
        return int(match[1]) - 1 if match else -1

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
        try:
            result = await controls.play(self.client, ctx.guild, ctx.author, query, channel=ctx.channel)
        except MusicError as exc:
            await self._play_reply(ctx, f"{emoji.error} {exc}", config.color.red, quiet)
            return
        if quiet:
            await slash_log(ctx, result.content, color=result.color, render=False)
        else:
            await ctx.respond(view=container(result.content, result.color))

    # Now playing
    @slash_command(name="now-playing")
    async def now_playing(self, ctx: discord.ApplicationContext):
        """Shows currently playing track."""
        player = await self.ensure_voice(ctx)
        if not player:
            return
        await ctx.defer(ephemeral=True)
        track = player.current
        requester = ctx.guild.get_member(requester_id(player, track) or 0)
        up_next = player.queue[0] if len(player.queue) else None
        artwork, next_artwork, avatar = await asyncio.gather(
            assets.fetch_url(track.artwork),
            assets.fetch_url(up_next.artwork if up_next else None),
            assets.fetch(requester.display_avatar if requester else None, 64),
        )
        data = track_card.NowPlaying(
            title=track.title,
            author=track.author,
            source=track.source_name or "",
            artwork=artwork,
            requester=requester.display_name if requester else None,
            requester_avatar=avatar,
            progress=0 if track.is_stream or not track.length else player.position / track.length,
            elapsed=fmt_time(player.position),
            duration=fmt_time(track.length),
            stream=track.is_stream,
            paused=player.paused,
            volume=player.volume,
            loop=LOOP_LABELS[player.queue_mode],
            shuffle=player.shuffled,
            autoplay=player.autoplay_on,
            filters=[EQ_PRESETS[name].label for name in player.presets],
            up_next=f"{up_next.title} by {up_next.author}" if up_next else None,
            up_next_artwork=next_artwork,
            queued=len(player.queue),
        )
        file = await imaging.render(track_card.build, data, filename="now-playing.png")
        alt = f"Now playing {track.title} by {track.author}" + (
            ", live" if track.is_stream else f", {data.elapsed} of {data.duration}"
        )
        view = DesignerView(
            ui.Container(ui.MediaGallery(discord.MediaGalleryItem("attachment://now-playing.png", description=alt)))
        )
        if track.uri:
            view.add_item(
                ui.ActionRow(
                    ui.Button(
                        label=f"Open on {track_card.source_label(data.source)}",
                        emoji=get_source(track.source_name)["emoji"],
                        style=discord.ButtonStyle.link,
                        url=track.uri,
                    )
                )
            )
        await ctx.respond(view=view, file=file, ephemeral=True)

    # Stop
    @slash_command(name="stop")
    async def stop(self, ctx: discord.ApplicationContext):
        """Stops the music and clears the queue."""
        await self._control(ctx, controls.stop(ctx.guild, ctx.author))

    # Seek
    @slash_command(name="seek")
    @option("duration", description="How far to jump, forwards or backwards. Ex: 10s, +1m, -30s, -1m20s etc....")
    async def seek(self, ctx: discord.ApplicationContext, duration: str):
        """Seeks forwards or backwards in the current track."""
        offset_ms = int(parse_duration(duration, signed=True).total_seconds() * 1000)
        await self._control(ctx, controls.seek_by(ctx.guild, ctx.author, offset_ms))

    # Skip
    @slash_command(name="skip")
    async def skip(self, ctx: discord.ApplicationContext):
        """Skips the current playing track, or opens a vote when you aren't a DJ."""
        await self._control(ctx, controls.skip(ctx.guild, ctx.author, channel=ctx.channel))

    # Skip to
    @slash_command(name="skip-to")
    @option("track", description="Enter your track index number to skip", autocomplete=track_autocomplete)
    async def skip_to(self, ctx: discord.ApplicationContext, track: str):
        """Skips to a given track in the queue."""
        await self._control(ctx, controls.jump(ctx.guild, ctx.author, self._queue_index(track)))

    # Pause
    @slash_command(name="pause")
    async def pause(self, ctx: discord.ApplicationContext):
        """Pauses the player."""
        await self._control(ctx, controls.set_paused(ctx.guild, ctx.author, True))

    # Resume
    @slash_command(name="resume")
    async def resume(self, ctx: discord.ApplicationContext):
        """Resumes the player."""
        await self._control(ctx, controls.set_paused(ctx.guild, ctx.author, False))

    # Volume
    @slash_command(name="volume")
    @option("volume", description="Enter your volume amount from 1 - 100", min_value=1, max_value=100)
    async def volume(self, ctx: discord.ApplicationContext, volume: int):
        """Changes the player's volume 1 - 100."""
        await self._control(ctx, controls.set_volume(ctx.guild, ctx.author, volume))

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
        await self._control(ctx, controls.clear_queue(ctx.guild, ctx.author))

    # Shuffle
    @slash_command(name="shuffle")
    async def shuffle(self, ctx: discord.ApplicationContext):
        """Toggle shuffle for the player's queue."""
        await self._control(ctx, controls.set_shuffle(ctx.guild, ctx.author))

    # Autoplay
    @slash_command(name="autoplay")
    async def autoplay(self, ctx: discord.ApplicationContext):
        """Toggles autoplay."""
        await self._control(ctx, controls.set_autoplay(ctx.guild, ctx.author))

    # Loop
    @slash_command(name="loop")
    @option("mode", description="Enter loop mode", choices=list(loop_modes))
    async def loop(self, ctx: discord.ApplicationContext, mode: str):
        """Loops the current track or the whole queue."""
        await self._control(ctx, controls.set_loop(ctx.guild, ctx.author, self.loop_modes[mode]))

    # Remove
    @slash_command(name="remove")
    @option("track", description="Select the track to remove", autocomplete=track_autocomplete)
    async def remove(self, ctx: discord.ApplicationContext, track: str):
        """Removes a track from the player's queue with the given index."""
        await self._control(ctx, controls.remove(ctx.guild, ctx.author, self._queue_index(track)))


def setup(client: Client):
    client.add_cog(Music(client))
