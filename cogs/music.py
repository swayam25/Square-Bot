import asyncio
import datetime
import discord
import lavalink
import math
import re
from babel.dates import format_timedelta
from core import Client
from core.view import DesignerView
from discord import SlashCommandGroup
from discord.commands import option, slash_command
from discord.ext import commands, tasks
from discord.ui import ActionRow, Button, Container, Section, Separator, TextDisplay, Thumbnail
from music import store
from music.client import LavalinkVoiceClient
from utils import config
from utils.emoji import emoji
from utils.helpers import parse_duration

# Regex
url_rx = re.compile("https?:\\/\\/(?:www\\.)?.+")

# Music sources
sources = {
    "spotify": {"emoji": emoji.spotify, "color": config.color.green},
    "youtube": {"emoji": emoji.youtube, "color": config.color.red},
    "soundcloud": {"emoji": emoji.soundcloud, "color": config.color.orange},
    "_": {"emoji": emoji.music, "color": config.color.theme},
}


async def update_play_msg(client: Client, guild_id: int):
    """
    Updates the play message with the current player status.

    Parameters:
        client (Client): The Discord bot client.
        guild_id (int): The ID of the guild to update the play message for.
    """
    player: lavalink.DefaultPlayer = client.lavalink.player_manager.get(guild_id)
    if player and player.is_connected:
        play_msg, _ = store.play_msg(player.guild_id)
        if play_msg:
            view = MusicView(client, guild_id)
            try:
                await play_msg.edit(view=view)
            except discord.NotFound:
                store.play_msg(guild_id, "clear")
                return


async def stop_player(player: lavalink.DefaultPlayer, guild: discord.Guild):
    await player.stop()
    await guild.me.voice.channel.set_status(status=None)
    await guild.voice_client.disconnect(force=True)

    async def background_cleanup():
        player.queue.clear()
        player.set_loop(player.LOOP_NONE)
        player.set_shuffle(False)
        await player.clear_filters()
        await player.set_volume(100)

    asyncio.create_task(background_cleanup())


async def music_interaction_check(view: DesignerView, player: lavalink.DefaultPlayer, interaction: discord.Interaction):
    if not player or not player.current:
        err_view = DesignerView(
            Container(
                TextDisplay(f"{emoji.error} Nothing is being played at the current moment."),
                color=config.color.red,
            )
        )
        view.disable_all_items()
        await interaction.edit(view=view)
        await interaction.followup.send(view=err_view, ephemeral=True)
        return False
    elif not interaction.user.voice:
        err_view = DesignerView(
            Container(
                TextDisplay(f"{emoji.error} Join a voice channel first."),
                color=config.color.red,
            )
        )
        await interaction.response.send_message(view=err_view, ephemeral=True)
        return False
    elif player.is_connected and interaction.user.voice.channel.id != int(player.channel_id):
        err_view = DesignerView(
            Container(
                TextDisplay(f"{emoji.error} You are not in my voice channel."),
                color=config.color.red,
            )
        )
        await interaction.response.send_message(view=err_view, ephemeral=True)
        return False
    else:
        return True


class MusicContainer(Container):
    def __init__(self, player: lavalink.DefaultPlayer):
        super().__init__()
        requester = f"<@{player.current.requester}>"
        if player.current.stream:
            duration = f"{emoji.live} LIVE"
        else:
            duration = datetime.timedelta(milliseconds=player.current.duration)
            duration = format_timedelta(duration)
        self.items = [
            Section(
                TextDisplay(f"## [{player.current.title}]({player.current.uri})"),
                TextDisplay(
                    f"{emoji.user} **Requested By**: {requester if requester else 'Unknown'}\n"
                    f"{emoji.mic} **Artist**: {sources.get(player.current.source_name, sources['_'])['emoji']} {player.current.author}\n"
                    f"{emoji.duration} **Duration**: {duration}"
                ),
                accessory=Thumbnail(url=player.current.artwork_url),
            )
        ]


