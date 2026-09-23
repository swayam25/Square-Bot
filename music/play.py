import asyncio
import datetime
import discord
import math
import re
import sonolink
from babel.dates import format_timedelta
from core import Client, console
from core.view import DesignerView
from dataclasses import dataclass
from discord import ui
from music.core import SquarePlayer, fmt_time, get_player, session_lock, tag_requester
from music.player import schedule_render, stop_player
from music.utils import get_source, reply, split_log_text
from sonolink.models import Playlist
from sonolink.models.responses import SearchResult
from utils import config
from utils.emoji import emoji

REQUEST_LINGER = 1.0
PICKER_LIMIT = 10
PICKER_TIMEOUT = 60.0
PICKER_RESULT_LINGER = 3.0

url_rx = re.compile("https?:\\/\\/(?:www\\.)?.+")
# Autocomplete entries carry the track duration, which is noise once submitted.
_timestamp_rx = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b|\s*-\s*\d{1,2}:\d{2}(?::\d{2})?\b")


@dataclass(slots=True)
class Enqueued:
    """
    The outcome of resolving a query and putting it on the queue.

    Attributes:
        ok (bool): Whether anything was queued.
        content (str): A rendered, emoji-prefixed line describing the outcome, ready to show either
            as a public reply or as a self-deleting toast.
        color (int | None): The accent color the line should be shown in.
        started (bool): Whether this call started playback, meaning a track start event is inbound
            and will render the card on its own.
    """

    ok: bool
    content: str
    color: int | None = None
    started: bool = False


def clean_query(query: str) -> str:
    """Strips the angle brackets and the trailing duration an autocomplete entry carries."""
    return _timestamp_rx.sub("", query.strip("<>"))


def voice_error(member: discord.Member) -> str | None:
    """
    Says why a member can't ask for playback right now, or None when they can.

    Separate from connecting, so a request can be turned away before anything is searched for and
    long before the bot takes up a voice channel.

    Args:
        member (:class:`Member`): The member asking for playback.

    Returns:
        str | None: An emoji-prefixed error line, or None when the request may go ahead.
    """
    if not member.voice or not member.voice.channel:
        return f"{emoji.error} Join a voice channel first."
    bot_channel = member.guild.me.voice.channel if member.guild.me.voice else None
    if bot_channel is not None and member.voice.channel != bot_channel:
        return f"{emoji.error} You are not in my voice channel."
    permissions = member.voice.channel.permissions_for(member.guild.me)
    if not permissions.connect or not permissions.speak:
        return f"{emoji.error} I need the `Connect` and `Speak` permissions."
    return None


async def ensure_connected(client: Client, member: discord.Member) -> tuple[SquarePlayer | None, str | None, bool]:
    """
    Resolves the guild's player, connecting to the member's voice channel when nothing is playing yet.

    Called as late as possible, so the bot never holds a voice channel it isn't playing to and
    can't be timed out for inactivity while someone is still deciding what to queue.

    Returns strings rather than replying, so both a slash command and a typed request can render
    the outcome in their own shape. Deliberately leaves the player channel alone: where the card
    lives is the caller's business, and a bound request channel has already decided.

    Args:
        client (:class:`Client`): The Discord bot client.
        member (:class:`Member`): The member asking for playback.

    Returns:
        tuple[:class:`SquarePlayer` | None, str | None, bool]: The player, an emoji-prefixed error
        line when there isn't one, and whether this call is what connected the bot.
    """
    err = voice_error(member)
    if err:
        return None, err, False
    guild = member.guild
    async with session_lock(guild.id):
        player = get_player(client, guild.id)
        if player is not None and guild.me.voice is not None:
            return player, None, False
        if guild.voice_client:
            await guild.voice_client.disconnect(force=True)
        try:
            player = await member.voice.channel.connect(cls=SquarePlayer)
        except Exception as exc:
            # A raise here reaches a typed request with no handler, stranding it mid-reaction.
            console.print("[yellow]Voice connect failed:[/]", exc)
            return None, f"{emoji.error} I couldn't join your voice channel. Try again in a moment.", False
        return player, None, True


def is_link(query: str) -> bool:
    """Whether a query is a URL, which resolves to one thing rather than a list to choose from."""
    return bool(url_rx.match(query.strip("<>")))


def _search_nodes(client: Client) -> list[sonolink.Node]:
    """Every connected node, lowest penalty first."""
    try:
        best = client.sonolink.get_best_node()
    except RuntimeError:
        return []
    return [best, *(node for node in client.sonolink.nodes if node.is_connected and node is not best)]


