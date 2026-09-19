import discord
import math
from core import Client
from core.view import DesignerView
from discord import ui
from music.core import SquarePlayer, fmt_time, get_player, requester_id, tag_requester
from music.utils import music_interaction_check, music_log, reply
from sonolink.models import Playable
from utils.emoji import emoji


def history_tracks(player: SquarePlayer) -> list[Playable]:
    """Returns the played tracks newest-first, or an empty list when history is disabled."""
    history = player.history
    return list(reversed(history[:])) if history else []


class HistoryContainer(ui.Container):
    """
    Renders a page of previously played tracks as a Discord container component.

    Args:
        player (:class:`SquarePlayer`): The active player.
        source (:class:`ApplicationContext` | :class:`Interaction`): The invoking command or button press, used to resolve the guild.
        page (int): The page number to display (1-indexed).
        items_per_page (int): Number of tracks shown per page.
        history_view (:class:`HistoryListView` | None): The parent view, used to wire each track's replay button.
    """

    def __init__(
        self,
        player: SquarePlayer,
        source: discord.ApplicationContext | discord.Interaction,
        page=1,
        items_per_page=5,
        history_view=None,
    ):
        super().__init__()
        tracks = history_tracks(player)
        pages = max(1, math.ceil(len(tracks) / items_per_page))
        start = (page - 1) * items_per_page
        self.add_item(ui.TextDisplay(f"## {source.guild.name}'s History"))
        if not tracks:
            self.add_item(ui.TextDisplay("Nothing has been played yet."))
            return
        self.add_item(
            ui.TextDisplay(
                f"### Played {len(tracks)} Tracks • `{fmt_time(sum(t.length for t in tracks if not t.is_stream))}`"
            )
        )
        for index, track in enumerate(tracks[start : start + items_per_page], start=start):
            requester = source.guild.get_member(requester_id(player, track) or 0)
            btn = ui.Button(emoji=emoji.reload_white, style=discord.ButtonStyle.grey)
            btn.callback = lambda i, t=track: history_view.replay_callback(i, t)
            self.add_item(
                ui.Section(
                    ui.TextDisplay(
                        f"`{index + 1}.` [**{track.title}** by **{track.author}**]({track.uri}) [`{fmt_time(track.length)}`]\n"
                        f"-# {emoji.bottom_right} {requester.mention if requester else 'Unknown'}"
                    ),
                    accessory=btn,
                )
            )
        if len(tracks) > items_per_page:
            self.add_item(ui.Separator())
            self.add_item(ui.TextDisplay(f"-# Viewing Page {page}/{pages}"))


class HistoryListView(DesignerView):
    """
    Paginated list of previously played tracks, newest first, each with a button to queue it again.

    Args:
        client (:class:`Client`): The bot client used to fetch the player.
        source (:class:`ApplicationContext` | :class:`Interaction`): The invoking command or button press, passed down to :class:`HistoryContainer`.
        page (int): The initial page to display (1-indexed, default 1).
    """

    def __init__(self, client: Client, source: discord.ApplicationContext | discord.Interaction, page: int = 1):
        super().__init__()
        self.client = client
        self.source = source
        self.page = page
        self.items_per_page = 5
        self.player = get_player(client, source.guild.id)
        self.interaction_check = lambda interaction: music_interaction_check(
            player=self.player, interaction=interaction, view=self
        )
        self.build()

    def build(self):
        self.clear_items()
        self.add_item(
            HistoryContainer(
                self.player,
                self.source,
                page=self.page,
                items_per_page=self.items_per_page,
                history_view=self,
            )
        )
        total_pages = max(1, math.ceil(len(history_tracks(self.player)) / self.items_per_page))
        if total_pages > 1:
            self.add_item(row := ui.ActionRow())
            for btn_emoji, action in [
                (emoji.start_white, "start"),
                (emoji.previous_white, "previous"),
                (emoji.next_white, "next"),
                (emoji.end_white, "end"),
            ]:
                btn = ui.Button(emoji=btn_emoji, style=discord.ButtonStyle.grey)
                btn.callback = lambda i, action=action: self.interaction_callback(i, action=action)
                row.add_item(btn)

    async def replay_callback(self, interaction: discord.Interaction, track: Playable):
        """Queues a played track again, crediting whoever pressed replay as its requester."""
        await interaction.response.defer()
        self.player.queue.put(tag_requester(self.client, track, interaction.user.id))
        await reply(interaction, f"{emoji.reload} Queued **{track.title}** again.")
        await music_log(
            interaction.guild_id,
            f"{emoji.reload} {interaction.user.mention} queued [**{track.title}**]({track.uri}) again.",
        )

    async def interaction_callback(self, interaction: discord.Interaction, action: str):
        total_pages = max(1, math.ceil(len(history_tracks(self.player)) / self.items_per_page))
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
