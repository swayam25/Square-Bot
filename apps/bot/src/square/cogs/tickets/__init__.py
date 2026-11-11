import asyncio
import discord
from collections.abc import Awaitable, Callable
from contextlib import suppress
from discord import ui
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from square.cogs.tickets import actions, cards, panel
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, modal, show_loading, success_view
from square.db import cache
from square.db.funcs.tickets import fetch_ticket
from square.db.schema import TicketTable
from square.music.utils import delete_quietly
from square.utils.emoji import emoji

# Buttons on ticket channels made before v2, which have no database row
LEGACY_IDS = {"ticket_close", "ticket_transcript"}


class Tickets(Cog, name="Tickets", description="Need help? Open a ticket and ask.", emoji=emoji.ticket, order=7):
    def __init__(self, client: Client):
        self.client = client
        self._adopting: asyncio.Task | None = None
        self._busy: set[int] = set()  # Ticket channels with a slow press still running

    ticket = SlashCommandGroup(name="ticket", description="Ticket commands.")

    async def _context(
        self, interaction: discord.Interaction
    ) -> tuple[discord.Guild, discord.Member, discord.TextChannel, TicketTable] | None:
        """The ticket the interaction happened in. Replies and returns None outside a ticket."""
        guild, member, channel = interaction.guild, interaction.user, interaction.channel
        if guild and isinstance(member, discord.Member) and isinstance(channel, discord.TextChannel):
            if ticket := await fetch_ticket(channel.id):
                return guild, member, channel, ticket
        await self._reply(interaction, error_view("This isn't a ticket channel."))
        return None

    @staticmethod
    def _with_file(file: discord.File) -> tuple[DesignerView, discord.File]:
        return cards.transcript_reply(file.filename or "transcript.html"), file

    @staticmethod
    async def _reply(interaction: discord.Interaction, view: DesignerView, file: discord.File | None = None) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(view=view, file=file or discord.utils.MISSING, ephemeral=True)
        else:
            # Unlike followup.send, send_message rejects MISSING and wants None for "no file"
            await interaction.response.send_message(view=view, file=file, ephemeral=True)

    async def _with_loading(
        self,
        interaction: discord.Interaction,
        pressed: Callable[[], ui.DesignerView],
        label: str,
        work: Callable[[], Awaitable[object]],
    ) -> None:
        """
        Runs a slow press with its button loading, and puts the message back if the work fails.

        These views aren't kept between presses and staff share the card, so the guard is per channel.

        Args:
            interaction (:class:`Interaction`): The press.
            pressed (Callable): Draws the pressed message as it was.
            label (str): The button's status text.
            work (Callable): The action. It leaves the message in its final state.
        """
        channel_id = interaction.channel_id or 0
        if channel_id in self._busy:
            await interaction.response.defer()
            return
        self._busy.add(channel_id)
        try:
            await show_loading(pressed(), interaction, label)
            await work()
        except Exception:
            with suppress(discord.HTTPException):
                await interaction.edit_original_response(view=pressed())
            raise
        finally:
            self._busy.discard(channel_id)

    # Panel

    @commands.Cog.listener()
    async def on_ready(self):
        if self._adopting and not self._adopting.done():
            return  # A resume re-fires this, and two sweeps would each repost
        self._adopting = self.client.loop.create_task(panel.adopt_all(self.client))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or not isinstance(message.channel, discord.TextChannel):
            return
        # Checked by author, not panel ID: a fresh panel's own event can land before its ID is saved, and would loop
        if message.author.id != message.guild.me.id:
            if panel.is_panel_channel(message.guild.id, message.channel.id):
                panel.stick(message.channel)
        # Discord's "pinned a message" line under a new ticket's card. Pins staff make keep theirs.
        elif message.type is discord.MessageType.pins_add and await fetch_ticket(message.channel.id):
            await delete_quietly(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.guild_id:
            await panel.repost_if_deleted(self.client, payload.guild_id, {payload.message_id})

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if payload.guild_id:
            await panel.repost_if_deleted(self.client, payload.guild_id, payload.message_ids)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if panel.is_panel_channel(channel.guild.id, channel.id):
            await panel.unbind(channel.guild.id)

    # Buttons

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type is not discord.InteractionType.component:
            return
        custom_id = str((interaction.data or {}).get("custom_id", ""))
        if custom_id in LEGACY_IDS:
            await self._legacy(interaction, custom_id)
        elif custom_id == "ticket:open":
            await self._open_from_panel(interaction)
        elif custom_id.startswith("ticket:") and (context := await self._context(interaction)):
            await self._button(interaction, custom_id.removeprefix("ticket:"), *context)

    async def _button(
        self,
        interaction: discord.Interaction,
        action: str,
        guild: discord.Guild,
        member: discord.Member,
        channel: discord.TextChannel,
        ticket: TicketTable,
    ) -> None:
        support = actions.is_support(member)

        def card() -> DesignerView:
            return cards.controls(ticket, guild)

        def confirm_close() -> DesignerView:
            return cards.confirm("close", f"Close ticket {cards.label(ticket)}?")

        def confirm_delete() -> DesignerView:
            return cards.confirm("delete", f"Delete ticket {cards.label(ticket)} and its channel?")

        if action in ("close", "confirm-close"):
            if not support and member.id != ticket.opener_id:
                await self._reply(interaction, error_view("Only staff or the opener can close this ticket."))
            elif ticket.status != "open":
                await self._reply(interaction, error_view("This ticket is already closed."))
            elif action == "close" and cache.get(guild.id).ticket_confirm_close:
                await self._reply(interaction, confirm_close())
            elif action == "close":
                await self._with_loading(
                    interaction, card, "Closing...", lambda: actions.close(self.client, guild, ticket, channel, member)
                )
            else:

                async def close_confirmed() -> None:
                    await actions.close(self.client, guild, ticket, channel, member)
                    await interaction.edit_original_response(view=success_view(f"Closed ticket {cards.label(ticket)}."))

                await self._with_loading(interaction, confirm_close, "Closing...", close_confirmed)
            return
        if action == "transcript":
            if not support and member.id != ticket.opener_id:
                await self._reply(interaction, error_view("Only staff or the opener can get the transcript."))
                return
            if ticket.status == "open":
                await self._reply(interaction, error_view("Close the ticket first to get its transcript."))
                return

            async def send_transcript() -> None:
                await self._reply(interaction, *self._with_file(await actions.transcript(guild, channel, ticket)))
                await interaction.edit_original_response(view=card())

            await self._with_loading(interaction, card, "Generating...", send_transcript)
            return
        if not support:
            await self._reply(interaction, error_view("Only staff can do that."))
            return
        match action:
            case "claim" if ticket.status != "open":
                await self._reply(interaction, error_view("Closed tickets can't be claimed or unclaimed."))
            case "claim" if ticket.claimed_by == member.id:
                await self._with_loading(
                    interaction, card, "Unclaiming...", lambda: actions.unclaim(self.client, guild, ticket)
                )
            case "claim":
                await self._with_loading(
                    interaction, card, "Claiming...", lambda: actions.claim(self.client, guild, ticket, member)
                )
            case "add" | "remove" if ticket.status != "open":
                await self._reply(interaction, error_view("Reopen the ticket first to add or remove members."))
            case "add" | "remove":
                await self._member_modal(interaction, action, ticket, channel, member)
            case "reopen":
                await self._with_loading(
                    interaction, card, "Reopening...", lambda: actions.reopen(self.client, guild, ticket, channel)
                )
            case "delete":
                await self._reply(interaction, confirm_delete())
            case "confirm-delete":
                await self._with_loading(
                    interaction,
                    confirm_delete,
                    "Deleting...",
                    lambda: actions.delete(self.client, guild, ticket, channel, member),
                )

    async def _member_modal(
        self,
        interaction: discord.Interaction,
        action: str,
        ticket: TicketTable,
        channel: discord.TextChannel,
        by: discord.Member,
    ) -> None:
        picker = ui.Select(discord.ComponentType.user_select, min_values=1, max_values=5)

        async def submit(submitted: discord.Interaction) -> None:
            members = [user for user in picker.values or [] if isinstance(user, discord.Member)]
            run = actions.add_members if action == "add" else actions.remove_members
            result = await run(ticket, channel, members, by)
            await submitted.response.send_message(view=success_view(result))

        verb = "Add to" if action == "add" else "Remove from"
        await interaction.response.send_modal(
            modal(f"{verb} ticket {cards.label(ticket)}", ui.Label("Members", picker), on_submit=submit)
        )

    async def _open_from_panel(self, interaction: discord.Interaction) -> None:
        reason = ui.InputText(style=discord.InputTextStyle.long, max_length=500, required=False)

        async def submit(submitted: discord.Interaction) -> None:
            if not submitted.guild or not isinstance(submitted.user, discord.Member):
                return
            await submitted.response.defer(ephemeral=True)
            result = await actions.open_ticket(
                self.client, submitted.guild, submitted.user, (reason.value or "").strip() or "No reason provided"
            )
            view = error_view(result) if isinstance(result, str) else success_view(f"Opened {result.mention}.")
            await submitted.followup.send(view=view, ephemeral=True)

        label = ui.Label("Reason", reason, description="What do you need help with?")
        await interaction.response.send_modal(modal("Open a ticket", label, on_submit=submit))

    async def _legacy(self, interaction: discord.Interaction, custom_id: str) -> None:
        guild, member, channel, message = interaction.guild, interaction.user, interaction.channel, interaction.message
        if not (guild and message and isinstance(member, discord.Member) and isinstance(channel, discord.TextChannel)):
            return
        if not member.guild_permissions.manage_channels:
            await self._reply(interaction, error_view("You need `Manage Channels` to use this."))
            return

        def card() -> ui.DesignerView:
            view = ui.DesignerView.from_message(message, timeout=None)
            view._store = False  # from_message has no option for it, and the listener handles these buttons
            return view

        async def send_transcript() -> None:
            await self._reply(interaction, *self._with_file(await actions.transcript(guild, channel, None)))
            await interaction.edit_original_response(view=card())

        if custom_id == "ticket_transcript":
            await self._with_loading(interaction, card, "Generating...", send_transcript)
        else:
            await self._with_loading(
                interaction, card, "Closing...", lambda: actions.close_legacy(self.client, guild, channel, member)
            )

    # Commands

    @ticket.command(name="create")
    @option("reason", description="What do you need help with?", required=False)
    async def create_ticket(self, ctx: discord.ApplicationContext, reason: str = "No reason provided"):
        """Opens a ticket."""
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return
        if not cache.get(ctx.guild.id).ticket_cmds:
            await ctx.respond(
                view=error_view("Ticket commands are turned off. Use the ticket panel instead."), ephemeral=True
            )
            return
        await ctx.defer(ephemeral=True)
        result = await actions.open_ticket(self.client, ctx.guild, ctx.author, reason)
        view = error_view(result) if isinstance(result, str) else success_view(f"Opened {result.mention}.")
        await ctx.respond(view=view, ephemeral=True)

    async def _ticket_here(
        self, ctx: discord.ApplicationContext, *, staff: bool, closed: str | None = None, still_open: str | None = None
    ) -> tuple[discord.Guild, discord.Member, discord.TextChannel, TicketTable] | None:
        """
        The ticket this command runs in, checking who may use it. Replies and returns None when refused.

        Args:
            ctx (:class:`ApplicationContext`): The command.
            staff (bool): Only staff may use it. Otherwise the opener can too.
            closed (str | None): Refuses an open ticket with this message.
            still_open (str | None): Refuses a closed ticket with this message.
        """
        guild, member, channel = ctx.guild, ctx.author, ctx.channel
        ticket = await fetch_ticket(channel.id) if isinstance(channel, discord.TextChannel) else None
        if not (guild and isinstance(member, discord.Member) and isinstance(channel, discord.TextChannel) and ticket):
            await ctx.respond(view=error_view("This isn't a ticket channel."), ephemeral=True)
            return None
        if not actions.is_support(member) and (staff or member.id != ticket.opener_id):
            await ctx.respond(view=error_view("You can't do that in this ticket."), ephemeral=True)
            return None
        refusal = closed if ticket.status == "open" else still_open
        if refusal:
            await ctx.respond(view=error_view(refusal), ephemeral=True)
            return None
        return guild, member, channel, ticket

    @ticket.command(name="close")
    async def close_ticket(self, ctx: discord.ApplicationContext):
        """Closes this ticket and saves its transcript."""
        if not (found := await self._ticket_here(ctx, staff=False, still_open="This ticket is already closed.")):
            return
        guild, member, channel, ticket = found
        await ctx.defer(ephemeral=True)
        await actions.close(self.client, guild, ticket, channel, member)
        await ctx.respond(view=success_view(f"Closed ticket {cards.label(ticket)}."), ephemeral=True)

    @ticket.command(name="reopen")
    async def reopen_ticket(self, ctx: discord.ApplicationContext):
        """Reopens this closed ticket."""
        if not (found := await self._ticket_here(ctx, staff=True, closed="This ticket is already open.")):
            return
        guild, _, channel, ticket = found
        await ctx.defer(ephemeral=True)
        await actions.reopen(self.client, guild, ticket, channel)
        await ctx.respond(view=success_view(f"Reopened ticket {cards.label(ticket)}."), ephemeral=True)

    @ticket.command(name="delete")
    async def delete_ticket(self, ctx: discord.ApplicationContext):
        """Deletes this closed ticket and its channel."""
        if found := await self._ticket_here(ctx, staff=True, closed="Close the ticket before deleting it."):
            ticket = found[3]
            await ctx.respond(
                view=cards.confirm("delete", f"Delete ticket {cards.label(ticket)} and its channel?"), ephemeral=True
            )

    @ticket.command(name="claim")
    async def claim_ticket(self, ctx: discord.ApplicationContext):
        """Claims this ticket, taking it over if someone else has."""
        if not (found := await self._ticket_here(ctx, staff=True, still_open="Closed tickets can't be claimed.")):
            return
        guild, member, _, ticket = found
        if ticket.claimed_by == member.id:
            await ctx.respond(view=error_view("You've already claimed this ticket."), ephemeral=True)
            return
        await ctx.respond(view=success_view(await actions.claim(self.client, guild, ticket, member)), ephemeral=True)

    @ticket.command(name="unclaim")
    async def unclaim_ticket(self, ctx: discord.ApplicationContext):
        """Releases your claim on this ticket."""
        if not (found := await self._ticket_here(ctx, staff=True, still_open="Closed tickets can't be unclaimed.")):
            return
        guild, member, _, ticket = found
        if ticket.claimed_by is None:
            await ctx.respond(view=error_view("Nobody has claimed this ticket."), ephemeral=True)
        elif ticket.claimed_by != member.id and not member.guild_permissions.manage_channels:
            await ctx.respond(
                view=error_view(f"Only <@{ticket.claimed_by}> or an admin can unclaim this ticket."), ephemeral=True
            )
        else:
            await ctx.respond(view=success_view(await actions.unclaim(self.client, guild, ticket)), ephemeral=True)

    @ticket.command(name="add")
    @option("member", description="Who to add to this ticket.")
    async def add_to_ticket(self, ctx: discord.ApplicationContext, member: discord.Member):
        """Adds a member to this ticket."""
        if found := await self._ticket_here(ctx, staff=True, still_open="Reopen the ticket first to add members."):
            _, by, channel, ticket = found
            await ctx.respond(view=success_view(await actions.add_members(ticket, channel, [member], by)))

    @ticket.command(name="remove")
    @option("member", description="Who to remove from this ticket.")
    async def remove_from_ticket(self, ctx: discord.ApplicationContext, member: discord.Member):
        """Removes a member from this ticket."""
        if found := await self._ticket_here(ctx, staff=True, still_open="Reopen the ticket first to remove members."):
            _, by, channel, ticket = found
            await ctx.respond(view=success_view(await actions.remove_members(ticket, channel, [member], by)))

    @ticket.command(name="transcript")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def transcript_ticket(self, ctx: discord.ApplicationContext):
        """Gets this closed ticket's transcript as a file."""
        if found := await self._ticket_here(ctx, staff=False, closed="Close the ticket first to get its transcript."):
            guild, _, channel, ticket = found
            await ctx.defer(ephemeral=True)
            view, file = self._with_file(await actions.transcript(guild, channel, ticket))
            await ctx.respond(view=view, file=file, ephemeral=True)


def setup(client: Client):
    client.add_cog(Tickets(client))
