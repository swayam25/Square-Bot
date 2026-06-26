import discord
import lavalink
import math
from core import Client
from core.view import DesignerView
from discord import ui
from music.utils import music_interaction_check, music_log, reply
from utils import config
from utils.emoji import emoji


async def _update_queue_view(interaction: discord.Interaction, queue_view: QueueListView):
    queue_view.build()
    await interaction.response.edit_message(view=queue_view)


class QueueBtnCallback:
    """Static callbacks for per-track action buttons (expand, move up/down, remove, play now)."""

    @staticmethod
    async def queue_btn_callback(
        i: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: QueueListView
    ):
        if not player or not player.queue or track_index >= len(player.queue) or not queue_view:
            return
        queue_view.toggle_action_buttons(track_index)
        queue_view.build()
        await i.response.edit_message(view=queue_view)

    @staticmethod
    async def move_up_callback(
        interaction: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: QueueListView
    ):
        if track_index <= 0:
            return
        new_index = track_index - 1
        player.queue[track_index], player.queue[new_index] = (
            player.queue[new_index],
            player.queue[track_index],
        )
        if track_index == queue_view.visible_action_button:
            queue_view.visible_action_button = new_index
        current_page_start = (queue_view.page - 1) * queue_view.items_per_page
        if new_index < current_page_start:
            queue_view.page = (new_index // queue_view.items_per_page) + 1
        await _update_queue_view(interaction, queue_view)

    @staticmethod
    async def move_down_callback(
        interaction: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: QueueListView
    ):
        if track_index >= len(player.queue) - 1:
            return
        new_index = track_index + 1
        player.queue[track_index], player.queue[new_index] = (
            player.queue[new_index],
            player.queue[track_index],
        )
        if track_index == queue_view.visible_action_button:
            queue_view.visible_action_button = new_index
        current_page_start = (queue_view.page - 1) * queue_view.items_per_page
        current_page_end = current_page_start + queue_view.items_per_page - 1
        if new_index > current_page_end:
            queue_view.page = (new_index // queue_view.items_per_page) + 1
        await _update_queue_view(interaction, queue_view)

    @staticmethod
    async def remove_callback(
        interaction: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: QueueListView
    ):
        if track_index >= len(player.queue):
            return
        player.queue.pop(track_index)
        queue_view.visible_action_button = None
        total_pages = max(1, math.ceil(len(player.queue) / queue_view.items_per_page))
        if queue_view.page > total_pages and total_pages > 0:
            queue_view.page = total_pages
        queue_view.build()
        await interaction.response.edit_message(view=queue_view)

    @staticmethod
    async def play_now_callback(
        interaction: discord.Interaction, player: lavalink.DefaultPlayer, track_index: int, queue_view: QueueListView
    ):
        if track_index >= len(player.queue):
            return
        await player.play_track(player.queue.pop(track_index))
        total_pages = max(1, math.ceil(len(player.queue) / queue_view.items_per_page))
        if queue_view.page > total_pages and total_pages > 0:
            queue_view.page = total_pages
        await _update_queue_view(interaction, queue_view)
        await music_log(
            interaction.client,
            interaction.guild_id,
            f"{interaction.user.mention} is now playing track `{track_index + 1}` from the queue.",
        )


class QueueContainer(ui.Container):
    """
    Renders a paginated list of queued tracks as a Discord container component.

    Shows the currently playing track at position 0, followed by the queued tracks for the current page.
    Each track has an expand button to reveal move/remove/play-now actions.

    Parameters:
        player (DefaultPlayer): The active Lavalink player.
        ctx (ApplicationContext): The slash command context (used to resolve member mentions).
        page (int): The page number to display (1-indexed).
        items_per_page (int): Number of tracks shown per page.
        queue_view (QueueListView | None): The parent view, used to track which track's action buttons are expanded.
    """

    def __init__(
        self,
        player: lavalink.DefaultPlayer,
        ctx: discord.ApplicationContext,
        page=1,
        items_per_page=5,
        queue_view=None,
    ):
        super().__init__()
        pages = max(1, math.ceil(len(player.queue) / items_per_page))
        start = (page - 1) * items_per_page
        end = start + items_per_page
        queue_list: list = []

        for index, track in enumerate(player.queue[start:end], start=start):
            requester = ctx.guild.get_member(track.requester)
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
                        f"`{index + 1}.` [**{track.title}** by **{track.author}**]({track.uri}) [`{lavalink.format_time(track.duration)}`]\n"
                        f"-# {emoji.bottom_right} {requester.mention if requester else 'Unknown'}"
                    ),
                    accessory=btn,
                )
            )
            if queue_view and index == queue_view.visible_action_button:
                move_up_btn = ui.Button(emoji=emoji.up_white, style=discord.ButtonStyle.grey, disabled=(index == 0))
                move_up_btn.callback = lambda i, track_idx=index: QueueBtnCallback.move_up_callback(
                    i, player=player, track_index=track_idx, queue_view=queue_view
                )
                move_down_btn = ui.Button(
                    emoji=emoji.down_white, style=discord.ButtonStyle.grey, disabled=(index == len(player.queue) - 1)
                )
                move_down_btn.callback = lambda i, track_idx=index: QueueBtnCallback.move_down_callback(
                    i, player=player, track_index=track_idx, queue_view=queue_view
                )
                remove_btn = ui.Button(emoji=emoji.bin_white, style=discord.ButtonStyle.grey)
                remove_btn.callback = lambda i, track_idx=index: QueueBtnCallback.remove_callback(
                    i, player=player, track_index=track_idx, queue_view=queue_view
                )
                play_now_btn = ui.Button(emoji=emoji.play_white, style=discord.ButtonStyle.grey)
                play_now_btn.callback = lambda i, track_idx=index: QueueBtnCallback.play_now_callback(
                    i, player=player, track_index=track_idx, queue_view=queue_view
                )
                queue_list.append(ui.ActionRow(move_up_btn, move_down_btn, remove_btn, play_now_btn))

        current_requester = ctx.guild.get_member(player.current.requester) if player.current else None
        self.add_item(ui.TextDisplay(f"## {ctx.guild.name}'s Queue"))
        self.add_item(
            ui.TextDisplay(
                f"`0.` [**{player.current.title}** by **{player.current.author}**]({player.current.uri}) [`{lavalink.format_time(player.current.duration)}`]\n"
                f"-# {emoji.bottom_right} {current_requester.mention if current_requester else 'Unknown'}"
                if player.current
                else "No track playing."
            )
        )
        if queue_list:
            self.add_item(ui.TextDisplay(f"### Queued {len(player.queue)} Tracks"))
            self.items.extend(queue_list)
        if len(player.queue) > items_per_page:
            self.add_item(ui.Separator())
            self.add_item(ui.TextDisplay(f"-# Viewing Page {page}/{pages}"))
        elif not queue_list:
            self.add_item(ui.Separator())
            self.add_item(ui.TextDisplay("-# Queue is empty"))