async def search_tracks(
    client: Client,
    query: str,
    *,
    source: sonolink.TrackSourceType = sonolink.TrackSourceType.YOUTUBE_MUSIC,
    retry: bool = True,
) -> SearchResult | None:
    """
    Searches the nodes in turn, best first, and returns the first one that answers.

    A node fronted by a proxy answers a bad gateway with an HTML body, which sonolink feeds
    straight into ``msgspec`` while building its own ``HTTPException``. The failure therefore
    arrives as a bare ``DecodeError``, so there is no useful exception type to catch here.

    Args:
        client (:class:`Client`): The Discord bot client.
        query (str): The search query, already cleaned.
        source (:class:`sonolink.TrackSourceType`): The source to search.
        retry (bool): Whether to fall through to the remaining nodes. Autocomplete passes False:
            it runs per keystroke against a ~3s deadline, so a degraded node would spend the whole
            budget on retries and answer nothing at all.

    Returns:
        :class:`SearchResult` | None: The result, or None when no node could answer.
    """
    nodes = _search_nodes(client)
    for node in nodes if retry else nodes[:1]:
        try:
            return await node.search_track(query, source=source)
        except Exception as err:
            console.print(f"[yellow]Search failed on node[/] [cyan]{node.id}[/]:", err)
    return None


async def resolve_query(client: Client, query: str) -> tuple[object | None, str | None]:
    """
    Searches for a query and hands back whatever it resolved to, without queueing any of it.

    Args:
        client (:class:`Client`): The Discord bot client.
        query (str): The raw track name, link, or playlist link.

    Returns:
        tuple[object | None, str | None]: A playlist, a list of matches, or a single track, and an
        emoji-prefixed error line when the search came back empty or broken.
    """
    result = await search_tracks(client, clean_query(query))
    if result is None or result.is_error():
        return None, f"{emoji.error} Failed to load the track. Please try again in a moment."
    if result.is_empty() or result.result is None:
        return None, f"{emoji.error} No track found from the given query."
    return result.result, None


async def enqueue(client: Client, player: SquarePlayer, data: object, requester_id: int) -> Enqueued:
    """
    Puts a resolved search result on the queue, starting playback when nothing is going yet.

    Args:
        client (:class:`Client`): The Discord bot client.
        player (:class:`SquarePlayer`): The player to queue onto.
        data (object): A playlist, a list of matches, or a single track, from :func:`resolve_query`.
        requester_id (int): The user the queued tracks are credited to.

    Returns:
        :class:`Enqueued`: The outcome, rendered but not sent.
    """
    if isinstance(data, Playlist):
        queued = [tag_requester(client, track, requester_id) for track in data.tracks]
        src_info = get_source(queued[0].source_name)
        content = f"{src_info['emoji']} Added **{data.name}** with `{len(queued)}` tracks."
    else:
        queued = tag_requester(client, data[0] if isinstance(data, list) else data, requester_id)
        src_info = get_source(queued.source_name)
        if queued.is_stream:
            dur = f"{emoji.live} LIVE"
        else:
            dur = format_timedelta(datetime.timedelta(milliseconds=queued.length), locale="en")
        content = f"{src_info['emoji']} Added [**{queued.title}** by **{queued.author}**]({queued.uri}) [{dur}]."
    async with session_lock(player.guild.id):
        player.queue.put(queued)
        started = not player.current
        if started:
            await player.play(player.queue.get())
    return Enqueued(True, content, int(src_info["color"]), started)


async def resolve_and_enqueue(client: Client, player: SquarePlayer, query: str, requester_id: int) -> Enqueued:
    """
    Resolves a query and queues the first thing it comes back with, in one step.

    For `/play` and for links, where there is nothing to pick between.

    Args:
        client (:class:`Client`): The Discord bot client.
        player (:class:`SquarePlayer`): The player to queue onto.
        query (str): The raw track name, link, or playlist link.
        requester_id (int): The user the queued tracks are credited to.

    Returns:
        :class:`Enqueued`: The outcome, rendered but not sent.
    """
    data, err = await resolve_query(client, query)
    if err:
        return Enqueued(False, err, config.color.red)
    return await enqueue(client, player, data, requester_id)


async def mark_request(message: discord.Message, ok: bool) -> None:
    """
    Settles a request message: swaps the working reaction for the outcome, then clears it away.

    The pause before the delete is what makes the mark worth adding, otherwise the message and its
    reaction vanish in the same frame.

    Args:
        message (:class:`Message`): The request message to settle.
        ok (bool): Whether the track was queued.
    """
    for coro in (
        message.remove_reaction(emoji.loading, message.guild.me),
        message.add_reaction(emoji.success if ok else emoji.error),
    ):
        try:
            await coro
        except discord.HTTPException:
            pass
    await asyncio.sleep(REQUEST_LINGER)
    try:
        await message.delete()
    except discord.HTTPException:
        pass


