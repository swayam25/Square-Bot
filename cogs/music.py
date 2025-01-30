import aiohttp
import discord
import asyncio
import math
import re
import lavalink
import discord.ui
import asyncio
from typing import Tuple
from utils import database as db, emoji
from discord.ext import commands, tasks
from discord.commands import slash_command, option

# Regex
url_rx = re.compile("https?:\\/\\/(?:www\\.)?.+")

# Equalizer Presets
equalizer_presets = {
    "bassboost": [(0, 0.10), (1, 0.15), (2, 0.20), (3, 0.25), (4, 0.35), (5, 0.45), (6, 0.50), (7, 0.55)],
    "jazz": [(0, 0.18), (1, 0.16), (2, 0.12), (3, 0.09), (4, 0.08), (5, 0.08), (6, 0.12), (7, 0.18)],
    "pop": [(0, 0.18), (1, 0.14), (2, 0.10), (3, 0.08), (4, 0.06), (5, 0.06), (6, 0.10), (7, 0.18)],
    "treble": [(0, 0.55), (1, 0.50), (2, 0.40), (3, 0.30), (4, 0.20), (5, 0.10), (6, 0.05), (7, 0.02)],
    "nightcore": [(0, 0.30), (1, 0.30), (2, 0.30), (3, 0.30), (4, 0.30), (5, 0.30), (6, 0.30), (7, 0.30)],
    "superbass": [(0, 0.20), (1, 0.30), (2, 0.40), (3, 0.50), (4, 0.60), (5, 0.70), (6, 0.80), (7, 0.90)]
}

