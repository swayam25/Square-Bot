import asyncio
import datetime
import discord
import lavalink
from babel.dates import format_timedelta
from core import Client
from core.view import DesignerView
from discord import ui
from music import recommend, store
from music.utils import music_interaction_check, music_log, reply, sources, to_log_text
from utils import config
from utils.emoji import emoji

# Per-guild asyncio locks - prevents concurrent render_player executions for the same guild.
_render_locks: dict[int, asyncio.Lock] = {}


def _get_render_lock(guild_id: int) -> asyncio.Lock:
    """
    Returns the render lock for a guild, creating it on first access.

    Parameters:
        guild_id (int): The guild ID to retrieve the lock for.

    Returns:
        asyncio.Lock: The lock associated with the guild.
    """
    if guild_id not in _render_locks:
        _render_locks[guild_id] = asyncio.Lock()
    return _render_locks[guild_id]


async def render_player(client: Client, guild_id: int, *, force_new: bool = False) -> None:
    """
    Renders the single persistent player message.

    Edits the player in place while it is still the latest message, otherwise deletes the stale player and posts a fresh one at the bottom of the channel.
    Skips silently if a render is already in progress for this guild.

    Parameters:
        client (Client): The Discord bot client.
        guild_id (int): The guild to render the player for.
        force_new (bool): Always send a new player message instead of editing.
    """
    lock = _get_render_lock(guild_id)
    if lock.locked():
        return
    player: lavalink.DefaultPlayer = client.lavalink.player_manager.get(guild_id)
    if not player or not player.is_connected or not player.current:
        return
    channel = store.play_ch(guild_id)
    if not channel:
        return
    async with lock:
        view = MusicView(client, guild_id)
        play_msg, _ = store.play_msg(guild_id)
        if play_msg and not force_new:
            try:
                await play_msg.edit(view=view)
                store.play_msg(guild_id, play_msg, view, "set")
                return
            except discord.NotFound:
                pass
        # Send new and delete old concurrently - both API calls happen in parallel
        coros: list = [channel.send(view=view)]
        if play_msg:
            coros.append(play_msg.delete())
        results = await asyncio.gather(*coros, return_exceptions=True)
        new_msg = results[0]
        if isinstance(new_msg, discord.Forbidden):
            store.play_msg(guild_id, mode="clear")
            return
        if isinstance(new_msg, BaseException):
            return
        store.play_msg(guild_id, new_msg, view, "set")


def cleanup_guild(guild_id: int) -> None:
    """Releases all per-guild in-memory state: render lock and recommendation lock."""
    _render_locks.pop(guild_id, None)
    recommend.cleanup(guild_id)


async def clear_player(guild_id: int) -> None:
    """
    Deletes the persistent player message and clears its store entry.

    Parameters:
        guild_id (int): The guild whose player message should be removed.
    """
    play_msg, _ = store.play_msg(guild_id)
    if play_msg:
        try:
            await play_msg.delete()
        except discord.HTTPException:
            pass
    store.flush_store(guild_id)
    cleanup_guild(guild_id)


async def stop_player(player: lavalink.DefaultPlayer, guild: discord.Guild) -> None:
    """
    Stops playback, clears the VC status, disconnects from voice, and deletes the player card.

    Parameters:
        player (DefaultPlayer): The active Lavalink player to stop.
        guild (Guild): The guild to disconnect from.
    """
    await player.stop()
    if guild.me.voice and guild.me.voice.channel:
        await guild.me.voice.channel.set_status(status=None)
    if guild.voice_client:
        await guild.voice_client.disconnect(force=True)
    await clear_player(guild.id)


async def slash_log(
    ctx: discord.ApplicationContext,
    content: str,
    *,
    color: int | None = None,
    render: bool = True,
) -> None:
    """
    Acknowledges a state-changing slash command ephemerally and logs it publicly.

    Sends an ephemeral confirmation to the invoker, optionally re-renders the player card, and posts a public log line with the user mention prepended.

    Parameters:
        ctx (ApplicationContext): The slash command context.
        content (str): The confirmation/log message (leading emoji is stripped for the log line).
        color (int | None): Optional accent color applied to both the reply and the log.
        render (bool): Whether to re-render the player card after the action.
    """
    await reply(ctx, content, color=color)
    if render:
        await render_player(ctx.bot, ctx.guild.id)
    await music_log(ctx.bot, ctx.guild.id, f"{ctx.author.mention} {to_log_text(content)}", color=color)


