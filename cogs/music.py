import asyncio
import datetime
import discord
import discord.ui
import lavalink
import math
import re
from babel.dates import format_timedelta
from discord.commands import option, slash_command
from discord.ext import commands, tasks
from music import equalizer_presets, store
from music.client import LavalinkVoiceClient
from utils import config
from utils.emoji import emoji

# Regex
url_rx = re.compile("https?:\\/\\/(?:www\\.)?.+")


class MusicView(discord.ui.View):
    def __init__(self, client: discord.Bot, timeout: int):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client

    async def interaction_check(self, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if not player.current:
            error_em = discord.Embed(
                description=f"{emoji.error} Nothing is being played at the current moment.", color=config.color.red
            )
            await interaction.response.send_message(embed=error_em, ephemeral=True)
            return False
        elif not interaction.user.voice:
            error_em = discord.Embed(description=f"{emoji.error} Join a voice channel first.", color=config.color.red)
            await interaction.response.send_message(embed=error_em, ephemeral=True)
            return False
        elif player.is_connected and interaction.user.voice.channel.id != int(player.channel_id):
            error_em = discord.Embed(
                description=f"{emoji.error} You are not in my voice channel.", color=config.color.red
            )
            await interaction.response.send_message(embed=error_em, ephemeral=True)
        else:
            return True

    # Pause / Resume
    @discord.ui.button(emoji=f"{emoji.pause_white}", custom_id="pause", style=discord.ButtonStyle.grey)
    async def pause_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if not player.paused:
            await player.set_pause(True)
        elif player.paused:
            await player.set_pause(False)
        button.emoji = emoji.play_white if player.paused else emoji.pause_white
        pause_em = discord.Embed(
            description=f"{interaction.user.mention} {'Paused' if player.paused else 'Resumed'} the player.",
            color=config.color.theme,
        )
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=pause_em, delete_after=5)

    # Stop
    @discord.ui.button(emoji=f"{emoji.stop_white}", custom_id="stop", style=discord.ButtonStyle.grey)
    async def stop_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild: discord.Guild = self.client.get_guild(int(interaction.guild_id))
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(int(interaction.guild_id))
        await player.stop()
        player.queue.clear()
        stop_embed = discord.Embed(
            description=f"{interaction.user.mention} Destroyed the player.",
            color=config.color.theme,
        )
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        await guild.me.voice.channel.set_status(status=None)
        await guild.voice_client.disconnect(force=True)
        await interaction.followup.send(embed=stop_embed, delete_after=5)
        await Disable(self.client, guild.id).queue_msg()

    # Skip
    @discord.ui.button(emoji=f"{emoji.skip_white}", custom_id="skip", style=discord.ButtonStyle.grey)
    async def skip_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        await player.skip()
        skip_em = discord.Embed(
            description=f"{interaction.user.mention} Skipped the track.",
            color=config.color.theme,
        )
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=skip_em, delete_after=5)

    # Loop
    @discord.ui.button(emoji=f"{emoji.loop_white}", custom_id="loop", style=discord.ButtonStyle.grey)
    async def loop_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if player.loop == player.LOOP_NONE:
            player.set_loop(1)
            button.emoji = emoji.loop_one
            mode = "Track"
        elif player.loop == player.LOOP_SINGLE and player.queue:
            player.set_loop(2)
            button.emoji = emoji.loop
            mode = "Queue"
        else:
            player.set_loop(0)
            button.emoji = emoji.loop_white
            mode = "OFF"
        loop_em = discord.Embed(
            description=f"{interaction.user.mention} {'Enabled' if mode != 'OFF' else 'Disabled'} {mode if mode != 'OFF' else ''} loop.",
            color=config.color.theme,
        )
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=loop_em, delete_after=5)

    # Shuffle
    @discord.ui.button(emoji=f"{emoji.shuffle_white}", custom_id="shuffle", style=discord.ButtonStyle.grey)
    async def shuffle_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if not player.queue:
            error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=config.color.red)
            await interaction.response.send_message(embed=error_em, ephemeral=True)
        else:
            player.shuffle = not player.shuffle
            button.emoji = f"{emoji.shuffle if player.shuffle else emoji.shuffle_white}"
            shuffle_em = discord.Embed(
                description=f"{interaction.user.mention} {'Enabled' if player.shuffle else 'Disabled'} shuffle.",
                color=config.color.theme,
            )
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=shuffle_em, delete_after=5)