class LavalinkVoiceClient(discord.VoiceProtocol):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.connect_event = asyncio.Event()

    async def on_voice_server_update(self, data):
        lavalink_data = {
                "t": "VOICE_SERVER_UPDATE",
                "d": data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        lavalink_data = {
                "t": "VOICE_STATE_UPDATE",
                "d": data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

# Connect
    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        await self.channel.guild.change_voice_state(channel=self.channel)
        try:
            self.lavalink: lavalink.Client = self.client.lavalink
        except AttributeError:
            self.client.lavalink = self.lavalink = lavalink.Client(self.client.user.id)
            self.client.lavalink.add_node(
                    db.lavalink(key="host"),
                    db.lavalink(key="port"),
                    db.lavalink(key="pass"),
                    "us",
                    "default-node")

# Disconnect
    async def disconnect(self, *, force: bool) -> None:
        await self.channel.guild.change_voice_state(channel=None)
        player: lavalink.DefaultPlayer = self.lavalink.player_manager.get(self.channel.guild.id)
        if player:
            player.channel_id = False
            await player.stop()
        self.cleanup()

class SpotifyAudioTrack(lavalink.DeferredAudioTrack):
    async def load(self, client: discord.Client):
        result: lavalink.LoadResult = await client.get_tracks(
            f"ytsearch:{self.title} {self.author}"
        )
        if result.load_type != lavalink.LoadType.SEARCH or not result.tracks:
            raise lavalink.LoadError
        first_track = result.tracks[0]
        base64 = first_track.track
        self.track = base64
        return base64

class SpotifySource(lavalink.Source):
    def __init__(self, url: str, requester: int):
        self.url = url
        self.requester = requester
        super().__init__(name="spotify")

# Spotify source
    async def get(self):
        token = ""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://open.spotify.com/get_access_token?reason=transport&productType=web_player") as resp:
                res = await resp.json()
                token = res['accessToken']
        if "playlist" in self.url:
            pl_id = self.url.split("/playlist/")[1]
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.spotify.com/v1/playlists/{pl_id}", headers={"Authorization": f"Bearer {token}"}) as resp:
                    res = await resp.json()
                    return res
        elif "album" in self.url:
            al_id = self.url.split("/album/")[1]
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.spotify.com/v1/albums/{al_id}", headers={"Authorization": f"Bearer {token}"}) as resp:
                    res = await resp.json()
                    return res
        elif "track" in self.url:
            track_id = self.url.split("/track/")[1]
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.spotify.com/v1/tracks/{track_id}", headers={"Authorization": f"Bearer {token}"}) as resp:
                    res = await resp.json()
                    return res

# Load playlist
    async def _load_pl(self) -> Tuple[list[SpotifyAudioTrack], lavalink.PlaylistInfo]:
        pl = await self.get()
        tracks = []
        for track in pl['tracks']['items']:
            tracks.append(
                SpotifyAudioTrack(
                    {
                        "identifier": track['track']['id'],
                        "isSeekable": True,
                        "author": ", ".join([artist['name'] for artist in track['track']['artists']]),
                        "length": track['track']['duration_ms'],
                        "isStream": False,
                        "title": track['track']['name'],
                        "uri": track['track']['external_urls']['spotify'],
                        "sourceName": "spotify"
                    },
                    requester=self.requester,
                    cover=track['track']['album']['images'][0]['url']
                )
            )
        pl_info = lavalink.PlaylistInfo(name=pl['name'])
        return tracks, pl_info

# Load album
    async def _load_al(self) -> Tuple[list[SpotifyAudioTrack], lavalink.PlaylistInfo]:
        al = await self.get()
        tracks = []
        for track in al['tracks']['items']:
            tracks.append(
                SpotifyAudioTrack(
                    {
                        "identifier": track['id'],
                        "isSeekable": True,
                        "author": ", ".join([artist['name'] for artist in track['artists']]),
                        "length": track['duration_ms'],
                        "isStream": False,
                        "title": track['name'],
                        "uri": track['external_urls']['spotify'],
                        "sourceName": "spotify"
                    },
                    requester=self.requester,
                    cover=track['album']['images'][0]['url']
                )
            )
        pl_info = lavalink.PlaylistInfo(name=al['name'])
        return tracks, pl_info

# Load track
    async def _load_track(self) -> SpotifyAudioTrack:
        track = await self.get()
        return SpotifyAudioTrack({
            "identifier": track['id'],
            "isSeekable": True,
            "author": ", ".join([artist['name'] for artist in track['artists']]),
            "length": track['duration_ms'],
            "isStream": False,
            "title": track['name'],
            "uri": track['external_urls']['spotify'],
            "sourceName": "spotify"
        }, requester=self.requester, cover=track['album']['images'][0]['url'])

# Load items
    async def load_item(self, client: discord.Client):
        if "playlist" in self.url:
            pl, pl_info = await self._load_pl()
            return lavalink.LoadResult(lavalink.LoadType.PLAYLIST, pl, pl_info)
        if "album" in self.url:
            al, al_info = await self._load_al()
            return lavalink.LoadResult(lavalink.LoadType.PLAYLIST, al, al_info)
        if "track" in self.url:
            track = await self._load_track()
            return lavalink.LoadResult(lavalink.LoadType.TRACK, [track], lavalink.PlaylistInfo.none())

class MusicView(discord.ui.View):
    def __init__(self, client: discord.Client, timeout: int):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client

    async def interaction_check(self, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if not player.current:
            error_em = discord.Embed(description=f"{emoji.error} Nothing is being played at the current moment", color=db.error_color)
            await interaction.response.send_message(embed=error_em, ephemeral=True)
            return False
        elif not interaction.user.voice:
            error_em = discord.Embed(description=f"{emoji.error} Join a voice channel first", color=db.error_color)
            await interaction.response.send_message(embed=error_em, ephemeral=True)
            return False
        elif player.is_connected and interaction.user.voice.channel.id != int(player.channel_id):
            error_em = discord.Embed(description=f"{emoji.error} You are not in my voice channel", color=db.error_color)
            await interaction.response.send_message(embed=error_em, ephemeral=True)
        else:
            return True

# Pause / Resume
    @discord.ui.button(emoji=f"{emoji.pause2}", custom_id="pause", style=discord.ButtonStyle.grey)
    async def pause_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if not player.paused:
            await player.set_pause(True)
        elif player.paused:
            await player.set_pause(False)
        button.emoji = emoji.play2 if player.paused else emoji.pause2
        pause_em = discord.Embed(
            title=f"{emoji.play if player.paused else emoji.pause} Player {'Paused' if player.paused else 'Resumed'}",
            description=f"{interaction.user.mention} {'Paused' if player.paused else 'Resumed'} the player",
            color=db.theme_color
        )
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=pause_em, delete_after=5)

# Stop
    @discord.ui.button(emoji=f"{emoji.stop2}", custom_id="stop", style=discord.ButtonStyle.grey)
    async def stop_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild: discord.Guild = self.client.get_guild(int(interaction.guild_id))
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(int(interaction.guild_id))
        if player:
            player.channel_id = False
            await player.stop()
        player.queue.clear()
        stop_embed = discord.Embed(
            title=f"{emoji.stop} Player Destroyed",
            description=f"{interaction.user.mention} Destroyed the player",
            color=db.theme_color
        )
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await guild.voice_client.disconnect(force=True)
        await interaction.followup.send(embed=stop_embed, delete_after=5)
        await Disable(self.client, guild.id).queue_msg()

# Skip
    @discord.ui.button(emoji=f"{emoji.skip2}", custom_id="skip", style=discord.ButtonStyle.grey)
    async def skip_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        await player.skip()
        skip_em = discord.Embed(
            title=f"{emoji.skip} Track Skipped",
            description=f"{interaction.user.mention} Skipped the track",
            color=db.theme_color
        )
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=skip_em, delete_after=5)

# Loop
    @discord.ui.button(emoji=f"{emoji.loop3}", custom_id="loop", style=discord.ButtonStyle.grey)
    async def loop_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if player.loop == player.LOOP_NONE:
            player.set_loop(1)
            button.emoji = emoji.loop2
            mode = "Track"
        elif player.loop == player.LOOP_SINGLE and player.queue:
            player.set_loop(2)
            button.emoji = emoji.loop
            mode = "Queue"
        else:
            player.set_loop(0)
            button.emoji = emoji.loop3
            mode = "OFF"
        loop_em = discord.Embed(
            title=f"{button.emoji} {mode if mode != 'OFF' else ''} Loop {'Enabled' if mode != 'OFF' else 'Disabled'}",
            description=f"Successfully {'enabled' if mode != 'OFF' else 'disabled'} {mode if mode != 'OFF' else ''} Loop",
            color=db.theme_color
        )
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=loop_em, delete_after=5)