class QueueListView(DesignerView):
    """
    Interactive queue view with pagination, bulk actions, and per-track controls.

    Renders a QueueContainer for the current page, a More Actions dropdown (clear, reverse, sort, deduplicate, remove by requester), and pagination buttons when the queue spans multiple pages.

    Parameters:
        client (Client): The bot client used to fetch the player.
        ctx (ApplicationContext): The slash command context passed down to QueueContainer.
        page (int): The initial page to display (1-indexed, default 1).
    """

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
        if track_index == self.visible_action_button:
            self.visible_action_button = None
        else:
            self.visible_action_button = track_index

    def build(self):
        self.clear_items()
        self.add_item(
            QueueContainer(self.player, self.ctx, page=self.page, items_per_page=self.items_per_page, queue_view=self)
        )
        if self.player.queue:
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
        else:
            await interaction.response.defer()
            self.visible_action_button = None
            if selected_value == "clear_queue":
                self.player.queue.clear()
            elif selected_value == "reverse_queue":
                self.player.queue.reverse()
            elif selected_value == "sort_by_duration":
                self.player.queue.sort(key=lambda track: track.duration)
            elif selected_value == "remove_duplicates":
                seen = set()
                original_length = len(self.player.queue)
                self.player.queue = [
                    track for track in self.player.queue if not (track.identifier in seen or seen.add(track.identifier))
                ]
                if original_length == len(self.player.queue):
                    await reply(
                        interaction, f"{emoji.error} No duplicate tracks found in the queue.", color=config.color.red
                    )
            self.build()
            await interaction.edit(view=self)

    async def requester_modal_callback(self, interaction: discord.Interaction, view_interaction: discord.Interaction):
        user_id = int(interaction.data["components"][0]["component"]["values"][0])
        original_length = len(self.player.queue)
        self.player.queue = [track for track in self.player.queue if track.requester != user_id]
        removed_count = original_length - len(self.player.queue)
        self.visible_action_button = None
        if removed_count == 0:
            await reply(
                interaction,
                f"{emoji.error} No tracks found requested by <@{user_id}> in the queue.",
                color=config.color.red,
            )
        else:
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