class MusicView(DesignerView):
    def __init__(self, client: Client, guild_id: int):
        super().__init__(timeout=None)
        self.client = client
        self.player: lavalink.DefaultPlayer = client.lavalink.player_manager.get(guild_id)
        self.interaction_check = lambda interaction: music_interaction_check(
            player=self.player, interaction=interaction, view=self
        )
        self.build()

    # Builder
    def build(self):
        self.clear_items()
        self.add_item(MusicContainer(self.player))
        self.add_item(row := ActionRow())
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
            btn = Button(emoji=btn_emoji, custom_id=action, style=discord.ButtonStyle.grey)
            btn.callback = getattr(self, f"{action}_callback")
            row.add_item(btn)

    # Pause / Resume
    async def pause_callback(self, interaction: discord.Interaction):
        button: Button = self.get_item("pause")
        if not self.player.paused:
            await self.player.set_pause(True)
        elif self.player.paused:
            await self.player.set_pause(False)
        button.emoji = emoji.play_white if self.player.paused else emoji.pause_white
        view = DesignerView(
            Container(
                TextDisplay(f"{interaction.user.mention} {'Paused' if self.player.paused else 'Resumed'} the player."),
            )
        )
        await interaction.edit(view=self)
        await interaction.followup.send(view=view, delete_after=5)

    # Stop
    async def stop_callback(self, interaction: discord.Interaction):
        guild: discord.Guild = self.client.get_guild(int(interaction.guild_id))

        view = DesignerView(Container(TextDisplay(f"{interaction.user.mention} Destroyed the player.")))
        self.disable_all_items()
        await interaction.edit(view=self)
        await interaction.followup.send(view=view, delete_after=5)
        store.play_msg(interaction.guild_id, mode="clear")
        await stop_player(self.player, guild)

    # Skip
    async def skip_callback(self, interaction: discord.Interaction):
        await self.player.skip()
        self.disable_all_items()
        await interaction.edit(view=self)
        view = DesignerView(
            Container(
                TextDisplay(f"{interaction.user.mention} Skipped the track."),
            )
        )
        await interaction.followup.send(view=view, delete_after=5)

    # Loop
    async def loop_callback(self, interaction: discord.Interaction):
        button: Button = self.get_item("loop")
        if self.player.loop == self.player.LOOP_NONE:
            self.player.set_loop(1)
            button.emoji = emoji.loop_one
            mode = "Track"
        elif self.player.loop == self.player.LOOP_SINGLE and self.player.queue:
            self.player.set_loop(2)
            button.emoji = emoji.loop
            mode = "Queue"
        else:
            self.player.set_loop(0)
            button.emoji = emoji.loop_white
            mode = "Disable"
        view = DesignerView(
            Container(
                TextDisplay(
                    f"{interaction.user.mention} {'Enabled' if mode != 'Disable' else 'Disabled'} {mode} loop."
                ),
            )
        )
        await interaction.edit(view=self)
        await interaction.followup.send(view=view, delete_after=5)

    # Shuffle
    async def shuffle_callback(self, interaction: discord.Interaction):
        button: Button = self.get_item("shuffle")
        if not self.player.queue:
            err_view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.error} Queue is empty."),
                    color=config.color.red,
                )
            )
            await interaction.response.send_message(view=err_view, ephemeral=True)
        else:
            self.player.set_shuffle(not self.player.shuffle)
            button.emoji = emoji.shuffle if self.player.shuffle else emoji.shuffle_white
            shuffle_view = DesignerView(
                Container(
                    TextDisplay(
                        f"{interaction.user.mention} {'Enabled' if self.player.shuffle else 'Disabled'} shuffle."
                    ),
                )
            )
            await interaction.edit(view=self)
            await interaction.followup.send(view=shuffle_view, delete_after=5)