# Shuffle
    @discord.ui.button(emoji=f"{emoji.shuffle2}", custom_id="shuffle", style=discord.ButtonStyle.grey)
    async def shuffle_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if not player.queue:
            error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=db.error_color)
            await interaction.response.send_message(embed=error_em, ephemeral=True)
        else:
            player.shuffle = not player.shuffle
            button.emoji = f"{emoji.shuffle if player.shuffle else emoji.shuffle2}"
            shuffle_em = discord.Embed(
                title=f"{button.emoji} Shuffle {'Enabled' if player.shuffle else 'Disabled'}",
                description=f"{interaction.user.mention} {'Enabled' if player.shuffle else 'Disabled'} shuffle",
                color=db.theme_color
            )
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=shuffle_em, delete_after=5)

class QueueView(discord.ui.View):
    def __init__(self, client: discord.Client, page: int, timeout: int):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client
        self.page = page
        self.items_per_page = 5

    async def interaction_check(self, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        if not player.queue:
            error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=db.error_color)
            await interaction.response.send_message(embed=error_em, ephemeral=True)
        else:
            return True

    # Start
    @discord.ui.button(emoji=f"{emoji.start}", custom_id="start", style=discord.ButtonStyle.grey)
    async def start_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page = 1
        queue_embed = await QueueEmbed(self.client, interaction, self.page).get_embed()
        await interaction.response.edit_message(embed=queue_embed, view=self)

    # Previous
    @discord.ui.button(emoji=f"{emoji.previous}", custom_id="previous", style=discord.ButtonStyle.grey)
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
    @discord.ui.button(emoji=f"{emoji.next}", custom_id="next", style=discord.ButtonStyle.grey)
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
    @discord.ui.button(emoji=f"{emoji.end}", custom_id="end", style=discord.ButtonStyle.grey)
    async def end_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(interaction.guild_id)
        pages = math.ceil(len(player.queue) / self.items_per_page)
        self.page = pages
        queue_embed = await QueueEmbed(self.client, interaction, self.page).get_embed()
        await interaction.response.edit_message(embed=queue_embed, view=self)

class QueueEmbed:
    def __init__(self, client: discord.Client, ctx: discord.ApplicationContext, page: int):
        self.client = client
        self.ctx = ctx
        self.page = page

    async def get_embed(self) -> discord.Embed:
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(self.ctx.guild_id)
        items_per_page = 5
        pages = math.ceil(len(player.queue) / items_per_page)
        start = (self.page - 1) * items_per_page
        end = start + items_per_page
        current_requester = self.ctx.guild.get_member(player.current.requester)
        queue_list = ""
        for index, track in enumerate(player.queue[start:end], start=start):
            requester = self.ctx.guild.get_member(track.requester)
            queue_list += f"`{index + 1}.` **[{track.title}]({track.uri})** [{requester.mention if requester else 'Unknown'}]\n"
        queue_em = discord.Embed(
                    title=f"{emoji.playlist} {self.ctx.guild.name}'s Queue",
                    colour=db.theme_color
                )
        queue_em.add_field(name=f"Now Playing",
                        value=f"`0.` **[{player.current.title}]({player.current.uri})** [{current_requester.mention if current_requester else 'Unknown'}]", inline=False)
        queue_em.add_field(name=f"Queued {len(player.queue)} Track(s)",
                        value=f"{queue_list}", inline=False)
        queue_em.set_footer(text=f"Viewing Page {self.page}/{pages}")
        return queue_em