class TrackPickerView(DesignerView):
    """
    Lets the author choose between the matches a typed track name came back with.

    Args:
        client (:class:`Client`): The Discord bot client.
        request_msg (:class:`Message`): The request message that opened this picker.
        tracks (list): The candidate tracks, in search order.
    """

    def __init__(self, client: Client, request_msg: discord.Message, tracks: list):
        super().__init__(timeout=PICKER_TIMEOUT, disable_on_timeout=False)
        self.client = client
        self.request_msg = request_msg
        self.tracks = tracks[:PICKER_LIMIT]
        self.page = 1
        self.items_per_page = 5
        self.msg: discord.Message | None = None
        self.build()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.request_msg.author.id:
            await reply(interaction, f"{emoji.error} That isn't your request.", color=config.color.red)
            return False
        return True

    @property
    def pages(self) -> int:
        return max(1, math.ceil(len(self.tracks) / self.items_per_page))

    def build(self) -> None:
        self.clear_items()
        start = (self.page - 1) * self.items_per_page
        container = ui.Container(
            ui.TextDisplay("## Which one?"),
            ui.TextDisplay(
                f"-# {self.request_msg.author.mention} searched for "
                f"`{discord.utils.escape_markdown(self.request_msg.content.strip())[:80]}`"
            ),
        )
        for index, track in enumerate(self.tracks[start : start + self.items_per_page], start=start):
            btn = ui.Button(emoji=emoji.play_white, style=discord.ButtonStyle.grey)
            btn.callback = lambda i, track_index=index: self.pick_callback(i, track_index)
            container.add_item(
                ui.Section(
                    ui.TextDisplay(
                        f"`{index + 1}.` [**{track.title}** by **{track.author}**]({track.uri}) "
                        f"[`{fmt_time(track.length)}`]"
                    ),
                    accessory=btn,
                )
            )
        if self.pages > 1:
            container.add_item(ui.Separator())
            container.add_item(ui.TextDisplay(f"-# Viewing Page {self.page}/{self.pages}"))
        self.add_item(container)
        single = self.pages <= 1
        self.add_item(row := ui.ActionRow())
        for btn_emoji, action in (
            (emoji.start_white, "start"),
            (emoji.previous_white, "previous"),
            (emoji.bin_white, "cancel"),
            (emoji.next_white, "next"),
            (emoji.end_white, "end"),
        ):
            btn = ui.Button(
                emoji=btn_emoji,
                style=discord.ButtonStyle.grey,
                disabled=single and action != "cancel",
            )
            btn.callback = self.cancel_callback if action == "cancel" else lambda i, a=action: self.page_callback(i, a)
            row.add_item(btn)

    async def page_callback(self, interaction: discord.Interaction, action: str) -> None:
        if action == "start":
            self.page = 1
        elif action == "previous":
            self.page = self.pages if self.page <= 1 else self.page - 1
        elif action == "next":
            self.page = 1 if self.page >= self.pages else self.page + 1
        elif action == "end":
            self.page = self.pages
        self.build()
        await interaction.edit(view=self)

    async def settle(self, content: str, color: int | None) -> None:
        """Shows the outcome in place of the list, then takes the picker away."""
        self.stop()
        self.clear_items()
        self.add_item(ui.Container(ui.TextDisplay(content), color=color))
        if self.msg:
            try:
                await self.msg.edit(view=self)
                await self.msg.delete(delay=PICKER_RESULT_LINGER)
            except discord.HTTPException:
                pass
            self.msg = None

    async def pick_callback(self, interaction: discord.Interaction, track_index: int) -> None:
        await interaction.response.defer()
        # Resolved now rather than held from when the picker opened: the bot may have been
        # disconnected, stopped or moved while the list sat there, leaving that player dead.
        player, err, connected_now = await ensure_connected(self.client, interaction.user)
        if err:
            err_emoji, err_text = split_log_text(err)
            await self.settle(f"{err_emoji} {interaction.user.mention} {err_text}".strip(), config.color.red)
            return
        try:
            result = await enqueue(self.client, player, self.tracks[track_index], interaction.user.id)
        except Exception:
            if connected_now:
                await stop_player(player, interaction.guild)
            raise
        await self.settle(result.content.replace("Added", f"{interaction.user.mention} added", 1), result.color)
        if result.ok and not result.started:
            schedule_render(self.client, self.request_msg.guild.id)

    async def cancel_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await self.settle(f"{emoji.error} {interaction.user.mention} cancelled the request.", config.color.red)

    async def on_timeout(self) -> None:
        await self.settle(
            f"{emoji.error} {self.request_msg.author.mention} didn't pick a track in time.", config.color.red
        )
