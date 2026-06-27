import asyncio
import datetime
import discord
import lavalink
import logging
import math
import re
from babel.dates import format_timedelta
from core import Client
from core.view import DesignerView
from discord import SlashCommandGroup, ui
from discord.commands import option, slash_command
from discord.ext import commands
from music import recommend, store
from music.client import LavalinkVoiceClient
from music.player import _get_render_lock, cleanup_guild, render_player, slash_log, stop_player
from music.queue import QueueListView
from music.utils import container, music_log, reply, sources
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from utils import config, logger
from utils.emoji import emoji
from utils.helpers import parse_duration

logging.getLogger("lavalink").setLevel(logging.ERROR)

console = Console()
_lavalink_live: Live | None = None

# Regex
url_rx = re.compile("https?:\\/\\/(?:www\\.)?.+")


class Music(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # Connect to lavalink
    def connect_lavalink(self):
        self.client.lavalink.add_node(
            host=config.lavalink["host"],
            port=config.lavalink["port"],
            password=config.lavalink["password"],
            region="auto",
            ssl=config.lavalink["secure"],
        )

    @commands.Cog.listener()
    async def on_ready(self):
        global _lavalink_live
        if self.client.lavalink is None:
            self.client.lavalink = lavalink.Client(self.client.user.id)
            self.connect_lavalink()
            if _lavalink_live is None or not _lavalink_live.is_started:
                _lavalink_live = Live(
                    Spinner("dots", text="[yellow]Connecting to Lavalink...[/]", style="yellow"),
                    console=console,
                    refresh_per_second=10,
                    transient=False,
                )
                _lavalink_live.start()
        if self.client.lavalink._event_hooks:
            self.client.lavalink._event_hooks.clear()
        self.client.lavalink.add_event_hooks(self)

    @lavalink.listener(lavalink.NodeReadyEvent)
    async def node_ready_hook(self, event: lavalink.NodeReadyEvent):
        global _lavalink_live
        latency = round(await event.node.get_rest_latency())
        text = Text()
        text.append("✓ Connected to Lavalink ", style="green")
        text.append(event.node.name, style="cyan")
        text.append("\n  ├ Latency", style="green")
        text.append(": ")
        text.append(f"{latency}ms", style="cyan")
        text.append("\n  ╰ Resumed", style="green")
        text.append(": ")
        text.append(str(event.resumed), style="cyan")
        if _lavalink_live and _lavalink_live.is_started:
            _lavalink_live.update(text)
            _lavalink_live.stop()
            _lavalink_live = None
        else:
            console.print(text)

    @lavalink.listener(lavalink.NodeDisconnectedEvent)
    async def node_disconnected_hook(self, event: lavalink.NodeDisconnectedEvent):
        global _lavalink_live
        items = [("Reason", event.reason or "Connection lost")]
        if event.code:
            items.append(("Code", str(event.code)))
        text = Text()
        text.append("✗ Disconnected from Lavalink ", style="red")
        text.append(event.node.name, style="cyan")
        for i, (key, value) in enumerate(items):
            prefix = "╰" if i == len(items) - 1 else "├"
            text.append(f"\n  {prefix} {key}", style="red")
            text.append(": ")
            text.append(value, style="cyan")
        if _lavalink_live and _lavalink_live.is_started:
            _lavalink_live.update(text)
            _lavalink_live.stop()
            _lavalink_live = None
        else:
            console.print(text)
        _lavalink_live = Live(
            Spinner("dots", text="[yellow]Reconnecting to Lavalink...[/]", style="yellow"),
            console=console,
            refresh_per_second=10,
            transient=False,
        )
        _lavalink_live.start()

    # Current voice
    def current_voice_channel(self, ctx: discord.ApplicationContext):
        if ctx.guild and ctx.guild.me.voice:
            return ctx.guild.me.voice.channel
        return None

    # Unloading cog
    def cog_unload(self):
        global _lavalink_live
        if _lavalink_live and _lavalink_live.is_started:
            _lavalink_live.stop()
            _lavalink_live = None
        self.client.lavalink._event_hooks.clear()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        cleanup_guild(guild.id)
        for task_fn in (store.inactivity_task, store.render_task):
            task = task_fn(guild.id, mode="get")
            if task is not None:
                task.cancel()
        store.store.pop(guild.id, None)

    @lavalink.listener(lavalink.TrackStartEvent)
    async def track_start_hook(self, event: lavalink.TrackStartEvent):
        guild_id = int(event.player.guild_id)
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(guild_id)
        store.last_track(guild_id, player.current, "set")
        store.autoplay_history(guild_id, player.current.identifier, "add")
        vc: discord.VoiceChannel | None = (
            self.client.get_channel(int(event.player.channel_id)) if event.player.channel_id else None
        )
        tasks = [render_player(self.client, guild_id)]
        if vc is not None:
            tasks.append(vc.set_status(status=f"Playing **{player.current.title}**"))
        await asyncio.gather(*tasks, return_exceptions=True)

    @lavalink.listener(lavalink.TrackStuckEvent, lavalink.TrackExceptionEvent)
    async def track_stuck_or_exception_hook(self, event: lavalink.TrackExceptionEvent):
        await music_log(
            self.client,
            int(event.player.guild_id),
            f"{emoji.error} Track is stuck or an error occurred while playing the track.",
            color=config.color.red,
        )

    @lavalink.listener(lavalink.QueueEndEvent)
    async def queue_end_hook(self, event: lavalink.QueueEndEvent):
        guild_id = int(event.player.guild_id)
        if not store.autoplay(guild_id):
            return
        lock = recommend.get_lock(guild_id)
        if lock.locked():
            return
        async with lock:
            player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(guild_id)
            guild: discord.Guild = self.client.get_guild(guild_id)
            pool = await recommend.fetch_recommendations(player, guild_id)
            if pool:
                track = pool[0]
                player.add(requester=self.client.user.id, track=track)
                try:
                    await player.play()
                except Exception:
                    await stop_player(player, guild)
                    return
                await music_log(
                    self.client,
                    guild_id,
                    f"{emoji.autoplay} Autoplay queued [**{track.title}** by **{track.author}**]({track.uri}).",
                )
                return
            await stop_player(player, guild)

    # Ensures voice parameters
    async def ensure_voice(self, ctx: discord.ApplicationContext):
        """Checks all the voice parameters."""

        def _err(text: str) -> DesignerView:
            return DesignerView(ui.Container(ui.TextDisplay(text), color=config.color.red))

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond(view=_err(f"{emoji.error} Join a voice channel first."), ephemeral=True)
            return None

        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.guild.id)
        bot_channel = self.current_voice_channel(ctx)

        if ctx.command.name == "play":
            needs_connect = bot_channel is None or not player.is_connected
            if needs_connect:
                if bot_channel is not None and ctx.author.voice.channel != bot_channel:
                    await ctx.respond(view=_err(f"{emoji.error} You are not in my voice channel."), ephemeral=True)
                    return None
                permissions = ctx.author.voice.channel.permissions_for(ctx.me)
                if not permissions.connect or not permissions.speak:
                    await ctx.respond(
                        view=_err(f"{emoji.error} I need the `Connect` and `Speak` permissions."), ephemeral=True
                    )
                    return None
                if not self.client.lavalink.node_manager.nodes:
                    self.connect_lavalink()
                if ctx.guild.voice_client:
                    await ctx.guild.voice_client.disconnect(force=True)
                await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
                player = self.client.lavalink.player_manager.create(ctx.guild.id)
                store.play_ch(ctx.guild.id, ctx.channel, "set")
            elif ctx.author.voice.channel != bot_channel:
                await ctx.respond(view=_err(f"{emoji.error} You are not in my voice channel."), ephemeral=True)
                return None
        else:
            if bot_channel is None or (not player.current and ctx.command.name != "stop"):
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
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.interaction.guild_id)
        tracks = []
        if re.match(url_rx, ctx.value):
            return tracks
        try:
            if ctx.value != "":
                result = await player.node.get_tracks(f"ytmsearch:{ctx.value}")
            else:
                result = await player.node.get_tracks("ytmsearch:top tracks")
        except lavalink.errors.ClientError:
            return tracks
        for track in result.tracks:
            dur = lavalink.format_time(track.duration)
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
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(ctx.interaction.guild_id)
        if not player or not player.queue:
            return []
        result = []
        for i, track in enumerate(player.queue):
            title = track.title
            full_entry = f"{i + 1}. {title}"
            entry = full_entry[:100]
            if ctx.value.lower() in entry.lower():
                result.append(entry)
        return result

    # Voice state update event
    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        """Handles voice state updates to manage the bot's connection."""
        if member.id == member.guild.me.id and after.channel is None:
            if member.guild.voice_client:
                await member.guild.voice_client.disconnect(force=True)
            return

        if member.bot:
            return

        if hasattr(self.client, "lavalink"):
            player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(member.guild.id)
            if not player or not player.is_connected:
                return

            bot_voice_channel = member.guild.me.voice.channel if member.guild.me.voice else None
            if not bot_voice_channel:
                return

            member_left_bot_channel = before.channel == bot_voice_channel and after.channel != bot_voice_channel
            member_joined_bot_channel = before.channel != bot_voice_channel and after.channel == bot_voice_channel

            if not (member_left_bot_channel or member_joined_bot_channel):
                return

            humans = [m for m in bot_voice_channel.members if not m.bot]

            if not humans:
                pending_inactivity_task = store.inactivity_task(member.guild.id, mode="get")
                if pending_inactivity_task:
                    pending_inactivity_task.cancel()
                    store.inactivity_task(member.guild.id, mode="clear")

                # Each inactivity task is uniquely associated with its guild ID in the store, ensuring isolation between guilds.
                async def inactivity_task():
                    async def stop_and_disconnect():
                        await music_log(
                            self.client,
                            member.guild.id,
                            f"{emoji.leave} Left {bot_voice_channel.mention} due to inactivity.",
                            color=config.color.red,
                        )
                        await stop_player(player, bot_voice_channel.guild)

                    is_paused_before = player.paused
                    await player.set_pause(True)
                    sleep_done: bool = False
                    try:
                        await asyncio.sleep(60)
                        sleep_done = True
                        current_humans = [m for m in bot_voice_channel.members if not m.bot]
                        if not current_humans:
                            await stop_and_disconnect()
                    except asyncio.CancelledError:
                        if player.paused and not is_paused_before:
                            await player.set_pause(False)
                        if sleep_done:
                            await stop_and_disconnect()

                store.inactivity_task(guild_id=member.guild.id, task=asyncio.create_task(inactivity_task()), mode="set")
            else:
                inactivity_task = store.inactivity_task(member.guild.id, mode="get")
                if inactivity_task:
                    inactivity_task.cancel()
                    store.inactivity_task(member.guild.id, mode="clear")

    # Track chat after the player so it can be relocated to the bottom
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Relocates the player to the bottom when unrelated chat arrives in its channel."""
        if not message.guild:
            return
        if message.author.name == f"{self.client.user.name} - {logger.LogType.MUSIC}":
            return
        play_msg, _ = store.play_msg(message.guild.id)
        if not play_msg or message.channel.id != play_msg.channel.id:
            return
        if message.author.bot:
            # Case 1: player card fires during channel.send - lock is still held mid-gather.
            # Case 2: player card fires after gather returns - store is already updated so IDs match.
            if _get_render_lock(message.guild.id).locked() or message.id == play_msg.id:
                return
        pending = store.render_task(message.guild.id)
        if pending and not pending.done():
            pending.cancel()

        async def _relocate(guild_id: int = message.guild.id):
            await asyncio.sleep(2)
            await render_player(self.client, guild_id, force_new=True)

        store.render_task(message.guild.id, asyncio.create_task(_relocate()), mode="set")

    # Play
    @slash_command(name="play")
    @option("query", description="Enter your track name/link or playlist link", autocomplete=search)
    async def play(self, ctx: discord.ApplicationContext, query: str):
        """Searches and plays a track from a given query."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if not player:
            return
        await ctx.defer()
        just_connected = not player.current and not player.queue
        try:
            query = query.strip("<>")
            query = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b|\s*-\s*\d{1,2}:\d{2}(?::\d{2})?\b", "", query)
            if not url_rx.match(query):
                query = f"ytmsearch:{query}"
            results = await player.node.get_tracks(query)
            if not results or not results.tracks:
                await ctx.respond(
                    view=container(f"{emoji.error} No track found from the given query.", config.color.red)
                )
                if just_connected:
                    await stop_player(player, ctx.guild)
                return
            if results.load_type == lavalink.LoadType.PLAYLIST:
                tracks = results.tracks
                src_info = sources.get(results.tracks[0].source_name, sources["_"])
                for track in tracks:
                    player.add(requester=ctx.author.id, track=track)
                content = f"{src_info['emoji']} Added **{results.playlist_info.name}** with `{len(tracks)}` tracks."
            else:
                track = results.tracks[0]
                player.add(requester=ctx.author.id, track=track)
                src_info = sources.get(track.source_name, sources["_"])
                if track.stream:
                    dur = f"{emoji.live} LIVE"
                else:
                    dur = format_timedelta(datetime.timedelta(milliseconds=track.duration), locale="en")
                content = f"{src_info['emoji']} Added [**{track.title}** by **{track.author}**]({track.uri}) [`{dur}`]."
            await ctx.respond(view=container(content, int(src_info["color"])))
            if not player.is_playing:
                await player.play()
        except Exception:
            if just_connected:
                await stop_player(player, ctx.guild)
            raise

    # Now playing
    @slash_command(name="now-playing")
    async def now_playing(self, ctx: discord.ApplicationContext):
        """Shows currently playing track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        duration: str = ""
        bar: str = ""
        if player:
            requester = ctx.guild.get_member(player.current.requester)
            if player.current.stream:
                duration = f"{emoji.live} LIVE"
            elif not player.current.stream:
                bar_length = 10
                filled_length = int(bar_length * player.position // float(player.current.duration))
                bar = f"`{lavalink.format_time(player.position)}` {emoji.filled_bar * filled_length}{emoji.empty_bar * (bar_length - filled_length)} `{lavalink.format_time(player.current.duration)}`"
                duration = datetime.timedelta(milliseconds=player.current.duration)
                duration = format_timedelta(duration, locale="en_IN")
            loop = ""
            if player.loop == player.LOOP_NONE:
                loop = "Disabled"
            elif player.loop == player.LOOP_SINGLE:
                loop = "Track"
            elif player.loop == player.LOOP_QUEUE:
                loop = "Queue"
            view = DesignerView(
                ui.Container(
                    ui.Section(
                        ui.TextDisplay(f"## [{player.current.title}]({player.current.uri})"),
                        ui.TextDisplay(
                            f"{emoji.user} **Requested By**: {requester.mention if requester else 'Unknown'}\n"
                            f"{emoji.mic} **Artist**: {sources.get(player.current.source_name, sources['_'])['emoji']} {player.current.author}\n"
                            f"{emoji.duration} **Duration**: {duration}\n"
                            f"{emoji.volume} **Volume**: `{player.volume}%`\n"
                            f"{emoji.loop} **Loop**: {loop}\n"
                            f"{emoji.shuffle} **Shuffle**: {'Enabled' if player.shuffle else 'Disabled'}\n"
                            f"{emoji.autoplay} **Autoplay**: {'Enabled' if store.autoplay(ctx.guild.id) else 'Disabled'}\n"
                            f"{emoji.equalizer} **Equalizers**: {', '.join([name.title() for name in player.filters]) if player.filters else 'None'}"
                            f"{f'\n\n {bar}' if bar else ''}"
                        ),
                        accessory=ui.Thumbnail(url=player.current.artwork_url) if player.current.artwork_url else None,
                    )
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Equalizer slash cmd group
    eq = SlashCommandGroup(name="eq", description="Equalizer commands.")

    @eq.command(name="reset")
    async def reset(self, ctx: discord.ApplicationContext):
        """Resets the equalizer to default."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await player.clear_filters()
            await slash_log(ctx, f"{emoji.equalizer} Reset equalizer to default settings.")

    async def filter_autocomplete(self, ctx: discord.AutocompleteContext):
        """Provides filter names for autocomplete."""
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.interaction.guild_id)
        return [name.title() for name in player.filters if ctx.value.lower() in name.lower()]

    @eq.command(name="remove")
    @option("name", description="Name of the equalizer to remove.", autocomplete=filter_autocomplete)
    async def remove_eq(self, ctx: discord.ApplicationContext, name: str):
        """Removes an equalizer by name."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.get_filter(name):
                await player.remove_filter(name)
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
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Light": {"level": 1.5, "mono_level": 0.8, "filter_band": 220.0, "filter_width": 100.0},
                "Medium": {"level": 2.0, "mono_level": 1.0, "filter_band": 220.0, "filter_width": 100.0},
                "Strong": {"level": 3.0, "mono_level": 1.2, "filter_band": 220.0, "filter_width": 100.0},
            }
            cfg = presets[intensity]
            eq = lavalink.Karaoke()
            eq.update(
                level=cfg["level"],
                mono_level=cfg["mono_level"],
                filter_band=cfg["filter_band"],
                filter_width=cfg["filter_width"],
            )
            await player.set_filter(eq)
            await slash_log(ctx, f"{emoji.equalizer} Applied **Karaoke** ({intensity}) equalizer.")

    @eq.command(name="timescale")
    @option(
        "speed",
        description="Playback speed multiplier",
        choices=["0.5x", "1x", "1.5x", "2x", "3x", "4x", "5x", "6x", "10x", "Nightcore", "Daycore"],
        required=False,
    )
    async def timescale(self, ctx: discord.ApplicationContext, speed: str = "1x"):
        """Change playback speed and pitch."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Nightcore": {"speed": 1.3, "pitch": 1.3, "rate": 1.0},
                "Daycore": {"speed": 0.7, "pitch": 0.7, "rate": 1.0},
            }
            if speed in presets:
                cfg = presets[speed]
                eq = lavalink.Timescale()
                eq.update(speed=cfg["speed"], pitch=cfg["pitch"], rate=cfg["rate"])
            else:
                speed_value = float(speed.replace("x", ""))
                eq = lavalink.Timescale()
                eq.update(speed=speed_value, pitch=speed_value, rate=1.0)
            await player.set_filter(eq)
            await slash_log(ctx, f"{emoji.equalizer} Applied **Timescale** ({speed}) equalizer.")

    @eq.command(name="tremolo")
    @option("intensity", description="Tremolo intensity", choices=["Subtle", "Medium", "Strong"], required=False)
    async def tremolo(self, ctx: discord.ApplicationContext, intensity: str = "Medium"):
        """Apply volume trembling effect."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Subtle": {"frequency": 1.5, "depth": 0.3},
                "Medium": {"frequency": 2.0, "depth": 0.5},
                "Strong": {"frequency": 3.0, "depth": 0.7},
            }
            cfg = presets[intensity]
            eq = lavalink.Tremolo()
            eq.update(frequency=cfg["frequency"], depth=cfg["depth"])
            await player.set_filter(eq)
            await slash_log(ctx, f"{emoji.equalizer} Applied **Tremolo** ({intensity}) equalizer.")

    @eq.command(name="vibrato")
    @option("intensity", description="Vibrato intensity", choices=["Light", "Medium", "Heavy"], required=False)
    async def vibrato(self, ctx: discord.ApplicationContext, intensity: str = "Medium"):
        """Apply pitch wobbling effect."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Light": {"frequency": 1.5, "depth": 0.3},
                "Medium": {"frequency": 2.0, "depth": 0.5},
                "Heavy": {"frequency": 3.5, "depth": 0.8},
            }
            cfg = presets[intensity]
            eq = lavalink.Vibrato()
            eq.update(frequency=cfg["frequency"], depth=cfg["depth"])
            await player.set_filter(eq)
            await slash_log(ctx, f"{emoji.equalizer} Applied **Vibrato** ({intensity}) equalizer.")

    @eq.command(name="rotation")
    @option("speed", description="8D rotation speed", choices=["Slow", "Medium", "Fast"], required=False)
    async def rotation(self, ctx: discord.ApplicationContext, speed: str = "Medium"):
        """Apply 8D audio rotation effect."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Slow": 0.1,
                "Medium": 0.2,
                "Fast": 0.3,
            }
            rotation_hz = presets[speed]
            eq = lavalink.Rotation()
            eq.update(rotation_hz=rotation_hz)
            await player.set_filter(eq)
            await slash_log(ctx, f"{emoji.equalizer} Applied **Rotation** ({speed}) equalizer.")

    @eq.command(name="lowpass")
    @option("strength", description="Low-pass filter strength", choices=["Light", "Medium", "Heavy"], required=False)
    async def lowpass(self, ctx: discord.ApplicationContext, strength: str = "Medium"):
        """Apply muffled/underwater sound effect."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Light": 5.0,
                "Medium": 20.0,
                "Heavy": 50.0,
            }
            smoothing = presets[strength]
            eq = lavalink.LowPass()
            eq.update(smoothing=smoothing)
            await player.set_filter(eq)
            await slash_log(ctx, f"{emoji.equalizer} Applied **Lowpass** ({strength}) equalizer.")

    @eq.command(name="channelmix")
    @option(
        "mode",
        description="Channel mixing mode",
        choices=["Mono", "Left Only", "Right Only", "Swap", "Wide Stereo"],
        required=False,
    )
    async def channelmix(self, ctx: discord.ApplicationContext, mode: str = "Mono"):
        """Mix audio channels for different stereo effects."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Mono": {"left_to_left": 0.5, "left_to_right": 0.5, "right_to_left": 0.5, "right_to_right": 0.5},
                "Left Only": {"left_to_left": 1.0, "left_to_right": 1.0, "right_to_left": 0.0, "right_to_right": 0.0},
                "Right Only": {"left_to_left": 0.0, "left_to_right": 0.0, "right_to_left": 1.0, "right_to_right": 1.0},
                "Swap": {"left_to_left": 0.0, "left_to_right": 1.0, "right_to_left": 1.0, "right_to_right": 0.0},
                "Wide Stereo": {"left_to_left": 1.0, "left_to_right": 0.3, "right_to_left": 0.3, "right_to_right": 1.0},
            }
            cfg = presets[mode]
            eq = lavalink.ChannelMix()
            eq.update(
                left_to_left=cfg["left_to_left"],
                left_to_right=cfg["left_to_right"],
                right_to_left=cfg["right_to_left"],
                right_to_right=cfg["right_to_right"],
            )
            await player.set_filter(eq)
            await slash_log(ctx, f"{emoji.equalizer} Applied **Channel Mix** ({mode}) equalizer.")

    @eq.command(name="distortion")
    @option(
        "type",
        description="Distortion type",
        choices=["Light Crunch", "Heavy Metal", "Vintage", "Digital Clip"],
        required=False,
    )
    async def distortion(self, ctx: discord.ApplicationContext, type: str = "Light Crunch"):
        """Apply audio distortion effects."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Light Crunch": {
                    "sin_offset": 0.0,
                    "sin_scale": 1.2,
                    "cos_offset": 0.0,
                    "cos_scale": 1.1,
                    "tan_offset": 0.0,
                    "tan_scale": 1.0,
                    "offset": 0.05,
                    "scale": 1.0,
                },
                "Heavy Metal": {
                    "sin_offset": 0.1,
                    "sin_scale": 1.5,
                    "cos_offset": 0.1,
                    "cos_scale": 1.4,
                    "tan_offset": 0.05,
                    "tan_scale": 1.2,
                    "offset": 0.1,
                    "scale": 1.1,
                },
                "Vintage": {
                    "sin_offset": 0.0,
                    "sin_scale": 1.1,
                    "cos_offset": 0.0,
                    "cos_scale": 1.05,
                    "tan_offset": 0.0,
                    "tan_scale": 1.0,
                    "offset": 0.02,
                    "scale": 0.95,
                },
                "Digital Clip": {
                    "sin_offset": 0.2,
                    "sin_scale": 2.0,
                    "cos_offset": 0.2,
                    "cos_scale": 1.8,
                    "tan_offset": 0.1,
                    "tan_scale": 1.5,
                    "offset": 0.15,
                    "scale": 1.2,
                },
            }
            cfg = presets[type]
            eq = lavalink.Distortion()
            eq.update(
                sin_offset=cfg["sin_offset"],
                sin_scale=cfg["sin_scale"],
                cos_offset=cfg["cos_offset"],
                cos_scale=cfg["cos_scale"],
                tan_offset=cfg["tan_offset"],
                tan_scale=cfg["tan_scale"],
                offset=cfg["offset"],
                scale=cfg["scale"],
            )
            await player.set_filter(eq)
            await slash_log(ctx, f"{emoji.equalizer} Applied **Distortion** ({type}) equalizer.")

    # Stop
    @slash_command(name="stop")
    async def stop(self, ctx: discord.ApplicationContext):
        """Destroys the player."""
        await ctx.defer(ephemeral=True)
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await slash_log(ctx, f"{emoji.stop} Destroyed player.", render=False)
            await stop_player(player, ctx.guild)

    # Seek
    @slash_command(name="seek")
    @option("duration", description="Enter the amount of duration to seek. Ex: 10s, 1m, 2h etc....")
    async def seek(self, ctx: discord.ApplicationContext, duration: str):
        """Seeks to a given position in a track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            timedelta = parse_duration(duration)
            track_time = int(player.position + timedelta.total_seconds() * 1000)
            if track_time < player.current.duration:
                await player.seek(track_time)
                await slash_log(ctx, f"{emoji.seek} Moved track to `{lavalink.format_time(track_time)}`.")
            else:
                await self.skip(ctx=ctx)

    # Skip
    @slash_command(name="skip")
    async def skip(self, ctx: discord.ApplicationContext):
        """Skips the current playing track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await player.skip()
            await slash_log(ctx, f"{emoji.skip} Skipped the track.", render=False)

    # Skip to
    @slash_command(name="skip-to")
    @option("track", description="Enter your track index number to skip", autocomplete=track_autocomplete)
    async def skip_to(self, ctx: discord.ApplicationContext, track: str):
        """Skips to a given track in the queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await ctx.defer(ephemeral=True)
            index: int = int(track.split(".")[0])
            if index < 1 or index > len(player.queue):
                await reply(
                    ctx,
                    f"{emoji.error} Track number must be between `1` and `{len(player.queue)}`",
                    color=config.color.red,
                )
            else:
                player.queue = player.queue[index - 1 :]
                shuffle_state = player.shuffle
                player.set_shuffle(False)
                await player.skip()
                player.set_shuffle(shuffle_state)
                await slash_log(ctx, f"{emoji.skip} Skipped to track `{index}`.", render=False)

    # Pause
    @slash_command(name="pause")
    async def pause(self, ctx: discord.ApplicationContext):
        """Pauses the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                await reply(ctx, f"{emoji.error} Player is already paused.", color=config.color.red)
            else:
                await ctx.defer(ephemeral=True)
                await player.set_pause(True)
                await slash_log(ctx, f"{emoji.pause} Player paused.")

    # Resume
    @slash_command(name="resume")
    async def resume(self, ctx: discord.ApplicationContext):
        """Resumes the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                await ctx.defer(ephemeral=True)
                await player.set_pause(False)
                await slash_log(ctx, f"{emoji.play} Player resumed.")
            else:
                await reply(ctx, f"{emoji.error} Player is not paused", color=config.color.red)

    # Volume
    @slash_command(name="volume")
    @option("volume", description="Enter your volume amount from 1 - 100")
    async def volume(self, ctx: discord.ApplicationContext, volume: int):
        """Changes the player's volume 1 - 100."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if volume < 1 or volume > 100:
                await reply(ctx, f"{emoji.error} Volume amount must be between `1` - `100`", color=config.color.red)
            else:
                await player.set_volume(volume)
                await slash_log(ctx, f"{emoji.volume} Volume changed to `{player.volume}%`.")

    # Queue
    @slash_command(name="queue")
    @option("page", description="Enter queue page number", default=1, required=False)
    async def queue(self, ctx: discord.ApplicationContext, page: int = 1):
        """Shows the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            items_per_page = 5
            pages = max(1, math.ceil(len(player.queue) / items_per_page))
            if page > pages or page < 1:
                await reply(ctx, f"{emoji.error} Page has to be between `1` to `{pages}`", color=config.color.red)
                return
            queue_view = QueueListView(client=self.client, ctx=ctx, page=page if pages > 1 else 1)
            await ctx.respond(view=queue_view, ephemeral=True)

    # Clear queue
    @slash_command(name="clear-queue")
    async def clear_queue(self, ctx: discord.ApplicationContext):
        """Clears the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if not player.queue:
                await reply(ctx, f"{emoji.error} Queue is empty", color=config.color.red)
            else:
                player.queue.clear()
                await slash_log(ctx, f"{emoji.success} Cleared the queue.", color=config.color.green)

    # Shuffle
    @slash_command(name="shuffle")
    async def shuffle(self, ctx: discord.ApplicationContext):
        """Toggle shuffle for the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if not player.queue:
                await reply(ctx, f"{emoji.error} Queue is empty", color=config.color.red)
            else:
                await ctx.defer(ephemeral=True)
                player.set_shuffle(not player.shuffle)
                await slash_log(ctx, f"{emoji.shuffle} {'Enabled' if player.shuffle else 'Disabled'} shuffle.")

    # Autoplay
    @slash_command(name="autoplay")
    async def autoplay(self, ctx: discord.ApplicationContext):
        """Toggles autoplay"""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            enabled = store.autoplay(ctx.guild.id)
            store.autoplay(ctx.guild.id, not enabled, "set")
            await slash_log(
                ctx,
                f"{emoji.autoplay} {'Enabled' if not enabled else 'Disabled'} autoplay.",
            )

    # Loop
    @slash_command(name="loop")
    @option("mode", description="Enter loop mode", choices=["Disable", "Queue", "Track"])
    async def loop(self, ctx: discord.ApplicationContext, mode: str):
        """Loops the current queue until the command is invoked again or until a new track is enqueued."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await ctx.defer(ephemeral=True)
            _emoji = ""
            if mode == "Disable":
                player.set_loop(0)
                _emoji = emoji.loop_white
            elif mode == "Track":
                player.set_loop(1)
                _emoji = emoji.loop_one
            elif mode == "Queue":
                if not player.queue:
                    await reply(ctx, f"{emoji.error} Queue is empty.", color=config.color.red)
                    return
                else:
                    player.set_loop(2)
                    _emoji = emoji.loop
            await slash_log(
                ctx,
                f"{_emoji} {'Enabled' if mode != 'Disable' else 'Disabled'} {mode if mode != 'Disable' else ''} Loop.",
            )

    # Remove
    @slash_command(name="remove")
    @option("track", description="Select the track to remove", autocomplete=track_autocomplete)
    async def remove(self, ctx: discord.ApplicationContext, track: str):
        """Removes a track from the player's queue with the given index."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            index: int = int(track.split(".")[0])
            if not player.queue:
                await reply(ctx, f"{emoji.error} Queue is empty", color=config.color.red)
            elif index > len(player.queue) or index < 1:
                await reply(
                    ctx, f"{emoji.error} Index has to be between `1` to `{len(player.queue)}`", color=config.color.red
                )
            else:
                removed = player.queue.pop(index - 1)
                await slash_log(ctx, f"{emoji.leave} Removed **{removed.title}**.", color=config.color.red)


def setup(client: Client):
    client.add_cog(Music(client))