class Disable:
    def __init__(self, client: discord.Client, guild_id: int):
        self.client = client
        self.guild_id = guild_id

    # Disable queue menu
    async def edit_messages_async(self, queue_view, messages) -> None:
        tasks = [msg.edit(view=queue_view) for msg in messages]
        await asyncio.gather(*tasks)

    async def queue_msg(self) -> None:
        if len(db.queue_msg(self.guild_id)) > 0:
            queue_view = QueueView(self.client, page=1, timeout=None)
            for child in queue_view.children:
                child.disabled = True
            await self.edit_messages_async(queue_view, db.queue_msg(self.guild_id))
            db.queue_msg(self.guild_id, "clear")

    # Disable play message
    async def play_msg(self) -> None:
        play_msg = db.play_msg(self.guild_id)
        music_view = MusicView(self.client, timeout=None)
        for child in music_view.children:
            child.disabled = True
        await play_msg.edit(view=music_view)

class Music(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client
        self.music.start()

# Looping music task
    @tasks.loop(seconds=0)
    async def music(self):
        await self.client.wait_until_ready()
        if not hasattr(self.client, "lavalink"):
            self.client.lavalink = lavalink.Client(self.client.user.id)
            self.client.lavalink.add_node(
                db.lavalink(key="host"),
                db.lavalink(key="port"),
                db.lavalink(key="pass"),
                "us",
                "default-node"
            )
            self.client.lavalink.add_event_hook(self.track_hook)

# Current voice
    def current_voice_channel(self, ctx: discord.ApplicationContext):
        if ctx.guild and ctx.guild.me.voice:
            return ctx.guild.me.voice.channel
        return None

# Unloading cog
    def cog_unload(self):
        self.client.lavalink._event_hooks.clear()

# Lavalink track hook event
    async def track_hook(self, event: lavalink.Event):
        if isinstance(event, lavalink.events.TrackStartEvent):
            player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(int(event.player.guild_id))
            channel = db.play_ch_id(event.player.guild_id)
            requester = f"<@{player.current.requester}>"
            if player.current.stream:
                duration = "🔴 LIVE"
            else:
                duration = lavalink.utils.format_time(player.current.duration)
            play_em = discord.Embed(
                title=f"{player.current.title}", url=f"{player.current.uri}",
                description=f"{emoji.bullet} **Requested By**: {requester if requester else 'Unknown'}\n" +
                            f"{emoji.bullet} **Duration**: `{duration}`", color=db.theme_color
            )
            if player.current.source_name == "spotify":
                play_em.set_thumbnail(url=player.current.extra['cover'])
            elif player.current.source_name == "youtube":
                play_em.set_image(url=f"https://i.ytimg.com/vi/{player.current.identifier}/maxresdefault.jpg")
            music_view = MusicView(self.client, timeout=None)
            # Loop emoji
            if player.loop == player.LOOP_NONE:
                music_view.children[3].emoji = emoji.loop3
            elif player.loop == player.LOOP_SINGLE:
                music_view.children[3].emoji = emoji.loop2
            else:
                music_view.children[3].emoji = emoji.loop
            # Shuffle emoji
            if player.shuffle:
                music_view.children[4].emoji = emoji.shuffle
            else:
                music_view.children[4].emoji = emoji.shuffle2
            # Player msg
            play_msg = await channel.send(embed=play_em, view=music_view)
            db.play_msg(event.player.guild_id, play_msg, "set")
        if isinstance(event, lavalink.events.TrackEndEvent):
            await Disable(self.client, event.player.guild_id).play_msg()
        if isinstance(event, lavalink.events.TrackStuckEvent):
            channel = db.play_ch_id(event.player.guild_id)
            error_em = discord.Embed(description=f"{emoji.error} Error while playing the track. Please try again later", color=db.error_color)
            await Disable(self.client, event.player.guild_id).play_msg()
            await channel.send(embed=error_em, delete_after=5)
        if isinstance(event, lavalink.events.TrackExceptionEvent):
            channel = db.play_ch_id(event.player.guild_id)
            error_em = discord.Embed(description=f"{emoji.error} Error while playing the track. Please try again later", color=db.error_color)
            await Disable(self.client, event.player.guild_id).play_msg()
            await channel.send(embed=error_em, delete_after=5)
        if isinstance(event, lavalink.events.QueueEndEvent):
            player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.get(int(event.player.guild_id))
            guild: discord.Guild = self.client.get_guild(int(event.player.guild_id))
            await player.clear_filters()
            await guild.voice_client.disconnect(force=True)
            await Disable(self.client, event.player.guild_id).queue_msg()

# Ensures voice parameters
    async def ensure_voice(self, ctx: discord.ApplicationContext):
        """Checks all the voice parameters."""
        player: lavalink.DefaultPlayer = None
        if not ctx.author.voice or not ctx.author.voice.channel:
            error_em = discord.Embed(description=f"{emoji.error} Join a voice channel first", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.guild.id)
            permissions = ctx.author.voice.channel.permissions_for(ctx.me)
            if ctx.command.name in ("play") and self.current_voice_channel(ctx) is None:
                if self.client.lavalink.node_manager.available_nodes:
                    voice_client = await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
                    player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.guild.id)
                    db.play_ch_id(ctx.guild.id, ctx.channel, "set")
                else:
                    self.client.lavalink.add_node(
                        db.lavalink(key="host"),
                        db.lavalink(key="port"),
                        db.lavalink(key="pass"),
                        "us",
                        "default-node")
            elif self.current_voice_channel(ctx) is not None and not self.client.lavalink.node_manager.available_nodes:
                self.client.lavalink.add_node(
                    db.lavalink(key="host"),
                    db.lavalink(key="port"),
                    db.lavalink(key="pass"),
                    "us",
                    "default-node")
            elif not permissions.connect or not permissions.speak:
                player: lavalink.DefaultPlayer = None
                error_em = discord.Embed(description=f"{emoji.error} I need the `Connect` and `Speak` permissions", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)
            elif not ctx.command.name in ("play"):
                if not player.current:
                    player: lavalink.DefaultPlayer = None
                    error_em = discord.Embed(description=f"{emoji.error} Nothing is being played at the current moment", color=db.error_color)
                    await ctx.respond(embed=error_em, ephemeral=True)
                elif ctx.author.voice.channel.id != int(player.channel_id):
                    player: lavalink.DefaultPlayer = None
                    error_em = discord.Embed(description=f"{emoji.error} You are not in my voice channel", color=db.error_color)
                    await ctx.respond(embed=error_em, ephemeral=True)
        return player