class MusicContainer(ui.Container):
    """
    Renders the currently playing track as a Discord container component.

    Displays the track title (linked), artist, requester mention, and duration.
    Duration shows as a human-readable string for normal tracks, or a LIVE badge for streams.

    Parameters:
        player (DefaultPlayer): The active Lavalink player with a current track set.
    """

    def __init__(self, player: lavalink.DefaultPlayer):
        super().__init__()
        requester = f"<@{player.current.requester}>"
        if player.current.stream:
            duration = f"{emoji.live} LIVE"
        else:
            duration = datetime.timedelta(milliseconds=player.current.duration)
            duration = format_timedelta(duration, locale="en")
        self.items = [
            ui.Section(
                ui.TextDisplay(f"## [{player.current.title}]({player.current.uri})"),
                ui.TextDisplay(
                    f"{emoji.user} **Requested By**: {requester if requester else 'Unknown'}\n"
                    f"{emoji.mic} **Artist**: {sources.get(player.current.source_name, sources['_'])['emoji']} {player.current.author}\n"
                    f"{emoji.duration} **Duration**: {duration}"
                ),
                accessory=ui.Thumbnail(url=player.current.artwork_url),
            )
        ]


class MusicView(DesignerView):
    """
    Persistent now-playing card with playback control buttons.

    Displays a `MusicContainer` and two action rows: the first with pause/resume, stop, skip, loop cycle, and shuffle toggle; the second with an autoplay toggle.
    The view has no timeout and re-checks interaction eligibility on every button press.

    Parameters:
        client (Client): The bot client used to fetch the player and send follow-up logs.
        guild_id (int): The guild this player card belongs to.
    """

    def __init__(self, client: Client, guild_id: int):
        super().__init__(timeout=None)
        self.client = client
        self.guild_id = guild_id
        self.player: lavalink.DefaultPlayer = client.lavalink.player_manager.get(guild_id)
        self.interaction_check = lambda interaction: music_interaction_check(
            player=self.player, interaction=interaction, view=self
        )
        self.build()

    def build(self):
        self.clear_items()
        self.add_item(MusicContainer(self.player))
        self.add_item(row := ui.ActionRow())
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
            btn = ui.Button(emoji=btn_emoji, custom_id=action, style=discord.ButtonStyle.grey)
            btn.callback = getattr(self, f"{action}_callback")
            row.add_item(btn)
        autoplay_on = store.autoplay(self.guild_id)
        autoplay_btn = ui.Button(emoji=emoji.autoplay if autoplay_on else emoji.autoplay_white, custom_id="autoplay")
        autoplay_btn.callback = self.autoplay_callback
        self.add_item(ui.ActionRow(autoplay_btn))

    async def pause_callback(self, interaction: discord.Interaction):
        await self.player.set_pause(not self.player.paused)
        await interaction.response.defer()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            self.client,
            interaction.guild_id,
            f"{interaction.user.mention} {'paused' if self.player.paused else 'resumed'} the player.",
        )

    async def stop_callback(self, interaction: discord.Interaction):
        guild: discord.Guild = self.client.get_guild(int(interaction.guild_id))
        await interaction.response.defer()
        await music_log(self.client, interaction.guild_id, f"{interaction.user.mention} destroyed the player.")
        await stop_player(self.player, guild)

    async def skip_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.player.skip()
        await music_log(self.client, interaction.guild_id, f"{interaction.user.mention} skipped the track.")

    async def loop_callback(self, interaction: discord.Interaction):
        if self.player.loop == self.player.LOOP_NONE:
            self.player.set_loop(1)
            mode = "Track"
        elif self.player.loop == self.player.LOOP_SINGLE and self.player.queue:
            self.player.set_loop(2)
            mode = "Queue"
        else:
            self.player.set_loop(0)
            mode = "Disable"
        await interaction.response.defer()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            self.client,
            interaction.guild_id,
            f"{interaction.user.mention} {'enabled' if mode != 'Disable' else 'disabled'} {mode} loop.",
        )

    async def shuffle_callback(self, interaction: discord.Interaction):
        if not self.player.queue:
            await reply(interaction, f"{emoji.error} Queue is empty.", color=config.color.red)
            return
        self.player.set_shuffle(not self.player.shuffle)
        await interaction.response.defer()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            self.client,
            interaction.guild_id,
            f"{interaction.user.mention} {'enabled' if self.player.shuffle else 'disabled'} shuffle.",
        )

    async def autoplay_callback(self, interaction: discord.Interaction):
        enabled = store.autoplay(interaction.guild_id)
        store.autoplay(interaction.guild_id, not enabled, "set")
        await interaction.response.defer()
        await render_player(self.client, interaction.guild_id)
        await music_log(
            self.client,
            interaction.guild_id,
            f"{interaction.user.mention} {'enabled' if not enabled else 'disabled'} autoplay.",
        )
