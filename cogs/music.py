import asyncio
import datetime
import discord
import math
import re
import sonolink
from babel.dates import format_timedelta
from core import Client
from core.view import DesignerView
from discord import SlashCommandGroup, ui
from discord.commands import option, slash_command
from discord.ext import commands
from music import store
from music.core import (
    SquarePlayer,
    fetch_node_info,
    fmt_time,
    get_player,
    register_nodes,
    requester_id,
    tag_requester,
)
from music.filters import EqPresets
from music.player import cleanup_guild, render_player, skip_or_stop, slash_log, start_lyrics, stop_player
from music.queue import QueueListView
from music.utils import container, get_source, music_log, reply
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from sonolink.models import Playlist
from utils import config
from utils.emoji import emoji
from utils.helpers import parse_duration

console = Console()


class Music(commands.Cog):
    # Regex matching URLs so plain queries get a search source instead.
    url_rx = re.compile("https?:\\/\\/(?:www\\.)?.+")
    # Estimated on-screen chat lines an attachment/embed/sticker occupies - tall enough that one big block relocates the player on its own.
    block_lines = 10
    # Characters per rendered chat line, used to estimate wrapping of long messages.
    chars_per_line = 60
    # Relocate the player once this many estimated chat lines have stacked below it.
    relocate_lines = 10

    def __init__(self, client: Client):
        self.client = client
        self._node_live: Live | None = None
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

    @commands.Cog.listener()
    async def on_sonolink_node_close(self, node: sonolink.Node):
        text = Text()
        text.append("✗ Disconnected from Lavalink ", style="red")
        text.append(node.id, style="cyan")
        self._finish_spinner(text)
        self._start_spinner("Reconnecting to Lavalink...")

    @commands.Cog.listener()
    async def on_sonolink_track_start(self, player: SquarePlayer, event: sonolink.gateway.TrackStartEvent):
        guild_id = player.guild.id
        track = player.current
        if track is None:
            return
        coros = [render_player(self.client, guild_id)]
        if player.channel is not None:
            coros.append(player.channel.set_status(status=f"Playing **{track.title}**"))
        if track.autoplay:
            coros.append(
                music_log(
                    guild_id,
                    f"{emoji.autoplay} Autoplay queued [**{track.title}** by **{track.author}**]({track.uri}).",
                )
            )
        await asyncio.gather(*coros, return_exceptions=True)
        start_lyrics(self.client, guild_id)

    @commands.Cog.listener()
    async def on_sonolink_track_end(self, player: SquarePlayer, event: sonolink.gateway.TrackEndEvent):
        if event.reason not in (sonolink.TrackEndReason.FINISHED, sonolink.TrackEndReason.LOAD_FAILED):
            return
        if player.current is None and not len(player.queue.tracks):
            guild = self.client.get_guild(player.guild.id)
            if guild:
                await stop_player(player, guild)

    @commands.Cog.listener()
    async def on_sonolink_track_exception(self, player: SquarePlayer, event: sonolink.gateway.TrackExceptionEvent):
        await music_log(
            player.guild.id,
            f"{emoji.error} An error occurred while playing the track.",
            color=config.color.red,
        )

    @commands.Cog.listener()
    async def on_sonolink_track_stuck(self, player: SquarePlayer, event: sonolink.gateway.TrackStuckEvent):
        await music_log(
            player.guild.id,
            f"{emoji.error} Track is stuck.",
            color=config.color.red,
        )

    @commands.Cog.listener()
    async def on_sonolink_player_disconnect(self, player: SquarePlayer, event: sonolink.PlayerDisconnectEvent):
        """Single cleanup funnel: fires for manual stops, inactivity, kicks, and node errors."""
        guild = self.client.get_guild(player.guild.id)
        if guild is None:
            cleanup_guild(player.guild.id)
            return
        if event.trigger is sonolink.DisconnectTriggerType.INACTIVITY:
            channel = player.channel
            await music_log(
                guild.id,
                f"{emoji.remove} Left {channel.mention if channel else 'the voice channel'} due to inactivity.",
                color=config.color.red,
            )
        await stop_player(player, guild)

    # Current voice
    def current_voice_channel(self, ctx: discord.ApplicationContext):
        if ctx.guild and ctx.guild.me.voice:
            return ctx.guild.me.voice.channel
        return None

    # Unloading cog
    def cog_unload(self):
        if self._node_live and self._node_live.is_started:
            self._node_live.stop()
            self._node_live = None

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        cleanup_guild(guild.id)

    # Ensures voice parameters
    async def ensure_voice(self, ctx: discord.ApplicationContext) -> SquarePlayer | None:
        """Checks all the voice parameters."""

        def _err(text: str) -> DesignerView:
            return DesignerView(ui.Container(ui.TextDisplay(text), color=config.color.red))

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond(view=_err(f"{emoji.error} Join a voice channel first."), ephemeral=True)
            return None

        player = get_player(self.client, ctx.guild.id)
        bot_channel = self.current_voice_channel(ctx)

        if ctx.command.name == "play":
            if player is None or bot_channel is None:
                if bot_channel is not None and ctx.author.voice.channel != bot_channel:
                    await ctx.respond(view=_err(f"{emoji.error} You are not in my voice channel."), ephemeral=True)
                    return None
                permissions = ctx.author.voice.channel.permissions_for(ctx.me)
                if not permissions.connect or not permissions.speak:
                    await ctx.respond(
                        view=_err(f"{emoji.error} I need the `Connect` and `Speak` permissions."), ephemeral=True
                    )
                    return None
                if ctx.guild.voice_client:
                    await ctx.guild.voice_client.disconnect(force=True)
                player = await ctx.author.voice.channel.connect(cls=SquarePlayer)
                store.play_ch(ctx.guild.id, ctx.channel, "set")
            elif ctx.author.voice.channel != bot_channel:
                await ctx.respond(view=_err(f"{emoji.error} You are not in my voice channel."), ephemeral=True)
                return None
        else:
            if player is None or bot_channel is None or (not player.current and ctx.command.name != "stop"):
                await ctx.respond(
                    view=_err(f"{emoji.error} Nothing is being played at the current moment."), ephemeral=True
                )
                return None
            if ctx.author.voice.channel != bot_channel:
                await ctx.respond(view=_err(f"{emoji.error} You are not in my voice channel."), ephemeral=True)
                return None

        return player

    # Search autocomplete
    async def search(self, ctx: discord.AutocompleteContext):
        """Searches a track from a given query."""
        tracks = []
        if re.match(self.url_rx, ctx.value):
            return tracks
        query = ctx.value if ctx.value != "" else "top tracks"
        result = await self.client.sonolink.search_track(query, source=sonolink.TrackSourceType.YOUTUBE_MUSIC)
        if result.is_error() or result.is_empty() or result.result is None:
            return tracks
        data = result.result
        found = data.tracks if isinstance(data, Playlist) else data if isinstance(data, list) else [data]
        for track in found:
            dur = fmt_time(track.length)
            max_len = 100
            dur_str = dur
            author = track.author
            title = track.title
            reserved = len(author) + len(dur_str) + 6  # " - " x2 and possible "..."
            max_title_len = max(0, max_len - reserved)
            if len(title) > max_title_len:
                title = title[: max_title_len - 3] + "..."
            track_name = f"{author} - {title} - {dur_str}"
            tracks.append(track_name)
        return tracks

    # Track autocomplete
    async def track_autocomplete(self, ctx: discord.AutocompleteContext):
        """Provides track indices for removal."""
        player = get_player(self.client, ctx.interaction.guild_id)
        if not player or not len(player.queue.tracks):
            return []
        result = []
        for i, track in enumerate(player.queue.tracks):
            title = track.title
            full_entry = f"{i + 1}. {title}"
            entry = full_entry[:100]
            if ctx.value.lower() in entry.lower():
                result.append(entry)
        return result

    # Track chat after the player so it can be relocated to the bottom
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Relocates the player to the bottom once enough chat has stacked up to push it out of view.

        Each message adds its estimated on-screen height to the guild's chat weight; the player is only re-sent when the total crosses :attr:`relocate_lines` (a single image/embed/long message can cross it alone).
        Light chatter below the threshold leaves the card edited in place, keeping delete/send API calls rare while the lyrics loop is already editing heavily.
        """
        if not message.guild:
            return
        if message.author.id == self.client.user.id:
            # Own messages never hide the card: log toasts self-delete in 5s and the card itself is exempt.
            return
        play_msg, _ = store.play_msg(message.guild.id)
        if not play_msg or message.channel.id != play_msg.channel.id:
            return
        if store.chat_weight(message.guild.id, self._visual_lines(message), "add") < self.relocate_lines:
            return
        pending = store.render_task(message.guild.id)
        if pending and not pending.done():
            # A relocation is already scheduled - let it fire instead of pushing it back on every message.
            return

        async def _relocate(guild_id: int = message.guild.id):
            await asyncio.sleep(2)
            await render_player(self.client, guild_id, force_new=True)

        store.render_task(message.guild.id, asyncio.create_task(_relocate()), mode="set")

    @classmethod
    def _visual_lines(cls, message: discord.Message) -> int:
        """Estimates how many on-screen chat lines a message occupies."""
        lines = 1
        if message.content:
            lines = sum(len(line) // cls.chars_per_line + 1 for line in message.content.splitlines()) or 1
        blocks = len(message.attachments) + len(message.embeds) + len(message.stickers)
        return lines + blocks * cls.block_lines

    # Play
    @slash_command(name="play")
    @option("query", description="Enter your track name/link or playlist link", autocomplete=search)
    async def play(self, ctx: discord.ApplicationContext, query: str):
        """Searches and plays a track from a given query."""
        player = await self.ensure_voice(ctx)
        if not player:
            return
        await ctx.defer()
        just_connected = not player.current and not len(player.queue.tracks)
        try:
            query = query.strip("<>")
            query = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b|\s*-\s*\d{1,2}:\d{2}(?::\d{2})?\b", "", query)
            result = await self.client.sonolink.search_track(query, source=sonolink.TrackSourceType.YOUTUBE_MUSIC)
            if result.is_error():
                await ctx.respond(
                    view=container(
                        f"{emoji.error} Failed to load the track. Please try again in a moment.",
                        config.color.red,
                    )
                )
                if just_connected:
                    await stop_player(player, ctx.guild)
                return
            if result.is_empty() or result.result is None:
                await ctx.respond(
                    view=container(f"{emoji.error} No track found from the given query.", config.color.red)
                )
                if just_connected:
                    await stop_player(player, ctx.guild)
                return
            data = result.result
            if isinstance(data, Playlist):
                tracks = [tag_requester(self.client, track, ctx.author.id) for track in data.tracks]
                src_info = get_source(tracks[0].source_name)
                player.queue.put(tracks)
                content = f"{src_info['emoji']} Added **{data.name}** with `{len(tracks)}` tracks."
            else:
                track = tag_requester(self.client, data[0] if isinstance(data, list) else data, ctx.author.id)
                player.queue.put(track)
                src_info = get_source(track.source_name)
                if track.is_stream:
                    dur = f"{emoji.live} LIVE"
                else:
                    dur = format_timedelta(datetime.timedelta(milliseconds=track.length), locale="en")
                content = f"{src_info['emoji']} Added [**{track.title}** by **{track.author}**]({track.uri}) [{dur}]."
            await ctx.respond(view=container(content, int(src_info["color"])))
            if not player.current:
                await player.play(player.queue.get())
        except Exception:
            if just_connected:
                await stop_player(player, ctx.guild)
            raise

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
                bar_length = 10
                filled_length = int(bar_length * player.position // float(player.current.length))
                bar = f"`{fmt_time(player.position)}` {emoji.filled_bar * filled_length}{emoji.empty_bar * (bar_length - filled_length)} `{fmt_time(player.current.length)}`"
                duration = datetime.timedelta(milliseconds=player.current.length)
                duration = format_timedelta(duration, locale="en")
            loop = ""
            if player.queue_mode is sonolink.QueueMode.NORMAL:
                loop = "Disabled"
            elif player.queue_mode is sonolink.QueueMode.LOOP:
                loop = "Track"
            elif player.queue_mode is sonolink.QueueMode.LOOP_ALL:
                loop = "Queue"
            autoplay_on = player.autoplay is sonolink.AutoPlayMode.ENABLED
            view = DesignerView(
                ui.Container(
                    ui.Section(
                        ui.TextDisplay(f"## [{player.current.title}]({player.current.uri})"),
                        ui.TextDisplay(
                            f"{emoji.user} **Requested By**: {requester.mention if requester else 'Unknown'}\n"
                            f"{emoji.mic} **Artist**: {get_source(player.current.source_name)['emoji']} {player.current.author}\n"
                            f"{emoji.duration} **Duration**: {duration}\n"
                            f"{emoji.voice} **Volume**: `{player.volume}%`\n"
                            f"{emoji.loop} **Loop**: {loop}\n"
                            f"{emoji.shuffle} **Shuffle**: {'Enabled' if player.queue.shuffle_mode is sonolink.ShuffleMode.PERSISTENT else 'Disabled'}\n"
                            f"{emoji.autoplay} **Autoplay**: {'Enabled' if autoplay_on else 'Disabled'}\n"
                            f"{emoji.equalizer} **Equalizers**: {', '.join([name.title() for name in player.presets]) if player.presets else 'None'}"
                            f"{f'\n\n {bar}' if bar else ''}"
                        ),
                        accessory=ui.Thumbnail(url=player.current.artwork) if player.current.artwork else None,
                    )
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Equalizer slash cmd group
    eq = SlashCommandGroup(name="eq", description="Equalizer commands.")

    async def _apply_preset(self, ctx: discord.ApplicationContext, kind: str, variant: str, label: str):
        """Stores the preset for its kind and re-applies the combined filter state."""
        player = await self.ensure_voice(ctx)
        if player:
            player.presets[kind] = EqPresets.build(kind, variant)
            await player.apply_presets()
            await slash_log(ctx, f"{emoji.equalizer} Applied **{label}** ({variant}) equalizer.")

    @eq.command(name="reset")
    async def reset(self, ctx: discord.ApplicationContext):
        """Resets the equalizer to default."""
        player = await self.ensure_voice(ctx)
        if player:
            player.presets.clear()
            await player.apply_presets()
            await slash_log(ctx, f"{emoji.equalizer} Reset equalizer to default settings.")

    async def filter_autocomplete(self, ctx: discord.AutocompleteContext):
        """Provides filter names for autocomplete."""
        player = get_player(self.client, ctx.interaction.guild_id)
        if not player:
            return []
        return [name.title() for name in player.presets if ctx.value.lower() in name.lower()]

    @eq.command(name="remove")
    @option("name", description="Name of the equalizer to remove.", autocomplete=filter_autocomplete)
    async def remove_eq(self, ctx: discord.ApplicationContext, name: str):
        """Removes an equalizer by name."""
        player = await self.ensure_voice(ctx)
        if player:
            key = name.lower()
            if key in player.presets:
                player.presets.pop(key)
                await player.apply_presets()
                await slash_log(ctx, f"{emoji.equalizer} Removed **{name.title()}** equalizer.")
            else:
                await reply(ctx, f"{emoji.error} **{name}** equalizer not found.", color=config.color.red)

    @eq.command(name="karaoke")
    @option(
        "intensity",
        description="Karaoke intensity: Light, Medium, or Strong",
        choices=["Light", "Medium", "Strong"],
        required=False,
    )
    async def karaoke(self, ctx: discord.ApplicationContext, intensity: str = "Medium"):
        """Remove center vocals for karaoke effect."""
        await self._apply_preset(ctx, "karaoke", intensity, "Karaoke")

    @eq.command(name="timescale")
    @option(
        "speed",
        description="Playback speed multiplier",
        choices=["0.5x", "1x", "1.5x", "2x", "3x", "4x", "5x", "6x", "10x", "Nightcore", "Daycore"],
        required=False,
    )
    async def timescale(self, ctx: discord.ApplicationContext, speed: str = "1x"):
        """Change playback speed and pitch."""
        await self._apply_preset(ctx, "timescale", speed, "Timescale")

    @eq.command(name="tremolo")
    @option("intensity", description="Tremolo intensity", choices=["Subtle", "Medium", "Strong"], required=False)
    async def tremolo(self, ctx: discord.ApplicationContext, intensity: str = "Medium"):
        """Apply volume trembling effect."""
        await self._apply_preset(ctx, "tremolo", intensity, "Tremolo")

    @eq.command(name="vibrato")
    @option("intensity", description="Vibrato intensity", choices=["Light", "Medium", "Heavy"], required=False)
    async def vibrato(self, ctx: discord.ApplicationContext, intensity: str = "Medium"):
        """Apply pitch wobbling effect."""
        await self._apply_preset(ctx, "vibrato", intensity, "Vibrato")

    @eq.command(name="rotation")
    @option("speed", description="8D rotation speed", choices=["Slow", "Medium", "Fast"], required=False)
    async def rotation(self, ctx: discord.ApplicationContext, speed: str = "Medium"):
        """Apply 8D audio rotation effect."""
        await self._apply_preset(ctx, "rotation", speed, "Rotation")

    @eq.command(name="lowpass")
    @option("strength", description="Low-pass filter strength", choices=["Light", "Medium", "Heavy"], required=False)
    async def lowpass(self, ctx: discord.ApplicationContext, strength: str = "Medium"):
        """Apply muffled/underwater sound effect."""
        await self._apply_preset(ctx, "lowpass", strength, "Lowpass")

    @eq.command(name="channelmix")
    @option(
        "mode",
        description="Channel mixing mode",
        choices=["Mono", "Left Only", "Right Only", "Swap", "Wide Stereo"],
        required=False,
    )
    async def channelmix(self, ctx: discord.ApplicationContext, mode: str = "Mono"):
        """Mix audio channels for different stereo effects."""
        await self._apply_preset(ctx, "channelmix", mode, "Channel Mix")

    @eq.command(name="distortion")
    @option(
        "type",
        description="Distortion type",
        choices=["Light Crunch", "Heavy Metal", "Vintage", "Digital Clip"],
        required=False,
    )
    async def distortion(self, ctx: discord.ApplicationContext, type: str = "Light Crunch"):
        """Apply audio distortion effects."""
        await self._apply_preset(ctx, "distortion", type, "Distortion")

    # Stop
    @slash_command(name="stop")
    async def stop(self, ctx: discord.ApplicationContext):
        """Destroys the player."""
        await ctx.defer(ephemeral=True)
        player = await self.ensure_voice(ctx)
        if player:
            await slash_log(ctx, f"{emoji.stop} Destroyed player.", render=False)
            await stop_player(player, ctx.guild)

    # Seek
    @slash_command(name="seek")
    @option("duration", description="Enter the amount of duration to seek. Ex: 10s, 1m, 2h etc....")
    async def seek(self, ctx: discord.ApplicationContext, duration: str):
        """Seeks to a given position in a track."""
        player = await self.ensure_voice(ctx)
        if player:
            timedelta = parse_duration(duration)
            track_time = int(player.position + timedelta.total_seconds() * 1000)
            if track_time < player.current.length:
                await player.seek(track_time)
                start_lyrics(self.client, ctx.guild.id)
                await slash_log(ctx, f"{emoji.seek} Moved track to `{fmt_time(track_time)}`.")
            else:
                await self.skip(ctx=ctx)

    # Skip
    @slash_command(name="skip")
    async def skip(self, ctx: discord.ApplicationContext):
        """Skips the current playing track."""
        player = await self.ensure_voice(ctx)
        if player:
            await slash_log(ctx, f"{emoji.skip} Skipped the track.", render=False)
            await skip_or_stop(player, ctx.guild)

    # Skip to
    @slash_command(name="skip-to")
    @option("track", description="Enter your track index number to skip", autocomplete=track_autocomplete)
    async def skip_to(self, ctx: discord.ApplicationContext, track: str):
        """Skips to a given track in the queue."""
        player = await self.ensure_voice(ctx)
        if player:
            await ctx.defer(ephemeral=True)
            index: int = int(track.split(".")[0])
            if index < 1 or index > len(player.queue.tracks):
                await reply(
                    ctx,
                    f"{emoji.error} Track number must be between `1` and `{len(player.queue.tracks)}`",
                    color=config.color.red,
                )
            else:
                await player.skip_to(index - 1)
                await slash_log(ctx, f"{emoji.skip} Skipped to track `{index}`.", render=False)

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
                await reply(ctx, f"{emoji.error} Player is not paused", color=config.color.red)

    # Volume
    @slash_command(name="volume")
    @option("volume", description="Enter your volume amount from 1 - 100")
    async def volume(self, ctx: discord.ApplicationContext, volume: int):
        """Changes the player's volume 1 - 100."""
        player = await self.ensure_voice(ctx)
        if player:
            if volume < 1 or volume > 100:
                await reply(ctx, f"{emoji.error} Volume amount must be between `1` - `100`", color=config.color.red)
            else:
                await player.set_volume(volume)
                await slash_log(ctx, f"{emoji.voice} Volume changed to `{player.volume}%`.")

    # Queue
    @slash_command(name="queue")
    @option("page", description="Enter queue page number", default=1, required=False)
    async def queue(self, ctx: discord.ApplicationContext, page: int = 1):
        """Shows the player's queue."""
        player = await self.ensure_voice(ctx)
        if player:
            items_per_page = 5
            pages = max(1, math.ceil(len(player.queue.tracks) / items_per_page))
            if page > pages or page < 1:
                await reply(ctx, f"{emoji.error} Page has to be between `1` to `{pages}`", color=config.color.red)
                return
            queue_view = QueueListView(client=self.client, ctx=ctx, page=page if pages > 1 else 1)
            await ctx.respond(view=queue_view, ephemeral=True)

    # Clear queue
    @slash_command(name="clear-queue")
    async def clear_queue(self, ctx: discord.ApplicationContext):
        """Clears the player's queue."""
        player = await self.ensure_voice(ctx)
        if player:
            if not len(player.queue.tracks):
                await reply(ctx, f"{emoji.error} Queue is empty", color=config.color.red)
            else:
                player.queue.clear()
                await slash_log(ctx, f"{emoji.success} Cleared the queue.", color=config.color.green)

    # Shuffle
    @slash_command(name="shuffle")
    async def shuffle(self, ctx: discord.ApplicationContext):
        """Toggle shuffle for the player's queue."""
        player = await self.ensure_voice(ctx)
        if player:
            if not len(player.queue.tracks):
                await reply(ctx, f"{emoji.error} Queue is empty", color=config.color.red)
            else:
                await ctx.defer(ephemeral=True)
                shuffled = player.queue.shuffle_mode is sonolink.ShuffleMode.PERSISTENT
                player.queue.shuffle_mode = (
                    sonolink.ShuffleMode.DEFAULT if shuffled else sonolink.ShuffleMode.PERSISTENT
                )
                await slash_log(ctx, f"{emoji.shuffle} {'Disabled' if shuffled else 'Enabled'} shuffle.")

    # Autoplay
    @slash_command(name="autoplay")
    async def autoplay(self, ctx: discord.ApplicationContext):
        """Toggles autoplay."""
        player = await self.ensure_voice(ctx)
        if player:
            enabled = player.autoplay is sonolink.AutoPlayMode.ENABLED
            player.autoplay = sonolink.AutoPlayMode.DISABLED if enabled else sonolink.AutoPlayMode.ENABLED
            await slash_log(
                ctx,
                f"{emoji.autoplay} {'Enabled' if not enabled else 'Disabled'} autoplay.",
            )

    # Loop
    @slash_command(name="loop")
    @option("mode", description="Enter loop mode", choices=["Disable", "Queue", "Track"])
    async def loop(self, ctx: discord.ApplicationContext, mode: str):
        """Loops the current queue until the command is invoked again or until a new track is enqueued."""
        player = await self.ensure_voice(ctx)
        if player:
            await ctx.defer(ephemeral=True)
            msg = ""
            if mode == "Disable":
                player.queue_mode = sonolink.QueueMode.NORMAL
                msg = f"{emoji.loop_white} Disabled loop."
            elif mode == "Track":
                player.queue_mode = sonolink.QueueMode.LOOP
                msg = f"{emoji.loop_one} Enabled track loop."
            elif mode == "Queue":
                if not len(player.queue.tracks):
                    await reply(ctx, f"{emoji.error} Queue is empty.", color=config.color.red)
                    return
                else:
                    player.queue_mode = sonolink.QueueMode.LOOP_ALL
                    msg = f"{emoji.loop} Enabled queue loop."
            await slash_log(ctx, msg)

    # Remove
    @slash_command(name="remove")
    @option("track", description="Select the track to remove", autocomplete=track_autocomplete)
    async def remove(self, ctx: discord.ApplicationContext, track: str):
        """Removes a track from the player's queue with the given index."""
        player = await self.ensure_voice(ctx)
        if player:
            index: int = int(track.split(".")[0])
            if not len(player.queue.tracks):
                await reply(ctx, f"{emoji.error} Queue is empty", color=config.color.red)
            elif index > len(player.queue.tracks) or index < 1:
                await reply(
                    ctx,
                    f"{emoji.error} Index has to be between `1` to `{len(player.queue.tracks)}`",
                    color=config.color.red,
                )
            else:
                removed = player.queue.remove_at(index - 1)
                await slash_log(ctx, f"{emoji.remove} Removed **{removed.title}**.", color=config.color.red)


def setup(client: Client):
    client.add_cog(Music(client))
