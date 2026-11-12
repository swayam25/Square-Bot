import discord
import math
from discord import ui
from sonolink.models import Playable
from square.core import Client
from square.core.view import DesignerView
from square.music.core import SquarePlayer, fmt_time, get_player, requester_id
from square.music.utils import music_interaction_check, reply
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count


def history_tracks(player: SquarePlayer) -> list[Playable]:
    history = player.history
    return list(reversed(history[:])) if history else []


class HistoryContainer(ui.Container):
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
                f"### Played {fmt_count(len(tracks))} Tracks • `{fmt_time(sum(t.length for t in tracks if not t.is_stream))}`"
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
        await interaction.response.defer()
        # Local: `music/controls.py` imports this module
        from square.music import controls
        from square.music.errors import MusicError

        index = next((i for i, played in enumerate(history_tracks(self.player)) if played is track), -1)
        try:
            await reply(
                interaction, await controls.replay(interaction.guild, interaction.user, index, track.identifier)
            )
        except MusicError as exc:
            await reply(interaction, f"{emoji.error} {exc}", color=config.color.red)

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
