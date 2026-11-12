import discord
import math
from collections.abc import Awaitable
from discord import ui
from itertools import islice
from square.core import Client
from square.core.view import DesignerView
from square.music import controls, request
from square.music.core import SquarePlayer, fmt_time, get_player, requester_id
from square.music.errors import MusicError
from square.music.utils import music_interaction_check, reply
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count

_AUTOPLAY_SHOWN = 10


async def _update_queue_view(interaction: discord.Interaction, queue_view: QueueListView):
    queue_view.build()
    await interaction.response.edit_message(view=queue_view)


def nudge_card(player: SquarePlayer, guild_id: int) -> None:
    from square.music.player import schedule_render  # Local: `music/player.py` imports this module.

    if request.setup_mode(guild_id):
        schedule_render(player.client, guild_id)


class QueueBtnCallback:
    @staticmethod
    async def queue_btn_callback(
        i: discord.Interaction, player: SquarePlayer, track_index: int, queue_view: QueueListView
    ):
        if not player or not len(player.queue) or track_index >= len(player.queue) or not queue_view:
            return
        queue_view.toggle_action_buttons(track_index)
        queue_view.build()
        await i.response.edit_message(view=queue_view)

    @staticmethod
    async def _run(interaction: discord.Interaction, action: Awaitable[str]) -> bool:
        try:
            await action
        except MusicError as exc:
            await reply(interaction, f"{emoji.error} {exc}", color=config.color.red)
            return False
        return True

    @staticmethod
    async def move_up_callback(
        interaction: discord.Interaction,
        player: SquarePlayer,
        track_index: int,
        identifier: str,
        queue_view: QueueListView,
    ):
        if track_index <= 0:
            return
        new_index = track_index - 1
        if not await QueueBtnCallback._run(
            interaction, controls.move(interaction.guild, interaction.user, track_index, new_index, identifier)
        ):
            return
        if track_index == queue_view.visible_action_button:
            queue_view.visible_action_button = new_index
        current_page_start = (queue_view.page - 1) * queue_view.items_per_page
        if new_index < current_page_start:
            queue_view.page = (new_index // queue_view.items_per_page) + 1
        await _update_queue_view(interaction, queue_view)

    @staticmethod
    async def move_down_callback(
        interaction: discord.Interaction,
        player: SquarePlayer,
        track_index: int,
        identifier: str,
        queue_view: QueueListView,
    ):
        if track_index >= len(player.queue) - 1:
            return
        new_index = track_index + 1
        if not await QueueBtnCallback._run(
            interaction, controls.move(interaction.guild, interaction.user, track_index, new_index, identifier)
        ):
            return
        if track_index == queue_view.visible_action_button:
            queue_view.visible_action_button = new_index
        current_page_start = (queue_view.page - 1) * queue_view.items_per_page
        current_page_end = current_page_start + queue_view.items_per_page - 1
        if new_index > current_page_end:
            queue_view.page = (new_index // queue_view.items_per_page) + 1
        await _update_queue_view(interaction, queue_view)

    @staticmethod
    async def remove_callback(
        interaction: discord.Interaction,
        player: SquarePlayer,
        track_index: int,
        identifier: str,
        queue_view: QueueListView,
    ):
        if track_index >= len(player.queue):
            return
        if not await QueueBtnCallback._run(
            interaction, controls.remove(interaction.guild, interaction.user, track_index, identifier)
        ):
            return
        queue_view.visible_action_button = None
        total_pages = max(1, math.ceil(len(player.queue) / queue_view.items_per_page))
        if queue_view.page > total_pages and total_pages > 0:
            queue_view.page = total_pages
        queue_view.build()
        await interaction.response.edit_message(view=queue_view)

    @staticmethod
    async def play_now_callback(
        interaction: discord.Interaction,
        player: SquarePlayer,
        track_index: int,
        identifier: str,
        queue_view: QueueListView,
    ):
        if track_index >= len(player.queue):
            return
        if not await QueueBtnCallback._run(
            interaction, controls.jump(interaction.guild, interaction.user, track_index, identifier)
        ):
            return
        total_pages = max(1, math.ceil(len(player.queue) / queue_view.items_per_page))
        if queue_view.page > total_pages and total_pages > 0:
            queue_view.page = total_pages
        await _update_queue_view(interaction, queue_view)


class QueueContainer(ui.Container):
    def __init__(
        self,
        player: SquarePlayer,
        source: discord.ApplicationContext | discord.Interaction,
        page=1,
        items_per_page=5,
        queue_view=None,
        autoplay_enabled: bool = False,
    ):
        super().__init__()
        autoplay_tracks = player.queue.autoplay_tracks
        total = len(player.queue)
        pages = max(1, math.ceil(total / items_per_page))
        start = (page - 1) * items_per_page
        end = start + items_per_page
        queue_list: list = []

        # islice over the live queue: `queue.tracks` would copy all of it to render one page.
        for index, track in enumerate(islice(player.queue, start, end), start=start):
            requester = source.guild.get_member(requester_id(player, track) or 0)
            btn = ui.Button(
                emoji=emoji.more if queue_view and index == queue_view.visible_action_button else emoji.more_white,
                style=discord.ButtonStyle.grey,
            )
            btn.callback = lambda i, track_idx=index: QueueBtnCallback.queue_btn_callback(
                i, player=player, track_index=track_idx, queue_view=queue_view
            )
            queue_list.append(
                ui.Section(
                    ui.TextDisplay(
                        f"`{index + 1}.` [**{track.title}** by **{track.author}**]({track.uri}) [`{fmt_time(track.length)}`]\n"
                        f"-# {emoji.bottom_right} {requester.mention if requester else 'Unknown'}"
                    ),
                    accessory=btn,
                )
            )
            if queue_view and index == queue_view.visible_action_button:
                move_up_btn = ui.Button(emoji=emoji.up_white, style=discord.ButtonStyle.grey, disabled=(index == 0))
                move_up_btn.callback = lambda i, track_idx=index, ident=track.identifier: (
                    QueueBtnCallback.move_up_callback(
                        i, player=player, track_index=track_idx, identifier=ident, queue_view=queue_view
                    )
                )
                move_down_btn = ui.Button(
                    emoji=emoji.down_white, style=discord.ButtonStyle.grey, disabled=(index == total - 1)
                )
                move_down_btn.callback = lambda i, track_idx=index, ident=track.identifier: (
                    QueueBtnCallback.move_down_callback(
                        i, player=player, track_index=track_idx, identifier=ident, queue_view=queue_view
                    )
                )
                remove_btn = ui.Button(emoji=emoji.bin_white, style=discord.ButtonStyle.grey)
                remove_btn.callback = lambda i, track_idx=index, ident=track.identifier: (
                    QueueBtnCallback.remove_callback(
                        i, player=player, track_index=track_idx, identifier=ident, queue_view=queue_view
                    )
                )
                play_now_btn = ui.Button(emoji=emoji.play_white, style=discord.ButtonStyle.grey)
                play_now_btn.callback = lambda i, track_idx=index, ident=track.identifier: (
                    QueueBtnCallback.play_now_callback(
                        i, player=player, track_index=track_idx, identifier=ident, queue_view=queue_view
                    )
                )
                queue_list.append(ui.ActionRow(move_up_btn, move_down_btn, remove_btn, play_now_btn))

        current = player.current
        current_requester = source.guild.get_member(requester_id(player, current) or 0) if current else None
        self.add_item(ui.TextDisplay(f"## {source.guild.name}'s Queue"))
        self.add_item(
            ui.TextDisplay(
                f"`0.` [**{current.title}** by **{current.author}**]({current.uri}) [`{fmt_time(current.length)}`]\n"
                f"-# {emoji.bottom_right} {current_requester.mention if current_requester else 'Unknown'}"
                if current
                else "No track playing."
            )
        )
        if queue_list:
            # duration_until ignores loop mode, unlike total_duration, which reports inf while looping.
            runtime = fmt_time(player.queue.duration_until(total))
            self.add_item(ui.TextDisplay(f"### Queued {fmt_count(total)} Tracks • `{runtime}`"))
            self.items.extend(queue_list)
        if total > items_per_page:
            self.add_item(ui.Separator())
            self.add_item(ui.TextDisplay(f"-# Viewing Page {page}/{pages}"))
        if autoplay_enabled:
            self.add_item(ui.Separator())
            if autoplay_tracks and page == pages:
                self.add_item(ui.TextDisplay(f"### {emoji.autoplay} Up Next • AutoPlay"))
                self.add_item(
                    ui.TextDisplay(
                        "\n".join(
                            f"`{idx + 1}.` [**{track.title}** by **{track.author}**]({track.uri}) "
                            f"[`{fmt_time(track.length)}`]"
                            for idx, track in enumerate(islice(autoplay_tracks, _AUTOPLAY_SHOWN))
                        )
                    )
                )
                if (more := len(autoplay_tracks) - _AUTOPLAY_SHOWN) > 0:
                    self.add_item(ui.TextDisplay(f"-# And {fmt_count(more)} more."))
            else:
                self.add_item(
                    ui.TextDisplay(
                        f"-# {emoji.autoplay} **Autoplay Enabled**\n"
                        f"-# Related tracks will be added automatically when the queue ends."
                    )
                )


class QueueListView(DesignerView):
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
        self.visible_action_button: int | None = None
        self.build()

    def toggle_action_buttons(self, track_index: int):
        if track_index == self.visible_action_button:
            self.visible_action_button = None
        else:
            self.visible_action_button = track_index

    def build(self):
        self.clear_items()
        autoplay_enabled = self.player.autoplay_on
        self.add_item(
            QueueContainer(
                self.player,
                self.source,
                page=self.page,
                items_per_page=self.items_per_page,
                queue_view=self,
                autoplay_enabled=autoplay_enabled,
            )
        )
        if len(self.player.queue):
            self.add_item(
                ui.ActionRow(
                    more_select := ui.Select(
                        placeholder="More Actions",
                        options=[
                            discord.SelectOption(label="Clear Queue", emoji=emoji.bin_white, value="clear_queue"),
                            discord.SelectOption(
                                label="Reverse Queue", emoji=emoji.reload_white, value="reverse_queue"
                            ),
                            discord.SelectOption(
                                label="Sort by Duration", emoji=emoji.duration_white, value="sort_by_duration"
                            ),
                            discord.SelectOption(
                                label="Remove Duplicates", emoji=emoji.copy_white, value="remove_duplicates"
                            ),
                            discord.SelectOption(
                                label="Remove songs by requester", emoji=emoji.user_white, value="remove_by_requester"
                            ),
                        ],
                        custom_id="more_actions",
                    )
                )
            )
            more_select.callback = lambda i: self.more_select_callback(i)
        total_pages = max(1, math.ceil(len(self.player.queue) / self.items_per_page))
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

    async def more_select_callback(self, interaction: discord.Interaction):
        selected_value = interaction.data["values"][0]
        if selected_value == "remove_by_requester":
            await interaction.response.send_modal(
                modal := ui.DesignerModal(
                    ui.Label(
                        "Select requester to remove their songs",
                        item=ui.Select(
                            discord.ComponentType.user_select, placeholder="Select a user", custom_id="requester_select"
                        ),
                    ),
                    title="Remove Songs by Requester",
                )
            )
            modal.callback = lambda i: self.requester_modal_callback(i, interaction)
            return
        await interaction.response.defer()
        action = {
            "clear_queue": controls.clear_queue,
            "reverse_queue": controls.reverse_queue,
            "sort_by_duration": controls.sort_queue,
            "remove_duplicates": controls.dedupe_queue,
        }[selected_value]
        if await QueueBtnCallback._run(interaction, action(interaction.guild, interaction.user)):
            self.visible_action_button = None
            self.build()
            await interaction.edit(view=self)

    async def requester_modal_callback(self, interaction: discord.Interaction, view_interaction: discord.Interaction):
        user_id = int(interaction.data["components"][0]["component"]["values"][0])
        if await QueueBtnCallback._run(
            interaction, controls.remove_requested_by(interaction.guild, interaction.user, user_id)
        ):
            await interaction.response.defer()
            self.visible_action_button = None
            self.build()
            await view_interaction.edit(view=self)

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