# Search autocomplete
    async def search(self, ctx: discord.ApplicationContext):
        """Searches a track from a given query."""
        player: lavalink.DefaultPlayer = self.client.lavalink.player_manager.create(ctx.interaction.guild_id)
        if ctx.value != "":
            result = await player.node.get_tracks(f"ytsearch:{ctx.value}")
            tracks = []
            for track in result['tracks']:
                track_name = ""
                if len(track['info']['title']) >= 97:
                    track_name = f"{track['info']['title'][:97]}..."
                else:
                    track_name = track['info']['title']
                tracks.append(track_name)
            return tracks
        else:
            return []

# Voice state update event
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        """Deafen yourself when joining a voice channel."""
        if member.id == member.guild.me.id and after.channel is None:
            if member.guild.voice_client:
                await member.guild.voice_client.disconnect(force=True)
        if member.id != member.guild.me.id or not after.channel:
            return
        my_perms = after.channel.permissions_for(member)
        if not after.deaf and my_perms.deafen_members:
            await member.edit(deafen=True)

# Play
    @slash_command(guild_ids=db.guild_ids(), name="play")
    @option("query", description="Enter your track name/link or playlist link", autocomplete=search)
    async def play(self, ctx: discord.ApplicationContext, query: str):
        """Searches and plays a track from a given query."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await ctx.defer()
            query = query.strip("<>")
            embed = discord.Embed(color=db.theme_color)
            # Spotify
            if "open.spotify.com" in query:
                results = await SpotifySource(query, ctx.author.id).load_item(self.client.lavalink)
                if results['loadType'] == lavalink.LoadType.PLAYLIST:
                    tracks = results['tracks']
                    for track in tracks:
                        player.add(requester=ctx.author.id, track=track)
                    embed.title = f"{emoji.playlist} Playlist Enqueued"
                    embed.description = f"**{results['playlistInfo'].name}** with `{len(tracks)}` tracks"
                elif results['loadType'] == lavalink.LoadType.TRACK:
                    track = results['tracks'][0]
                    player.add(requester=ctx.author.id, track=track)
                    embed.title = f"{emoji.music} Track Enqueued"
                    embed.description = f"**[{track.title}]({track.uri})**"
                else:
                    error_em = discord.Embed(description=f"{emoji.error} No track found from the given query", color=db.error_color)
                    await ctx.respond(embed=error_em, ephemeral=True)
                await ctx.respond(embed=embed)
            # Others
            else:
                if not url_rx.match(query):
                    if "soundcloud.com" in query:
                        query = f"scsearch:{query}"
                    elif "music.youtube.com" in query:
                        query = f"ytmsearch:{query}"
                    else:
                        query = f"ytsearch:{query}"
                results = await player.node.get_tracks(query)
                if not results or not results['tracks']:
                    error_em = discord.Embed(description=f"{emoji.error} No track found from the given query", color=db.error_color)
                    await ctx.respond(embed=error_em, ephemeral=True)
                if results['loadType'] == "PLAYLIST_LOADED":
                    tracks = results['tracks']
                    for track in tracks:
                        player.add(requester=ctx.author.id, track=track)
                    embed.title = f"{emoji.playlist} Playlist Enqueued"
                    embed.description = f"**{results['playlistInfo']['name']}** with `{len(tracks)}` tracks"
                    await ctx.respond(embed=embed)
                elif results['tracks']:
                    track = results['tracks'][0]
                    player.add(requester=ctx.author.id, track=track)
                    embed.title = f"{emoji.music} Track Enqueued"
                    embed.description = f"**[{track['info']['title']}]({track['info']['uri']})**"
                    await ctx.respond(embed=embed)
            if not player.is_playing:
                await player.play()

# Now playing
    @slash_command(guild_ids=db.guild_ids(), name="now-playing")
    async def now_playing(self, ctx: discord.ApplicationContext):
        """Shows currently playing track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            requester = ctx.guild.get_member(player.current.requester)
            if player.current.stream:
                duration = "🔴 LIVE"
            elif not player.current.stream:
                bar_length = 20
                filled_length = int(bar_length * player.position // float(player.current.duration))
                bar = emoji.filled_bar * filled_length + "" + emoji.empty_bar * (bar_length - filled_length)
                duration = lavalink.utils.format_time(player.current.duration)
            equalizer = db.equalizer(ctx.guild.id)
            loop = ""
            if player.loop == player.LOOP_NONE:
                loop = "Disabled"
            elif player.loop == player.LOOP_SINGLE:
                loop = "Track"
            elif player.loop == player.LOOP_QUEUE:
                loop = "Queue"
            play_em = discord.Embed(
                title=f"{player.current.title}", url=f"{player.current.uri}",
                description=f"{emoji.bullet} **Requested By**: {requester.mention if requester else 'Unknown'}\n" +
                            f"{emoji.bullet} **Duration**: `{duration}`\n" +
                            f"{emoji.bullet} **Volume**: `{player.volume}%`\n" +
                            f"{emoji.bullet} **Loop**: {loop}\n" +
                            f"{emoji.bullet} **Shuffle**: {'Enabled' if player.shuffle else 'Disabled'}\n" +
                            f"{emoji.bullet} **Equalizer**: `{equalizer}`\n" +
                            f"{bar}",
                color=db.theme_color
            )
            await ctx.respond(embed=play_em)

# Equalizer
    @slash_command(guild_ids=db.guild_ids(), name="equalizer")
    @option("equalizer", description="Choose your equalizer", choices=["Reset", "Bassboost", "Jazz", "Pop", "Treble", "Nightcore", "Superbass"])
    async def equalizer(self, ctx: discord.ApplicationContext, equalizer: str):
        """Equalizer to change track quality."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            _equalizer = equalizer.lower()
            if _equalizer == "reset":
                await player.clear_filters()
                eq_em = discord.Embed(
                    title=f"{emoji.equalizer} Reset Equalizer",
                    description=f"Reseted the equalizer",
                    color=db.theme_color
                )
                db.equalizer(guild_id=ctx.guild.id, name="None", mode="set")
            else:
                for eq_name, eq_gains in equalizer_presets.items():
                    if eq_name == _equalizer:
                        eq = lavalink.Equalizer()
                        eq.update(bands=eq_gains)
                        await player.set_filter(eq)
                        eq_em = discord.Embed(
                            title=f"{emoji.equalizer} Equalizer Changed",
                            description=f"Added `{equalizer}` equalizer",
                            color=db.theme_color
                        )
                        db.equalizer(guild_id=ctx.guild.id, name=equalizer, mode="set")
            await ctx.respond(embed=eq_em)

# Stop
    @slash_command(guild_ids=db.guild_ids(), name="stop")
    async def stop(self, ctx: discord.ApplicationContext):
        """Destroys the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            try:
                player.queue.clear()
                await player.stop()
                await ctx.guild.voice_client.disconnect(force=True)
            except:
                pass
            stop_embed = discord.Embed(
                title=f"{emoji.stop} Player Destroyed",
                color=db.theme_color
            )
            disable = Disable(self.client, ctx.guild.id)
            await disable.play_msg()
            await ctx.respond(embed=stop_embed)
            await disable.queue_msg()

# Seek
    @slash_command(guild_ids=db.guild_ids(), name="seek")
    @option("seconds", description="Enter track position in seconds")
    async def seek(self, ctx: discord.ApplicationContext, seconds: int):
        """Seeks to a given position in a track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            track_time = player.position + (seconds * 1000)
            if lavalink.utils.format_time(player.current.duration) > lavalink.utils.format_time(track_time):
                await player.seek(track_time)
                seek_em = discord.Embed(
                    title=f"{emoji.seek} Track Seeked",
                    description=f"Moved track to `{lavalink.utils.format_time(track_time)}`",
                    color=db.theme_color
                )
                await ctx.respond(embed=seek_em)
            elif lavalink.utils.format_time(player.current.duration) <= lavalink.utils.format_time(track_time):
                await self.skip()

# Skip
    @slash_command(guild_ids=db.guild_ids(), name="skip")
    async def skip(self, ctx: discord.ApplicationContext):
        """Skips the current playing track."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            skip_em = discord.Embed(
                title=f"{emoji.skip} Track Skipped",
                description=f"Skipped the track",
                color=db.theme_color
            )
            await Disable(self.client, ctx.guild.id).play_msg()
            await player.skip()
            await ctx.respond(embed=skip_em)