class QueueView(discord.ui.View):
    def __init__(self, client: discord.Bot, page: int, timeout: int):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client
        self.page = page
        self.items_per_page = 5

    async def interaction_check(self, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if not player.queue:
            error_em = discord.Embed(description=f"{emoji.error} Queue is empty.", color=config.color.red)
            await interaction.response.send_message(embed=error_em, ephemeral=True)
        else:
            return True

    # Start
    @discord.ui.button(emoji=f"{emoji.start_white}", custom_id="start", style=discord.ButtonStyle.grey)
    async def start_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page = 1
        queue_embed = await QueueEmbed(self.client, interaction, self.page).get_embed()
        await interaction.response.edit_message(embed=queue_embed, view=self)

    # Previous
    @discord.ui.button(emoji=f"{emoji.previous_white}", custom_id="previous", style=discord.ButtonStyle.grey)
    async def previous_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        pages = math.ceil(len(player.queue) / self.items_per_page)
        if self.page <= 1:
            self.page = pages
        else:
            self.page -= 1
        queue_embed = await QueueEmbed(self.client, interaction, self.page).get_embed()
        await interaction.response.edit_message(embed=queue_embed, view=self)

    # Next
    @discord.ui.button(emoji=f"{emoji.next_white}", custom_id="next", style=discord.ButtonStyle.grey)
    async def next_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        pages = math.ceil(len(player.queue) / self.items_per_page)
        if self.page >= pages:
            self.page = 1
        else:
            self.page += 1
        queue_embed = await QueueEmbed(self.client, interaction, self.page).get_embed()
        await interaction.response.edit_message(embed=queue_embed, view=self)

    # End
    @discord.ui.button(emoji=f"{emoji.end_white}", custom_id="end", style=discord.ButtonStyle.grey)
    async def end_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        pages = math.ceil(len(player.queue) / self.items_per_page)
        self.page = pages
        queue_embed = await QueueEmbed(self.client, interaction, self.page).get_embed()
        await interaction.response.edit_message(embed=queue_embed, view=self)


class QueueEmbed:
    def __init__(self, client: discord.Bot, ctx: discord.ApplicationContext, page: int):
        self.client = client
        self.ctx = ctx
        self.page = page
        self.items_per_page = 5

    async def get_embed(self) -> discord.Embed:
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(self.ctx.guild_id)
        pages = math.ceil(len(player.queue) / self.items_per_page)
        start = (self.page - 1) * self.items_per_page
        end = start + self.items_per_page
        current_requester = self.ctx.guild.get_member(player.current.requester)
        queue_list = ""
        for index, track in enumerate(player.queue[start:end], start=start):
            requester = self.ctx.guild.get_member(track.requester)
            queue_list += (
                f"`{index + 1}.` **[{track.title}]({track.uri})** [{requester.mention if requester else 'Unknown'}]\n"
            )
        queue_em = discord.Embed(title=f"{self.ctx.guild.name}'s Queue", colour=config.color.theme)
        queue_em.add_field(
            name="Now Playing",
            value=f"`0.` **[{player.current.title}]({player.current.uri})** [{current_requester.mention if current_requester else 'Unknown'}]",
            inline=False,
        )
        queue_em.add_field(name=f"Queued {len(player.queue)} Tracks", value=f"{queue_list}", inline=False)
        queue_em.set_footer(text=f"Viewing Page {self.page}/{pages}")
        return queue_em


class Disable:
    def __init__(self, client: discord.Bot, guild_id: int):
        self.client = client
        self.guild_id = guild_id

    # Disable queue menu
    async def edit_messages_async(self, queue_view, messages) -> None:
        tasks = [msg.edit(view=queue_view) for msg in messages]
        await asyncio.gather(*tasks)

    async def queue_msg(self) -> None:
        if store.queue_msg(self.guild_id):
            queue_view = QueueView(self.client, page=1, timeout=None)
            queue_view.disable_all_items()
            await self.edit_messages_async(queue_view, store.queue_msg(self.guild_id))
            store.queue_msg(self.guild_id, "clear")

    # Disable play message
    async def play_msg(self) -> None:
        play_msg = store.play_msg(self.guild_id)
        if play_msg:
            music_view = MusicView(self.client, timeout=None)
            music_view.disable_all_items()
            await play_msg.edit(view=music_view)


class Music(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client = client
        self.connection_loop.start()

    # Connect to lavalink
    def connect_lavalink(self):
        self.client.lavalink.add_node(
            host=config.lavalink["host"],
            port=config.lavalink["port"],
            password=config.lavalink["password"],
            region=config.lavalink["region"],
            ssl=config.lavalink["secure"],
        )

    @tasks.loop(seconds=0)
    async def connection_loop(self):
        await self.client.wait_until_ready()
        if not hasattr(self.client, "lavalink"):
            self.client.lavalink = lavalink.Client(self.client.user.id)
            self.connect_lavalink()
        if self.client.lavalink._event_hooks:
            self.client.lavalink._event_hooks.clear()
        self.client.lavalink.add_event_hooks(self)

    # Current voice
    def current_voice_channel(self, ctx: discord.ApplicationContext):
        if ctx.guild and ctx.guild.me.voice:
            return ctx.guild.me.voice.channel
        return None

    # Unloading cog
    def cog_unload(self):
        self.client.lavalink._event_hooks.clear()

    # Hooks
    @lavalink.listener(lavalink.TrackStartEvent)
    async def track_start_hook(self, event: lavalink.TrackStartEvent):
        """Hook for track start event."""
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(int(event.player.guild_id))
        vc: discord.VoiceChannel = self.client.get_channel(int(event.player.channel_id))
        if vc is not None:
            await vc.set_status(status=f"Playing {player.current.title}")
        channel = store.play_ch(event.player.guild_id)
        if channel:
            requester = f"<@{player.current.requester}>"
            if player.current.stream:
                duration = f"{emoji.live} LIVE"
            else:
                duration = datetime.timedelta(milliseconds=player.current.duration)
                duration = format_timedelta(duration, locale="en_IN")
            play_em = discord.Embed(
                title=f"{player.current.title}",
                url=f"{player.current.uri}",
                description=(
                    f"{emoji.user} **Requested By**: {requester if requester else 'Unknown'}\n"
                    f"{emoji.duration} **Duration**: {duration}"
                ),
                color=config.color.theme,
            )
            source_images = {
                "spotify": lambda: play_em.set_thumbnail(url=player.current.artwork_url),
                "soundcloud": lambda: play_em.set_thumbnail(url=player.current.artwork_url),
                "_": lambda: play_em.set_image(url=player.current.artwork_url),
            }
            (source_images.get(player.current.source_name) or source_images["_"])()
            music_view = MusicView(self.client, timeout=None)
            # Loop emoji
            if player.loop == player.LOOP_NONE:
                music_view.children[3].emoji = emoji.loop_white
            elif player.loop == player.LOOP_SINGLE:
                music_view.children[3].emoji = emoji.loop_one
            else:
                music_view.children[3].emoji = emoji.loop
            # Shuffle emoji
            if player.shuffle:
                music_view.children[4].emoji = emoji.shuffle
            else:
                music_view.children[4].emoji = emoji.shuffle_white
            # Player msg
            play_msg = await channel.send(embed=play_em, view=music_view)
            store.play_msg(event.player.guild_id, play_msg, "set")

    @lavalink.listener(lavalink.TrackEndEvent)
    async def track_end_hook(self, event: lavalink.TrackStartEvent):
        """Hook for track end event."""
        vc: discord.VoiceChannel = self.client.get_channel(int(event.player.channel_id))
        if vc is not None:
            await vc.set_status(status=None)
        await Disable(self.client, event.player.guild_id).play_msg()

    @lavalink.listener(lavalink.TrackStuckEvent, lavalink.TrackExceptionEvent)
    async def track_stuck_or_exception_hook(self, event: lavalink.TrackExceptionEvent):
        """Hook for track stuck event."""
        channel = store.play_ch(event.player.guild_id)
        if channel:
            error_em = discord.Embed(
                description=f"{emoji.error} Error while playing the track. Please try again later.",
                color=config.color.red,
            )
            await Disable(self.client, event.player.guild_id).play_msg()
            await channel.send(embed=error_em, delete_after=5)

    @lavalink.listener(lavalink.QueueEndEvent)
    async def queue_end_hook(self, event: lavalink.QueueEndEvent):
        """Hook for queue end event."""
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(int(event.player.guild_id))
        guild: discord.Guild = self.client.get_guild(int(event.player.guild_id))
        await player.clear_filters()
        await guild.voice_client.disconnect(force=True)
        await Disable(self.client, event.player.guild_id).queue_msg()

    # Ensures voice parameters
    async def ensure_voice(self, ctx: discord.ApplicationContext):
        """Checks all the voice parameters."""
        player: lavalink.DefaultPlayer | None = None
        if not ctx.author.voice or not ctx.author.voice.channel:
            error_em = discord.Embed(description=f"{emoji.error} Join a voice channel first.", color=config.color.red)
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.guild.id)
            permissions = ctx.author.voice.channel.permissions_for(ctx.me)
            if ctx.command.name in ("play",) and (
                self.current_voice_channel(ctx) is None
                or (self.current_voice_channel(ctx) is not None and not player.current)
            ):
                if not permissions.connect or not permissions.speak:
                    player = None
                    error_em = discord.Embed(
                        description=f"{emoji.error} I need the `Connect` and `Speak` permissions",
                        color=config.color.red,
                    )
                    await ctx.respond(embed=error_em, ephemeral=True)
                else:
                    if not self.client.lavalink.node_manager.available_nodes:
                        self.connect_lavalink()
                    await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
                    player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.guild.id)
                    store.play_ch(ctx.guild.id, ctx.channel, "set")
            else:
                if not player.current:
                    player = None
                    error_em = discord.Embed(
                        description=f"{emoji.error} Nothing is being played at the current moment.",
                        color=config.color.red,
                    )
                    await ctx.respond(embed=error_em, ephemeral=True)
                elif ctx.author.voice.channel.id != int(player.channel_id):
                    player = None
                    error_em = discord.Embed(
                        description=f"{emoji.error} You are not in my voice channel.", color=config.color.red
                    )
                    await ctx.respond(embed=error_em, ephemeral=True)
        return player

    # Search autocomplete
    async def search(self, ctx: discord.AutocompleteContext):
        """Searches a track from a given query."""
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.interaction.guild_id)
        tracks = []
        if ctx.value != "":
            result = await player.node.get_tracks(f"spsearch:{ctx.value}")
        else:
            result = await player.node.get_tracks("spsearch:top tracks")
        for track in result.tracks:
            dur = lavalink.format_time(track.duration)
            # Format: "Author - Title... - 00:00:00", max 100 chars
            max_len = 100
            dur_str = dur
            author = track.author
            title = track.title
            # Reserve space for author, duration, and separators
            reserved = len(author) + len(dur_str) + 6  # " - " x2 and possible "..."
            max_title_len = max(0, max_len - reserved)
            if len(title) > max_title_len:
                title = title[: max_title_len - 3] + "..."
            track_name = f"{author} - {title} - {dur_str}"
            tracks.append(track_name)
        return tracks

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

        if member.bot:  # Ignore bots
            return

        if hasattr(self.client, "lavalink"):
            player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(member.guild.id)
            if (
                not player or not player.is_connected
            ):  # We don't need to handle voice state updates if the player is not connected
                return

            bot_voice_channel = member.guild.me.voice.channel if member.guild.me.voice else None
            if (
                not bot_voice_channel
            ):  # We don't need to handle voice state updates if the bot is not in a voice channel
                return

            member_left_bot_channel = before.channel == bot_voice_channel and after.channel != bot_voice_channel
            member_joined_bot_channel = before.channel != bot_voice_channel and after.channel == bot_voice_channel

            if not (
                member_left_bot_channel or member_joined_bot_channel
            ):  # Only handle join/leave events in bot's voice channel
                return

            humans = [m for m in bot_voice_channel.members if not m.bot]

            if not humans:
                pending_inactivity_task = store.inactivity_task(member.guild.id, mode="get")
                if pending_inactivity_task:  # Clear any existing inactivity task
                    pending_inactivity_task.cancel()
                    store.inactivity_task(member.guild.id, mode="clear")

                # We can safely use local variables to store guild-specific data within this task, as each inactivity task is uniquely associated with its guild ID in the store, ensuring isolation between guilds.
                async def inactivity_task():  # Inactivity task to stop and disconnect the player
                    async def stop_and_disconnect():
                        """Stops the player and disconnects from the voice channel gracefully."""
                        await player.stop()
                        player.queue.clear()
                        await bot_voice_channel.guild.voice_client.disconnect(force=True)
                        disable = Disable(self.client, member.guild.id)
                        await disable.play_msg()
                        await disable.queue_msg()
                        play_ch = store.play_ch(member.guild.id)
                        if play_ch:
                            em = discord.Embed(
                                description=f"{emoji.leave} Left {bot_voice_channel.mention} due to inactivity.",
                                color=config.color.red,
                            )
                            await play_ch.send(embed=em)

                    is_paused_before = player.paused
                    await player.set_pause(True)  # Pause the player if no humans are in the voice channel
                    sleep_done: bool = False
                    try:
                        await asyncio.sleep(60)
                        sleep_done = True
                        current_humans = [m for m in bot_voice_channel.members if not m.bot]
                        if not current_humans:  # Double check if no humans are present
                            await stop_and_disconnect()
                    except asyncio.CancelledError:
                        if player.paused and not is_paused_before:
                            await player.set_pause(False)
                        if sleep_done:  # If the sleep was completed, we can safely stop and disconnect although the task was cancelled
                            await stop_and_disconnect()
                        else:
                            pass

                store.inactivity_task(guild_id=member.guild.id, task=asyncio.create_task(inactivity_task()), mode="set")
            else:  # If humans are present in the voice channel
                inactivity_task = store.inactivity_task(member.guild.id, mode="get")
                if inactivity_task:  # Cancel the inactivity task
                    inactivity_task.cancel()
                    store.inactivity_task(member.guild.id, mode="clear")

    # Play
    @slash_command(name="play")
    @option("query", description="Enter your track name/link or playlist link", autocomplete=search)
    async def play(self, ctx: discord.ApplicationContext, query: str):
        """Searches and plays a track from a given query."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        sources = {
            "spotify": {"emoji": emoji.spotify, "color": config.color.green},
            "youtube": {"emoji": emoji.youtube, "color": config.color.red},
            "soundcloud": {"emoji": emoji.soundcloud, "color": config.color.orange},
            "_": {"emoji": emoji.music, "color": config.color.theme},
        }
        if player:
            await ctx.defer()
            query = query.strip("<>")
            # Remove durations like 00:00:00 from query
            query = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", query).strip()
            embed = discord.Embed()
            if not url_rx.match(query):
                query = f"spsearch:{query}"
            results = await player.node.get_tracks(query)
            if not results or not results.tracks:
                error_em = discord.Embed(
                    description=f"{emoji.error} No track found from the given query.", color=config.color.red
                )
                await ctx.respond(embed=error_em, ephemeral=True)
            if results.load_type == lavalink.LoadType.PLAYLIST:
                tracks = results.tracks
                src = results.tracks[0].source_name
                src_info = sources.get(src, sources["_"])
                embed.color = src_info["color"]
                for track in tracks:
                    player.add(requester=ctx.author.id, track=track)
                embed.description = (
                    f"{src_info['emoji']} Added **{results.playlist_info.name}** with `{len(tracks)}` tracks."
                )
                await ctx.respond(embed=embed)
            elif results.tracks:
                track = results.tracks[0]
                player.add(requester=ctx.author.id, track=track)
                src_info = sources.get(track.source_name, sources["_"])
                embed.color = src_info["color"]
                dur: str
                if track.stream:
                    dur = f"{emoji.live} LIVE"
                else:
                    dur = format_timedelta(datetime.timedelta(milliseconds=track.duration))
                embed.description = f"{src_info['emoji']} Added **[{track.title}]({track.uri})** - {dur}."
                await ctx.respond(embed=embed)
            if not player.is_playing:
                await player.play()

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
            equalizer = store.equalizer(ctx.guild.id)
            loop = ""
            if player.loop == player.LOOP_NONE:
                loop = "Disabled"
            elif player.loop == player.LOOP_SINGLE:
                loop = "Track"
            elif player.loop == player.LOOP_QUEUE:
                loop = "Queue"
            play_em = discord.Embed(
                title=f"{player.current.title}",
                url=f"{player.current.uri}",
                description=(
                    f"{emoji.user} **Requested By**: {requester.mention if requester else 'Unknown'}\n"
                    f"{emoji.duration} **Duration**: {duration}\n"
                    f"{emoji.volume} **Volume**: `{player.volume}%`\n"
                    f"{emoji.loop} **Loop**: {loop}\n"
                    f"{emoji.shuffle} **Shuffle**: {'Enabled' if player.shuffle else 'Disabled'}\n"
                    f"{emoji.equalizer} **Equalizer**: `{equalizer}`"
                    f"{f'\n\n {bar}' if bar else ''}"
                ),
                color=config.color.theme,
            )
            play_em.set_thumbnail(url=player.current.artwork_url)
            await ctx.respond(embed=play_em)

    # Equalizer
    @slash_command(name="equalizer")
    @option(
        "equalizer", description="Choose your equalizer", choices=list(equalizer_presets.presets.keys()) + ["Reset"]
    )
    async def equalizer(self, ctx: discord.ApplicationContext, equalizer: str):
        """Equalizer to change track quality."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if equalizer == "Reset":
                await player.clear_filters()
                eq_em = discord.Embed(
                    description=f"{emoji.success} Reset the equalizer.",
                    color=config.color.green,
                )
                store.equalizer(guild_id=ctx.guild.id, name="None", mode="set")
            else:
                for eq_name, eq_gains in equalizer_presets.presets.items():
                    if eq_name == equalizer:
                        eq = lavalink.Equalizer()
                        eq.update(bands=eq_gains)
                        await player.set_filter(eq)
                        eq_em = discord.Embed(
                            description=f"{emoji.equalizer} Applied `{equalizer}` equalizer",
                            color=config.color.theme,
                        )
                        store.equalizer(guild_id=ctx.guild.id, name=equalizer, mode="set")
            await ctx.respond(embed=eq_em)

    # Stop
    @slash_command(name="stop")
    async def stop(self, ctx: discord.ApplicationContext):
        """Destroys the player."""
        await ctx.defer()
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            player.queue.clear()
            await player.stop()
            await ctx.guild.me.voice.channel.set_status(status=None)
            await ctx.guild.voice_client.disconnect(force=True)
            stop_embed = discord.Embed(description=f"{emoji.stop} Player destroyed.", color=config.color.theme)
            disable = Disable(self.client, ctx.guild.id)
            await disable.play_msg()
            await ctx.respond(embed=stop_embed)
            await disable.queue_msg()

    # Seek
    @slash_command(name="seek")
    @option("seconds", description="Enter track position in seconds")
    async def seek(self, ctx: discord.ApplicationContext, seconds: int):
        """Seeks to a given position in a track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            track_time = player.position + (seconds * 1000)
            if player.current.duration > track_time:
                await player.seek(track_time)
                seek_em = discord.Embed(
                    description=f"{emoji.seek} Moved track to `{lavalink.format_time(track_time)}`.",
                    color=config.color.theme,
                )
                await ctx.respond(embed=seek_em)
            elif player.current.duration <= track_time:
                await self.skip()

    # Skip
    @slash_command(name="skip")
    async def skip(self, ctx: discord.ApplicationContext):
        """Skips the current playing track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            skip_em = discord.Embed(description=f"{emoji.skip} Skipped the track.", color=config.color.theme)
            await Disable(self.client, ctx.guild.id).play_msg()
            await player.skip()
            await ctx.respond(embed=skip_em)

    # Skip to
    @slash_command(name="skip-to")
    @option("track", description="Enter your track index number to skip")
    async def skip_to(self, ctx: discord.ApplicationContext, track: int):
        """Skips to a given track in the queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await ctx.defer()
            if track < 1 or track > len(player.queue):
                error_em = discord.Embed(
                    description=f"{emoji.error} Track number must be between `1` and `{len(player.queue)}`",
                    color=config.color.red,
                )
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                player.queue = player.queue[track - 1 :]
                await player.skip()
                skip_em = discord.Embed(
                    description=f"{emoji.skip} Skipped to track `{track}`.",
                    color=config.color.theme,
                )
                await ctx.respond(embed=skip_em)

    # Pause
    @slash_command(name="pause")
    async def pause(self, ctx: discord.ApplicationContext):
        """Pauses the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                error_em = discord.Embed(description=f"{emoji.error} Player is already paused", color=config.color.red)
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                await player.set_pause(True)
                pause_em = discord.Embed(
                    description=f"{emoji.pause} Player paused.",
                    color=config.color.theme,
                )
                await ctx.respond(embed=pause_em)

    # Resume
    @slash_command(name="resume")
    async def resume(self, ctx: discord.ApplicationContext):
        """Resumes the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                await player.set_pause(False)
                resume_em = discord.Embed(
                    description=f"{emoji.play} Player resumed.",
                    color=config.color.theme,
                )
                await ctx.respond(embed=resume_em)
            else:
                error_em = discord.Embed(description=f"{emoji.error} Player is not paused", color=config.color.red)
                await ctx.respond(embed=error_em, ephemeral=True)

    # Volume
    @slash_command(name="volume")
    @option("volume", description="Enter your volume amount from 1 - 100")
    async def volume(self, ctx: discord.ApplicationContext, volume: int):
        """Changes the player's volume 1 - 100."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            volume_condition = [volume < 1, volume > 100]
            if any(volume_condition):
                error_em = discord.Embed(
                    description=f"{emoji.error} Volume amount must be between `1` - `100`", color=config.color.red
                )
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                await player.set_volume(volume)
                vol_em = discord.Embed(
                    description=f"{emoji.volume} Volume changed to `{player.volume}%`.",
                    color=config.color.theme,
                )
                await ctx.respond(embed=vol_em)

    # Queue
    @slash_command(name="queue")
    @option("page", description="Enter queue page number", default=1, required=False)
    async def queue(self, ctx: discord.ApplicationContext, page: int = 1):
        """Shows the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            items_per_page = 5
            pages = math.ceil(len(player.queue) / items_per_page)
            if not player.queue:
                error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=config.color.red)
                await ctx.respond(embed=error_em, ephemeral=True)
            elif page > pages or page < 1:
                error_em = discord.Embed(
                    description=f"{emoji.error} Page has to be between `1` to `{pages}`", color=config.color.red
                )
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                queue_obj = QueueEmbed(self.client, ctx, page)
                queue_em = await queue_obj.get_embed()
                if pages > 1:
                    queue_view = QueueView(client=self.client, page=page, timeout=60)
                    queue_msg = await ctx.respond(embed=queue_em, view=queue_view)
                    store.queue_msg(ctx.guild.id, queue_msg, "set")
                else:
                    await ctx.respond(embed=queue_em)

    # Shuffle
    @slash_command(name="shuffle")
    async def shuffle(self, ctx: discord.ApplicationContext):
        """Shuffles the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if not player.queue:
                error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=config.color.red)
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                player.shuffle = not player.shuffle
                shuffle_em = discord.Embed(
                    description=f"{emoji.shuffle} {'Enabled' if player.shuffle else 'Disabled'} shuffle.",
                    color=config.color.theme,
                )
                await ctx.respond(embed=shuffle_em)

    # Loop
    @slash_command(name="loop")
    @option("mode", description="Enter loop mode", choices=["OFF", "Queue", "Track"])
    async def loop(self, ctx: discord.ApplicationContext, mode: str):
        """Loops the current queue until the command is invoked again or until a new track is enqueued."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            _emoji = ""
            if mode == "OFF":
                player.set_loop(0)
                _emoji = emoji.loop_white
            elif mode == "Track":
                player.set_loop(1)
                _emoji = emoji.loop_one
            elif mode == "Queue":
                if not player.queue:
                    error_em = discord.Embed(description=f"{emoji.error} Queue is empty.", color=config.color.red)
                    await ctx.respond(embed=error_em, ephemeral=True)
                    return
                else:
                    player.set_loop(2)
                    _emoji = emoji.loop
            loop_em = discord.Embed(
                description=f"{_emoji} {'Enabled' if mode != 'OFF' else 'Disabled'} {mode if mode != 'OFF' else ''} Loop.",
                color=config.color.theme,
            )
            await ctx.respond(embed=loop_em)

    # Remove
    @slash_command(name="remove")
    @option("index", description="Enter your track index number")
    async def remove(self, ctx: discord.ApplicationContext, index: int):
        """Removes a track from the player's queue with the given index."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if ctx.author.id == player.queue[index - 1].requester:
                if not player.queue:
                    error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=config.color.red)
                    await ctx.respond(embed=error_em, ephemeral=True)
                elif index > len(player.queue) or index < 1:
                    error_em = discord.Embed(
                        description=f"{emoji.error} Index has to be between `1` to `{len(player.queue)}`",
                        color=config.color.red,
                    )
                    await ctx.respond(embed=error_em, ephemeral=True)
                else:
                    removed = player.queue.pop(index - 1)
                    remove_em = discord.Embed(
                        title="Track Removed",
                        description=f"**{removed.title}**",
                        color=config.color.red,
                    )
                    await ctx.respond(embed=remove_em)
            else:
                error_em = discord.Embed(
                    description=f"{emoji.error} Only requester can remove from the list.", color=config.color.red
                )
                await ctx.respond(embed=error_em, ephemeral=True)


def setup(client: discord.Bot):
    client.add_cog(Music(client))