class QueueBtnCallback:
    @staticmethod
    async def queue_btn_callback(
        i: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: "QueueListView"
    ):
        """
        Callback for Queue button (for more options).
        Toggles the visibility of action buttons for the specific track.

        Parameters:
            i (discord.Interaction): The interaction object.
            player (lavalink.DefaultPlayer): The lavalink player instance.
            track_index (int): The index of the track in the queue.
            queue_view (QueueListView): The parent queue view for updating.
        """
        if not player or not player.queue or track_index >= len(player.queue) or not queue_view:
            return

        # Toggle action buttons visibility for this track
        queue_view.toggle_action_buttons(track_index)
        queue_view.build()
        await i.response.edit_message(view=queue_view)

    @staticmethod
    async def move_up_callback(
        interaction: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: "QueueListView"
    ):
        """Move track up in the queue."""
        if track_index <= 0:
            return

        # Store the new position after move
        new_index = track_index - 1

        player.queue[track_index], player.queue[new_index] = (
            player.queue[new_index],
            player.queue[track_index],
        )

        if track_index == queue_view.visible_action_button:
            queue_view.visible_action_button = new_index

        # Check if track moved out of current page view and adjust page if needed
        current_page_start = (queue_view.page - 1) * queue_view.items_per_page

        # If the new position is before the current page, go to the page containing the track
        if new_index < current_page_start:
            queue_view.page = (new_index // queue_view.items_per_page) + 1

        await _update_queue_view(interaction, queue_view)

    @staticmethod
    async def move_down_callback(
        interaction: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: "QueueListView"
    ):
        """Move track down in the queue."""
        if track_index >= len(player.queue) - 1:
            return

        # Store the new position after move
        new_index = track_index + 1

        player.queue[track_index], player.queue[new_index] = (
            player.queue[new_index],
            player.queue[track_index],
        )

        if track_index == queue_view.visible_action_button:
            queue_view.visible_action_button = new_index

        # Check if track moved out of current page view and adjust page if needed
        current_page_start = (queue_view.page - 1) * queue_view.items_per_page
        current_page_end = current_page_start + queue_view.items_per_page - 1

        # If the new position is after the current page, go to the page containing the track
        if new_index > current_page_end:
            queue_view.page = (new_index // queue_view.items_per_page) + 1

        await _update_queue_view(interaction, queue_view)

    @staticmethod
    async def remove_callback(
        interaction: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: "QueueListView"
    ):
        """Remove track from the queue."""
        if track_index >= len(player.queue):
            return

        player.queue.pop(track_index)

        # Remove from visible action buttons and adjust indices
        queue_view.visible_action_button = None

        # Check if current page becomes empty and navigate to previous page if needed
        total_pages = max(1, math.ceil(len(player.queue) / queue_view.items_per_page))
        if queue_view.page > total_pages and total_pages > 0:
            queue_view.page = total_pages

        queue_view.build()
        await interaction.response.edit_message(view=queue_view)

    @staticmethod
    async def play_now_callback(
        interaction: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: "QueueListView"
    ):
        """Skip to this track immediately."""
        if track_index >= len(player.queue):
            return

        await player.play_track(player.queue.pop(track_index))

        # Check if current page becomes empty and navigate to previous page if needed
        total_pages = max(1, math.ceil(len(player.queue) / queue_view.items_per_page))
        if queue_view.page > total_pages and total_pages > 0:
            queue_view.page = total_pages

        await _update_queue_view(interaction, queue_view)


async def _update_queue_view(interaction: discord.Interaction, queue_view: "QueueListView"):
    """Helper method to update queue view and respond."""
    queue_view.build()
    await interaction.response.edit_message(view=queue_view)


class QueueContainer(Container):
    def __init__(
        self, player: lavalink.DefaultPlayer, ctx: discord.ApplicationContext, page=1, items_per_page=5, queue_view=None
    ):
        super().__init__()
        pages = max(1, math.ceil(len(player.queue) / items_per_page))
        start = (page - 1) * items_per_page
        end = start + items_per_page
        queue_list: list = []

        for index, track in enumerate(player.queue[start:end], start=start):
            requester = ctx.guild.get_member(track.requester)
            btn = Button(emoji=emoji.more_white)
            # Create a closure that captures the current index value
            btn.callback = lambda i, track_idx=index: QueueBtnCallback.queue_btn_callback(
                i, player=player, track_index=track_idx, queue_view=queue_view
            )

            # Add the section for the track
            queue_list.append(
                Section(
                    TextDisplay(
                        f"`{index + 1}.` [**{track.title}** by **{track.author}**]({track.uri}) [`{lavalink.format_time(track.duration)}`]\n"
                        f"-# {emoji.bottom_right} {requester.mention if requester else 'Unknown'}"
                    ),
                    accessory=btn,
                )
            )

            # Add action buttons if this track's buttons are visible
            if queue_view and index == queue_view.visible_action_button:
                move_up_btn = Button(emoji=emoji.up_white, style=discord.ButtonStyle.grey, disabled=(index == 0))
                move_up_btn.callback = lambda i, track_idx=index: QueueBtnCallback.move_up_callback(
                    i, player=player, track_index=track_idx, queue_view=queue_view
                )
                move_down_btn = Button(
                    emoji=emoji.down_white, style=discord.ButtonStyle.grey, disabled=(index == len(player.queue) - 1)
                )
                move_down_btn.callback = lambda i, track_idx=index: QueueBtnCallback.move_down_callback(
                    i, player=player, track_index=track_idx, queue_view=queue_view
                )
                remove_btn = Button(emoji=emoji.bin_white, style=discord.ButtonStyle.grey)
                remove_btn.callback = lambda i, track_idx=index: QueueBtnCallback.remove_callback(
                    i, player=player, track_index=track_idx, queue_view=queue_view
                )
                play_now_btn = Button(emoji=emoji.play_white, style=discord.ButtonStyle.grey)
                play_now_btn.callback = lambda i, track_idx=index: QueueBtnCallback.play_now_callback(
                    i, player=player, track_index=track_idx, queue_view=queue_view
                )
                queue_list.append(ActionRow(move_up_btn, move_down_btn, remove_btn, play_now_btn))

        current_requester = ctx.guild.get_member(player.current.requester) if player.current else None
        self.add_item(TextDisplay(f"## {ctx.guild.name}'s Queue"))
        self.add_item(
            TextDisplay(
                f"`0.` [**{player.current.title}** by **{player.current.author}**]({player.current.uri}) [`{lavalink.format_time(player.current.duration)}`]\n"
                f"-# {emoji.bottom_right} {current_requester.mention if current_requester else 'Unknown'}"
                if player.current
                else "No track playing."
            )
        )
        if queue_list:
            self.add_item(TextDisplay(f"### Queued {len(player.queue)} Tracks"))
            self.items.extend(queue_list)
        else:
            self.add_item(TextDisplay("Queue is empty."))
        if len(player.queue) > items_per_page:
            self.add_item(Separator())
            self.add_item(TextDisplay(f"-# Viewing Page {page}/{pages}"))


class QueueListView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, page: int = 1):
        super().__init__()
        self.client = client
        self.ctx = ctx
        self.page = page
        self.items_per_page = 5
        self.player: lavalink.DefaultPlayer = client.lavalink.player_manager.get(ctx.guild.id)
        self.interaction_check = lambda interaction: music_interaction_check(
            player=self.player, interaction=interaction, view=self
        )
        self.visible_action_button: int | None = None
        self.build()

    def toggle_action_buttons(self, track_index: int):
        """Toggle the visibility of action buttons for a specific track."""
        if track_index == self.visible_action_button:
            self.visible_action_button = None
        else:
            self.visible_action_button = track_index

    def build(self):
        self.clear_items()
        self.add_item(
            QueueContainer(self.player, self.ctx, page=self.page, items_per_page=self.items_per_page, queue_view=self)
        )
        total_pages = max(1, math.ceil(len(self.player.queue) / self.items_per_page))
        if total_pages > 1:
            self.add_item(row := ActionRow())
            for btn_emoji, action in [
                (emoji.start_white, "start"),
                (emoji.previous_white, "previous"),
                (emoji.next_white, "next"),
                (emoji.end_white, "end"),
            ]:
                btn = Button(emoji=btn_emoji, style=discord.ButtonStyle.grey)
                btn.callback = lambda i, action=action: self.interaction_callback(i, action=action)
                row.add_item(btn)

    async def interaction_callback(self, interaction: discord.Interaction, action: str):
        total_pages = max(1, math.ceil(len(self.player.queue) / self.items_per_page))
        if action == "start":
            self.page = 1
        elif action == "previous":
            self.page = total_pages if self.page <= 1 else self.page - 1
        elif action == "next":
            self.page = 1 if self.page >= total_pages else self.page + 1
        elif action == "end":
            self.page = total_pages
        self.build()
        await interaction.edit(view=self)


class Disable:
    def __init__(self, client: Client, guild_id: int):
        self.client = client
        self.guild_id = guild_id

    # Disable play message
    async def play_msg(self) -> None:
        play_msg, play_view = store.play_msg(self.guild_id)
        if play_msg:
            play_view.disable_all_items()
            try:
                await play_msg.edit(view=play_view)
            except discord.NotFound:
                store.play_msg(self.guild_id, "clear")
                return


class Music(commands.Cog):
    def __init__(self, client: Client):
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
        if self.client.lavalink is None:
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
            await vc.set_status(status=f"Playing **{player.current.title}**")
        channel = store.play_ch(event.player.guild_id)
        if channel:
            view = MusicView(client=self.client, guild_id=event.player.guild_id)
            try:
                play_msg = await channel.send(view=view)
            except discord.Forbidden:
                store.play_ch(event.player.guild_id, "clear")
                return
            store.play_msg(event.player.guild_id, play_msg, view, "set")

    @lavalink.listener(lavalink.TrackEndEvent)
    async def track_end_hook(self, event: lavalink.TrackEndEvent):
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
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.error} Track is stuck or an error occurred while playing the track."),
                    color=config.color.red,
                )
            )
            await Disable(self.client, event.player.guild_id).play_msg()
            try:
                await channel.send(view=view, delete_after=5)
            except discord.Forbidden:
                store.play_ch(event.player.guild_id, "clear")
                return

    @lavalink.listener(lavalink.QueueEndEvent)
    async def queue_end_hook(self, event: lavalink.QueueEndEvent):
        """Hook for queue end event."""
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(int(event.player.guild_id))
        guild: discord.Guild = self.client.get_guild(int(event.player.guild_id))
        await stop_player(player, guild)

    # Ensures voice parameters
    async def ensure_voice(self, ctx: discord.ApplicationContext):
        """Checks all the voice parameters."""
        player: lavalink.DefaultPlayer | None = None
        if not ctx.author.voice or not ctx.author.voice.channel:
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.error} Join a voice channel first."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.guild.id)
            permissions = ctx.author.voice.channel.permissions_for(ctx.me)
            if ctx.command.name in ("play",) and (
                self.current_voice_channel(ctx) is None
                or (self.current_voice_channel(ctx) is not None and not player.current)
            ):
                if not permissions.connect or not permissions.speak:
                    player = None
                    view = DesignerView(
                        Container(
                            TextDisplay(f"{emoji.error} I need the `Connect` and `Speak` permissions."),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view, ephemeral=True)
                else:
                    if not self.client.lavalink.node_manager.available_nodes:
                        self.connect_lavalink()
                    await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
                    player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.guild.id)
                    store.play_ch(ctx.guild.id, ctx.channel, "set")
            elif not player.current:
                player = None
                err_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Nothing is being played at the current moment."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=err_view, ephemeral=True)
            elif ctx.author.voice.channel.id != int(player.channel_id):
                player = None
                err_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} You are not in my voice channel."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=err_view, ephemeral=True)
        return player

    # Search autocomplete
    async def search(self, ctx: discord.AutocompleteContext):
        """Searches a track from a given query."""
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.interaction.guild_id)
        tracks = []
        if re.match(url_rx, ctx.value):
            return tracks
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

    # Track autocomplete
    async def track_autocomplete(self, ctx: discord.AutocompleteContext):
        """Provides track indices for removal."""
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(ctx.interaction.guild_id)
        if not player or not player.queue:
            return []
        # Return track indices and names in the format "{index}. {name}"
        result = []
        for i, track in enumerate(player.queue):
            title = track.title
            # Limit title length to 100 characters
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
                        disable = Disable(self.client, member.guild.id)
                        await disable.play_msg()
                        await stop_player(player, bot_voice_channel.guild)
                        play_ch = store.play_ch(member.guild.id)
                        if play_ch:
                            view = DesignerView(
                                Container(
                                    TextDisplay(f"{emoji.leave} Left {bot_voice_channel.mention} due to inactivity."),
                                    color=config.color.red,
                                )
                            )
                            try:
                                await play_ch.send(view=view)
                            except discord.Forbidden:
                                store.play_ch(member.guild.id, "clear")

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
        if player:
            await ctx.defer()
            query = query.strip("<>")
            # Remove durations like 00:00:00 from query
            query = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b|\s*-\s*\d{1,2}:\d{2}(?::\d{2})?\b", "", query)
            container = Container()
            if not url_rx.match(query):
                query = f"spsearch:{query}"
            results = await player.node.get_tracks(query)
            if not results or not results.tracks:
                view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} No track found from the given query."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
            if results.load_type == lavalink.LoadType.PLAYLIST:
                tracks = results.tracks
                src = results.tracks[0].source_name
                src_info = sources.get(src, sources["_"])
                container.color = int(src_info["color"])
                for track in tracks:
                    player.add(requester=ctx.author.id, track=track)
                container.add_text(
                    f"{src_info['emoji']} Added **{results.playlist_info.name}** with `{len(tracks)}` tracks."
                )
                await ctx.respond(view=DesignerView(container))
            elif results.tracks:
                track = results.tracks[0]
                player.add(requester=ctx.author.id, track=track)
                src_info = sources.get(track.source_name, sources["_"])
                container.color = int(src_info["color"])
                dur: str
                if track.stream:
                    dur = f"{emoji.live} LIVE"
                else:
                    dur = format_timedelta(datetime.timedelta(milliseconds=track.duration))
                container.add_text(
                    f"{src_info['emoji']} Added [**{track.title}** by **{track.author}**]({track.uri}) [`{dur}`]."
                )
                await ctx.respond(view=DesignerView(container))
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
            loop = ""
            if player.loop == player.LOOP_NONE:
                loop = "Disabled"
            elif player.loop == player.LOOP_SINGLE:
                loop = "Track"
            elif player.loop == player.LOOP_QUEUE:
                loop = "Queue"
            view = DesignerView(
                Container(
                    Section(
                        TextDisplay(f"## [{player.current.title}]({player.current.uri})"),
                        TextDisplay(
                            f"{emoji.user} **Requested By**: {requester.mention if requester else 'Unknown'}\n"
                            f"{emoji.mic} **Artist**: {sources.get(player.current.source_name, sources['_'])['emoji']} {player.current.author}\n"
                            f"{emoji.duration} **Duration**: {duration}\n"
                            f"{emoji.volume} **Volume**: `{player.volume}%`\n"
                            f"{emoji.loop} **Loop**: {loop}\n"
                            f"{emoji.shuffle} **Shuffle**: {'Enabled' if player.shuffle else 'Disabled'}\n"
                            f"{emoji.equalizer} **Equalizers**: {', '.join([name.title() for name in player.filters]) if player.filters else 'None'}"
                            f"{f'\n\n {bar}' if bar else ''}"
                        ),
                        accessory=Thumbnail(url=player.current.artwork_url) if player.current.artwork_url else None,
                    )
                )
            )
            await ctx.respond(view=view)

    # Equalizer slash cmd group
    eq = SlashCommandGroup(name="eq", description="Equalizer commands.")

    @eq.command(name="reset")
    async def reset(self, ctx: discord.ApplicationContext):
        """Resets the equalizer to default."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await player.clear_filters()
            view = DesignerView(Container(TextDisplay(f"{emoji.equalizer} Reset equalizer to default settings.")))
            await ctx.respond(view=view)

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
                view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.equalizer} Removed **{name.title()}** equalizer."),
                    )
                )
                await ctx.respond(view=view)
            else:
                view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} **{name}** equalizer not found."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    @eq.command(name="karaoke")
    @option(
        "intensity",
        description="Karaoke intensity: Light, Medium, or Strong",
        choices=["Light", "Medium", "Strong"],
        required=False,
    )
    async def karaoke(
        self,
        ctx: discord.ApplicationContext,
        intensity: str = "Medium",
    ):
        """Remove center vocals for karaoke effect."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            # Preset configurations optimized for vocal removal
            presets = {
                "Light": {"level": 1.5, "mono_level": 0.8, "filter_band": 220.0, "filter_width": 100.0},
                "Medium": {"level": 2.0, "mono_level": 1.0, "filter_band": 220.0, "filter_width": 100.0},
                "Strong": {"level": 3.0, "mono_level": 1.2, "filter_band": 220.0, "filter_width": 100.0},
            }
            config = presets[intensity]
            eq = lavalink.Karaoke()
            eq.update(
                level=config["level"],
                mono_level=config["mono_level"],
                filter_band=config["filter_band"],
                filter_width=config["filter_width"],
            )
            await player.set_filter(eq)
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.equalizer} Applied **Karaoke** ({intensity}) equalizer."),
                )
            )
            await ctx.respond(view=view)

    @eq.command(name="timescale")
    @option(
        "speed",
        description="Playback speed multiplier",
        choices=["0.5x", "1x", "1.5x", "2x", "3x", "4x", "5x", "6x", "10x", "Nightcore", "Daycore"],
        required=False,
    )
    async def timescale(
        self,
        ctx: discord.ApplicationContext,
        speed: str = "1x",
    ):
        """Change playback speed and pitch."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Nightcore": {"speed": 1.3, "pitch": 1.3, "rate": 1.0},
                "Daycore": {"speed": 0.7, "pitch": 0.7, "rate": 1.0},
            }

            if speed in presets:
                config = presets[speed]
                eq = lavalink.Timescale()
                eq.update(speed=config["speed"], pitch=config["pitch"], rate=config["rate"])
            else:
                # Convert speed string to float (remove 'x' and convert)
                speed_value = float(speed.replace("x", ""))
                eq = lavalink.Timescale()
                eq.update(speed=speed_value, pitch=speed_value, rate=1.0)

            await player.set_filter(eq)
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.equalizer} Applied **Timescale** ({speed}) equalizer."),
                )
            )
            await ctx.respond(view=view)

    @eq.command(name="tremolo")
    @option("intensity", description="Tremolo intensity", choices=["Subtle", "Medium", "Strong"], required=False)
    async def tremolo(
        self,
        ctx: discord.ApplicationContext,
        intensity: str = "Medium",
    ):
        """Apply volume trembling effect."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Subtle": {"frequency": 1.5, "depth": 0.3},
                "Medium": {"frequency": 2.0, "depth": 0.5},
                "Strong": {"frequency": 3.0, "depth": 0.7},
            }
            config = presets[intensity]
            eq = lavalink.Tremolo()
            eq.update(frequency=config["frequency"], depth=config["depth"])
            await player.set_filter(eq)
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.equalizer} Applied **Tremolo** ({intensity}) equalizer."),
                )
            )
            await ctx.respond(view=view)

    @eq.command(name="vibrato")
    @option("intensity", description="Vibrato intensity", choices=["Light", "Medium", "Heavy"], required=False)
    async def vibrato(
        self,
        ctx: discord.ApplicationContext,
        intensity: str = "Medium",
    ):
        """Apply pitch wobbling effect."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            presets = {
                "Light": {"frequency": 1.5, "depth": 0.3},
                "Medium": {"frequency": 2.0, "depth": 0.5},
                "Heavy": {"frequency": 3.5, "depth": 0.8},
            }
            config = presets[intensity]
            eq = lavalink.Vibrato()
            eq.update(frequency=config["frequency"], depth=config["depth"])
            await player.set_filter(eq)
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.equalizer} Applied **Vibrato** ({intensity}) equalizer."),
                )
            )
            await ctx.respond(view=view)

    @eq.command(name="rotation")
    @option("speed", description="8D rotation speed", choices=["Slow", "Medium", "Fast"], required=False)
    async def rotation(
        self,
        ctx: discord.ApplicationContext,
        speed: str = "Medium",
    ):
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
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.equalizer} Applied **Rotation** ({speed}) equalizer."),
                )
            )
            await ctx.respond(view=view)

    @eq.command(name="lowpass")
    @option("strength", description="Low-pass filter strength", choices=["Light", "Medium", "Heavy"], required=False)
    async def lowpass(
        self,
        ctx: discord.ApplicationContext,
        strength: str = "Medium",
    ):
        """Apply muffled/underwater sound effect."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            # Presets for low-pass filter strengths
            presets = {
                "Light": 5.0,
                "Medium": 20.0,
                "Heavy": 50.0,
            }
            smoothing = presets[strength]
            eq = lavalink.LowPass()
            eq.update(smoothing=smoothing)
            await player.set_filter(eq)
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.equalizer} Applied **Lowpass** ({strength}) equalizer."),
                )
            )
            await ctx.respond(view=view)

    @eq.command(name="channelmix")
    @option(
        "mode",
        description="Channel mixing mode",
        choices=["Mono", "Left Only", "Right Only", "Swap", "Wide Stereo"],
        required=False,
    )
    async def channelmix(
        self,
        ctx: discord.ApplicationContext,
        mode: str = "Mono",
    ):
        """Mix audio channels for different stereo effects."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            # Presets for different channel mixing modes
            presets = {
                "Mono": {"left_to_left": 0.5, "left_to_right": 0.5, "right_to_left": 0.5, "right_to_right": 0.5},
                "Left Only": {"left_to_left": 1.0, "left_to_right": 1.0, "right_to_left": 0.0, "right_to_right": 0.0},
                "Right Only": {"left_to_left": 0.0, "left_to_right": 0.0, "right_to_left": 1.0, "right_to_right": 1.0},
                "Swap": {"left_to_left": 0.0, "left_to_right": 1.0, "right_to_left": 1.0, "right_to_right": 0.0},
                "Wide Stereo": {"left_to_left": 1.0, "left_to_right": 0.3, "right_to_left": 0.3, "right_to_right": 1.0},
            }
            config = presets[mode]
            eq = lavalink.ChannelMix()
            eq.update(
                left_to_left=config["left_to_left"],
                left_to_right=config["left_to_right"],
                right_to_left=config["right_to_left"],
                right_to_right=config["right_to_right"],
            )
            await player.set_filter(eq)
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.equalizer} Applied **Channel Mix** ({mode}) equalizer."),
                )
            )
            await ctx.respond(view=view)

    @eq.command(name="distortion")
    @option(
        "type",
        description="Distortion type",
        choices=["Light Crunch", "Heavy Metal", "Vintage", "Digital Clip"],
        required=False,
    )
    async def distortion(
        self,
        ctx: discord.ApplicationContext,
        type: str = "Light Crunch",
    ):
        """Apply audio distortion effects."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            # Presets for different distortion types
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
            config = presets[type]
            eq = lavalink.Distortion()
            eq.update(
                sin_offset=config["sin_offset"],
                sin_scale=config["sin_scale"],
                cos_offset=config["cos_offset"],
                cos_scale=config["cos_scale"],
                tan_offset=config["tan_offset"],
                tan_scale=config["tan_scale"],
                offset=config["offset"],
                scale=config["scale"],
            )
            await player.set_filter(eq)
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.equalizer} Applied **Distortion** ({type}) equalizer."),
                )
            )
            await ctx.respond(view=view)

    # Stop
    @slash_command(name="stop")
    async def stop(self, ctx: discord.ApplicationContext):
        """Destroys the player."""
        await ctx.defer()
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            disable = Disable(self.client, ctx.guild.id)
            await disable.play_msg()
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.stop} Player destroyed."),
                )
            )
            await ctx.respond(view=view)
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
                view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.seek} Moved track to `{lavalink.format_time(track_time)}`."),
                    )
                )
                await ctx.respond(view=view)
            else:
                await self.skip(ctx=ctx)

    # Skip
    @slash_command(name="skip")
    async def skip(self, ctx: discord.ApplicationContext):
        """Skips the current playing track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            view = DesignerView(
                Container(
                    TextDisplay(f"{emoji.skip} Skipped the track."),
                )
            )
            await Disable(self.client, ctx.guild.id).play_msg()
            await player.skip()
            await ctx.respond(view=view)

    # Skip to
    @slash_command(name="skip-to")
    @option("track", description="Enter your track index number to skip", autocomplete=track_autocomplete)
    async def skip_to(self, ctx: discord.ApplicationContext, track: str):
        """Skips to a given track in the queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await ctx.defer()
            index: int = int(track.split(".")[0])  # Extract index from the selected track
            if index < 1 or index > len(player.queue):
                err_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Track number must be between `1` and `{len(player.queue)}`"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=err_view, ephemeral=True)
            else:
                player.queue = player.queue[index - 1 :]
                shuffle_state = player.shuffle
                player.set_shuffle(False)  # Disable shuffle to ensure the skip works correctly
                await player.skip()
                player.set_shuffle(shuffle_state)  # Restore shuffle state
                skip_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.skip} Skipped to track `{index}`."),
                    )
                )
                await ctx.respond(view=skip_view)

    # Pause
    @slash_command(name="pause")
    async def pause(self, ctx: discord.ApplicationContext):
        """Pauses the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                err_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Player is already paused."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=err_view, ephemeral=True)
            else:
                await ctx.defer()
                await player.set_pause(True)
                await update_play_msg(self.client, ctx.guild.id)
                view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.pause} Player paused."),
                    )
                )
                await ctx.respond(view=view)

    # Resume
    @slash_command(name="resume")
    async def resume(self, ctx: discord.ApplicationContext):
        """Resumes the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                await ctx.defer()
                await player.set_pause(False)
                await update_play_msg(self.client, ctx.guild.id)
                resume_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.play} Player resumed."),
                    )
                )
                await ctx.respond(view=resume_view)
            else:
                error_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Player is not paused"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=error_view, ephemeral=True)

    # Volume
    @slash_command(name="volume")
    @option("volume", description="Enter your volume amount from 1 - 100")
    async def volume(self, ctx: discord.ApplicationContext, volume: int):
        """Changes the player's volume 1 - 100."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            volume_condition = [volume < 1, volume > 100]
            if any(volume_condition):
                error_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Volume amount must be between `1` - `100`"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=error_view, ephemeral=True)
            else:
                await player.set_volume(volume)
                vol_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.volume} Volume changed to `{player.volume}%`."),
                    )
                )
                await ctx.respond(view=vol_view)

    # Queue
    @slash_command(name="queue")
    @option("page", description="Enter queue page number", default=1, required=False)
    async def queue(self, ctx: discord.ApplicationContext, page: int = 1):
        """Shows the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if not player.queue:
                error_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Queue is empty"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=error_view, ephemeral=True)
                return
            items_per_page = 5
            pages = max(1, math.ceil(len(player.queue) / items_per_page))
            if page > pages or page < 1:
                error_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Page has to be between `1` to `{pages}`"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=error_view, ephemeral=True)
                return
            if pages > 1:
                queue_view = QueueListView(client=self.client, ctx=ctx, page=page)
                await ctx.respond(view=queue_view)
            else:
                queue_view = QueueListView(client=self.client, ctx=ctx, page=1)
                await ctx.respond(view=queue_view)

    # Clear queue
    @slash_command(name="clear-queue")
    async def clear_queue(self, ctx: discord.ApplicationContext):
        """Clears the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if not player.queue:
                error_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Queue is empty"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=error_view, ephemeral=True)
            else:
                player.queue.clear()
                clear_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.success} Cleared the queue."),
                        color=config.color.green,
                    )
                )
                await ctx.respond(view=clear_view)

    # Shuffle
    @slash_command(name="shuffle")
    async def shuffle(self, ctx: discord.ApplicationContext):
        """Shuffles the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if not player.queue:
                error_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Queue is empty"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=error_view, ephemeral=True)
            else:
                await ctx.defer()
                player.set_shuffle(not player.shuffle)
                await update_play_msg(self.client, ctx.guild.id)
                shuffle_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.shuffle} {'Enabled' if player.shuffle else 'Disabled'} shuffle."),
                    )
                )
                await ctx.respond(view=shuffle_view)

    # Loop
    @slash_command(name="loop")
    @option("mode", description="Enter loop mode", choices=["Disable", "Queue", "Track"])
    async def loop(self, ctx: discord.ApplicationContext, mode: str):
        """Loops the current queue until the command is invoked again or until a new track is enqueued."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await ctx.defer()
            _emoji = ""
            if mode == "Disable":
                player.set_loop(0)
                _emoji = emoji.loop_white
            elif mode == "Track":
                player.set_loop(1)
                _emoji = emoji.loop_one
            elif mode == "Queue":
                if not player.queue:
                    error_view = DesignerView(
                        Container(
                            TextDisplay(f"{emoji.error} Queue is empty."),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=error_view, ephemeral=True)
                    return
                else:
                    player.set_loop(2)
                    _emoji = emoji.loop
            await update_play_msg(self.client, ctx.guild.id)
            loop_view = DesignerView(
                Container(
                    TextDisplay(
                        f"{_emoji} {'Enabled' if mode != 'Disable' else 'Disabled'} {mode if mode != 'Disable' else ''} Loop."
                    ),
                )
            )
            await ctx.respond(view=loop_view)

    # Remove
    @slash_command(name="remove")
    @option("track", description="Select the track to remove", autocomplete=track_autocomplete)
    async def remove(self, ctx: discord.ApplicationContext, track: str):
        """Removes a track from the player's queue with the given index."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            index: int = int(track.split(".")[0])  # Extract index from the selected track
            if not player.queue:
                error_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Queue is empty"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=error_view, ephemeral=True)
            elif index > len(player.queue) or index < 1:
                error_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.error} Index has to be between `1` to `{len(player.queue)}`"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=error_view, ephemeral=True)
            else:
                removed = player.queue.pop(index - 1)
                remove_view = DesignerView(
                    Container(
                        TextDisplay(f"{emoji.leave} Removed **{removed.title}**."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=remove_view)


def setup(client: Client):
    client.add_cog(Music(client))