# Skip to
    @slash_command(guild_ids=db.guild_ids(), name="skip-to")
    @option("track", description="Enter your track index number to skip")
    async def skip_to(self, ctx: discord.ApplicationContext, track: int):
        """Skips to a given track in the queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            await ctx.defer()
            if track < 1 or track > len(player.queue):
                error_em = discord.Embed(description=f"{emoji.error} Track number must be between `1` and `{len(player.queue)}`", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                player.queue = player.queue[track - 1:]
                await player.skip()
                skip_em = discord.Embed(
                    title=f"{emoji.skip} Track Skipped",
                    description=f"Skipped to track `{track}`",
                    color=db.theme_color
                )
                await ctx.respond(embed=skip_em)

# Pause
    @slash_command(guild_ids=db.guild_ids(), name="pause")
    async def pause(self, ctx: discord.ApplicationContext):
        """Pauses the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                error_em = discord.Embed(description=f"{emoji.error} Player is already paused", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                await player.set_pause(True)
                pause_em = discord.Embed(
                    title=f"{emoji.pause} Player Paused",
                    description=f"Successfully paused the player",
                    color=db.theme_color
                )
                await ctx.respond(embed=pause_em)

# Resume
    @slash_command(guild_ids=db.guild_ids(), name="resume")
    async def resume(self, ctx: discord.ApplicationContext):
        """Resumes the player."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if player.paused:
                await player.set_pause(False)
                resume_em = discord.Embed(
                    title=f"{emoji.play} Player Resumed",
                    description=f"Successfully resumed the player",
                    color=db.theme_color
                )
                await ctx.respond(embed=resume_em)
            else:
                error_em = discord.Embed(description=f"{emoji.error} Player is not paused", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)

# Volume
    @slash_command(guild_ids=db.guild_ids(), name="volume")
    @option("volume", description="Enter your volume amount from 1 - 100")
    async def volume(self, ctx: discord.ApplicationContext, volume: int):
        """Changes the player's volume 1 - 100."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            volume_condition = [
                volume < 1,
                volume > 100
            ]
            if any(volume_condition):
                error_em = discord.Embed(description=f"{emoji.error} Volume amount must be between `1` - `100`", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                await player.set_volume(volume)
                vol_em = discord.Embed(
                    title=f"{emoji.volume} Volume Changed",
                    description=f"Successfully changed volume to `{player.volume}%`",
                    color=db.theme_color
                )
                await ctx.respond(embed=vol_em)

# Queue
    @slash_command(guild_ids=db.guild_ids(), name="queue")
    @option("page", description="Enter queue page number", default=1, required=False)
    async def queue(self, ctx: discord.ApplicationContext, page: int = 1):
        """Shows the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            items_per_page = 5
            pages = math.ceil(len(player.queue) / items_per_page)
            if not player.queue:
                error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)
            elif page > pages or page < 1:
                error_em = discord.Embed(description=f"{emoji.error} Page has to be between `1` to `{pages}`", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                queue_obj = QueueEmbed(self.client, ctx, page)
                queue_em = await queue_obj.get_embed()
                if pages > 1:
                    queue_view = QueueView(client=self.client, page=page, timeout=60)
                    queue_msg = await ctx.respond(embed=queue_em, view=queue_view)
                    db.queue_msg(ctx.guild.id, queue_msg, "set")
                else:
                    await ctx.respond(embed=queue_em)

# Shuffle
    @slash_command(guild_ids=db.guild_ids(), name="shuffle")
    async def shuffle(self, ctx: discord.ApplicationContext):
        """Shuffles the player's queue."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if not player.queue:
                error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)
            else:
                player.shuffle = not player.shuffle
                shuffle_em = discord.Embed(
                    title=f"{emoji.shuffle if player.shuffle else emoji.shuffle2} Shuffle {'Enabled' if player.shuffle else 'Disabled'}",
                    description=f"Successfully {'enabled' if player.shuffle else 'disabled'} shuffle",
                    color=db.theme_color
                )
                await ctx.respond(embed=shuffle_em)

# Loop
    @slash_command(guild_ids=db.guild_ids(), name="loop")
    @option("mode", description="Enter loop mode", choices=["OFF", "Queue", "Track"])
    async def loop(self, ctx: discord.ApplicationContext, mode: str):
        """Loops the current queue until the command is invoked again or until a new track is enqueued."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            _emoji = ""
            if mode == "OFF":
                player.set_loop(0)
                _emoji = emoji.loop3
            elif mode == "Track":
                player.set_loop(1)
                _emoji = emoji.loop2
            elif mode == "Queue":
                if not player.queue:
                    error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=db.error_color)
                    await ctx.respond(embed=error_em, ephemeral=True)
                    return
                else:
                    player.set_loop(2)
                    _emoji = emoji.loop
            loop_em = discord.Embed(
                title=f"{_emoji} {mode if mode != 'OFF' else ''} Loop {'Enabled' if mode != 'OFF' else 'Disabled'}",
                description=f"Successfully {'enabled' if mode != 'OFF' else 'disabled'} {mode if mode != 'OFF' else ''} Loop",
                color=db.theme_color
            )
            await ctx.respond(embed=loop_em)

# Remove
    @slash_command(guild_ids=db.guild_ids(), name="remove")
    @option("index", description="Enter your track index number")
    async def remove(self, ctx: discord.ApplicationContext, index: int):
        """Removes a track from the player's queue with the given index."""
        player: lavalink.DefaultPlayer = await self.ensure_voice(ctx)
        if player:
            if ctx.author.id == player.queue[index-1].requester:
                if not player.queue:
                    error_em = discord.Embed(description=f"{emoji.error} Queue is empty", color=db.error_color)
                    await ctx.respond(embed=error_em, ephemeral=True)
                elif index > len(player.queue) or index < 1:
                    error_em = discord.Embed(description=f"{emoji.error} Index has to be between `1` to `{len(player.queue)}`", color=db.error_color)
                    await ctx.respond(embed=error_em, ephemeral=True)
                else:
                    removed = player.queue.pop(index - 1)
                    remove_em = discord.Embed(
                        title=f"{emoji.playlist} Track Removed",
                        description=f"**{removed.title}**",
                        color=db.theme_color
                    )
                    await ctx.respond(embed=remove_em)
            else:
                error_em = discord.Embed(description=f"{emoji.error} Only requester can remove from the list", color=db.error_color)
                await ctx.respond(embed=error_em, ephemeral=True)

def setup(client: discord.Client):
    client.add_cog(Music(client))
