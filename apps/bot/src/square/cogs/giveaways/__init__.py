import asyncio
import discord
from datetime import timedelta
from discord import ui
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from square.cogs.giveaways import actions, cards, files
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView, error_view, success_view
from square.db import cache
from square.db.funcs import giveaways as giveaways_db
from square.db.schema import GiveawayTable
from square.modules import Module, ModuleOff
from square.utils import config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_count, parse_duration

MAX_DURATION = "52w"
MAX_WINNERS = 50
_CHOICES = 25
_STATUS = {"scheduled": "Scheduled", "running": "Running", "ended": "Ended"}


def can_post(channel: discord.abc.GuildChannel) -> str | None:
    perms = channel.permissions_for(channel.guild.me)
    if not (perms.view_channel and perms.send_messages):
        return f"I can't send messages in {channel.mention}."
    return None


class Giveaways(
    Cog,
    name="Giveaways",
    description="Host giveaways that pick fair winners on time.",
    emoji=emoji.giveaway,
    order=9,
    module=Module.GIVEAWAYS,
):
    def __init__(self, client: Client):
        self.client = client
        self._scheduler: asyncio.Task | None = None

    giveaway = SlashCommandGroup(
        name="giveaway",
        description="Giveaway commands.",
        default_member_permissions=discord.Permissions(manage_guild=True),
    )

    @staticmethod
    async def _reply(interaction: discord.Interaction, view: DesignerView) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._scheduler and not self._scheduler.done():
            return  # A resume re-fires this
        self._scheduler = self.client.loop.create_task(actions.schedule(self.client))
        self.client.loop.create_task(actions.redraw_running(self.client))

    def cog_unload(self):
        if self._scheduler:
            self._scheduler.cancel()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        await self._message_gone(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        for message_id in payload.message_ids:
            await self._message_gone(message_id)

    @staticmethod
    async def _message_gone(message_id: int) -> None:
        if not (giveaway := await giveaways_db.fetch_by_message(message_id)):
            return
        if giveaway.status == "ended":
            await giveaways_db.save_giveaway(giveaway, message_id=None)
        else:
            await giveaways_db.delete_giveaway(giveaway)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        for giveaway_id in await giveaways_db.forget_channel(channel.id):
            await files.drop(channel.guild.id, giveaway_id)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type is not discord.InteractionType.component:
            return
        custom_id = str((interaction.data or {}).get("custom_id", ""))
        if not custom_id.startswith("giveaway:"):
            return
        guild, member = interaction.guild, interaction.user
        if not guild or not isinstance(member, discord.Member):
            return
        if not cache.enabled(guild.id, Module.GIVEAWAYS):
            await self._reply(interaction, error_view(str(ModuleOff(Module.GIVEAWAYS))))
        elif custom_id == "giveaway:enter":
            await self._enter(interaction, member)
        elif custom_id.startswith("giveaway:leave:"):
            await self._leave(interaction, member, custom_id.removeprefix("giveaway:leave:"))
        elif custom_id.startswith("giveaway:delete:"):
            await self._delete_confirmed(interaction, member, custom_id.removeprefix("giveaway:delete:"))

    async def _enter(self, interaction: discord.Interaction, member: discord.Member) -> None:
        giveaway = await giveaways_db.fetch_by_message(interaction.message.id) if interaction.message else None
        if not giveaway or giveaway.status != "running" or giveaway.ends_at <= actions.now():
            await self._reply(interaction, error_view("This giveaway has ended."))
            return
        if member.bot:
            await self._reply(interaction, error_view("Bots can't enter giveaways."))
            return
        totals = await actions.invite_totals(giveaway, member.guild.id, [member.id])
        reason = actions.refusal(giveaway, member, totals.get(member.id, 0))
        # Someone already in can always leave, even after they stop meeting the requirements
        if await giveaways_db.fetch_entry(giveaway.id, member.id):
            await interaction.response.send_message(view=cards.leave_card(giveaway, reason), ephemeral=True)
            return
        if reason:
            await self._reply(interaction, error_view(reason))
            return
        if not await giveaways_db.enter(giveaway.id, member.id):
            await interaction.response.send_message(view=cards.leave_card(giveaway), ephemeral=True)
            return
        actions.recount(self.client, giveaway.id)
        entries = actions.weight(giveaway, member, 0)
        extra = f" You have `{entries}` entries." if entries > 1 else ""
        await self._reply(interaction, success_view(f"You entered **{giveaway.prize}**.{extra} Good luck!"))

    async def _leave(self, interaction: discord.Interaction, member: discord.Member, raw_id: str) -> None:
        giveaway = await giveaways_db.fetch_giveaway_by_id(int(raw_id)) if raw_id.isdigit() else None
        if not giveaway or giveaway.status != "running":
            await interaction.response.edit_message(view=error_view("This giveaway has ended."))
            return
        if await giveaways_db.leave(giveaway.id, [member.id]):
            actions.recount(self.client, giveaway.id)
        await interaction.response.edit_message(view=success_view(f"You left **{giveaway.prize}**."))

    async def _delete_confirmed(self, interaction: discord.Interaction, member: discord.Member, raw_id: str) -> None:
        if not member.guild_permissions.manage_guild:
            await self._reply(interaction, error_view("You need `Manage Server` to delete giveaways."))
            return
        giveaway = await giveaways_db.fetch_giveaway(member.guild.id, int(raw_id)) if raw_id.isdigit() else None
        if not giveaway:
            await interaction.response.edit_message(view=error_view("That giveaway is already gone."))
            return
        await actions.remove(self.client, giveaway)
        await interaction.response.edit_message(view=success_view(f"Deleted **{giveaway.prize}**."))

    async def _autocomplete(self, ctx: discord.AutocompleteContext, statuses: tuple[str, ...]):
        if not ctx.interaction.guild_id:
            return []
        found = await giveaways_db.search_giveaways(ctx.interaction.guild_id, statuses, ctx.value.strip(), _CHOICES)
        return [
            discord.OptionChoice(name=f"{giveaway.prize[:80]} · {_STATUS[giveaway.status]}", value=str(giveaway.id))
            for giveaway in found
        ]

    async def running_choices(self, ctx: discord.AutocompleteContext):
        return await self._autocomplete(ctx, ("running",))

    async def ended_choices(self, ctx: discord.AutocompleteContext):
        return await self._autocomplete(ctx, ("ended",))

    async def any_choices(self, ctx: discord.AutocompleteContext):
        return await self._autocomplete(ctx, giveaways_db.STATUSES)

    async def _pick(self, ctx: discord.ApplicationContext, value: str) -> GiveawayTable | None:
        assert ctx.guild is not None
        giveaway = await giveaways_db.fetch_giveaway(ctx.guild.id, int(value)) if value.isdigit() else None
        if giveaway is None:
            found = await giveaways_db.search_giveaways(ctx.guild.id, giveaways_db.STATUSES, value.strip(), 1)
            giveaway = await giveaways_db.fetch_giveaway(ctx.guild.id, found[0].id) if found else None
        if giveaway is None:
            await ctx.respond(view=error_view("I couldn't find that giveaway."), ephemeral=True)
        return giveaway

    @giveaway.command(name="start")
    @option("prize", description="What the winners get.", max_length=256)
    @option("duration", description="How long it runs, like 1d 12h. Use m, w, d, h, min and s.")
    @option("winners", description="How many people win.", min_value=1, max_value=MAX_WINNERS, default=1)
    @option("channel", description="Where to post it. Defaults to this channel.", default=None)
    @option("description", description="A few words about the prize.", max_length=1000, default=None)
    async def start_giveaway(
        self,
        ctx: discord.ApplicationContext,
        prize: str,
        duration: str,
        winners: int,
        channel: discord.TextChannel | None,
        description: str | None,
    ):
        """Starts a giveaway. The dashboard has every other option."""
        assert ctx.guild is not None
        target = channel or ctx.channel
        if not isinstance(target, discord.TextChannel):
            await ctx.respond(view=error_view("Pick a text channel to post the giveaway in."), ephemeral=True)
            return
        try:
            length = parse_duration(duration, MAX_DURATION)
        except ValueError as exc:
            await ctx.respond(view=error_view(str(exc)), ephemeral=True)
            return
        if length < timedelta(seconds=10):
            await ctx.respond(view=error_view("A giveaway needs to run for at least `10s`."), ephemeral=True)
            return
        if problem := can_post(target):
            await ctx.respond(view=error_view(problem), ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        started = actions.now()
        giveaway = await giveaways_db.create_giveaway(
            ctx.guild.id,
            status="running",
            channel_id=target.id,
            host_id=ctx.author.id,
            prize=prize.strip(),
            description=(description or "").strip(),
            winner_count=winners,
            starts_at=started,
            ends_at=started + length,
        )
        giveaway = await giveaways_db.fetch_giveaway(ctx.guild.id, giveaway.id)
        assert giveaway is not None
        if not await actions.post(self.client, giveaway):
            await ctx.respond(view=error_view(f"I couldn't post the giveaway in {target.mention}."), ephemeral=True)
            return
        view = success_view(f"Started **{giveaway.prize}** in {target.mention}.")
        view.add_item(
            ui.ActionRow(
                ui.Button(
                    label="Go to giveaway",
                    style=discord.ButtonStyle.link,
                    url=f"https://discord.com/channels/{ctx.guild.id}/{target.id}/{giveaway.message_id}",
                ),
                ui.Button(
                    label="Customize",
                    emoji=emoji.settings_white,
                    style=discord.ButtonStyle.link,
                    url=cards.dashboard_url(ctx.guild.id, giveaway.id),
                ),
            ),
        )
        await ctx.respond(view=view, ephemeral=True)

    @giveaway.command(name="end")
    @option("giveaway", description="The giveaway to end now.", autocomplete=running_choices)
    async def end_giveaway(self, ctx: discord.ApplicationContext, giveaway: str):
        """Ends a giveaway now and picks its winners."""
        if not (found := await self._pick(ctx, giveaway)):
            return
        if found.status != "running":
            await ctx.respond(view=error_view(f"**{found.prize}** isn't running."), ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        if await actions.finish(self.client, found):
            await ctx.respond(view=success_view(f"Ended **{found.prize}**."), ephemeral=True)
        else:
            await ctx.respond(view=error_view(f"**{found.prize}** has already ended."), ephemeral=True)

    @giveaway.command(name="reroll")
    @option("giveaway", description="The ended giveaway to reroll.", autocomplete=ended_choices)
    @option("winner", description="Replace only this winner. Leave empty to replace all of them.", default=None)
    async def reroll_giveaway(self, ctx: discord.ApplicationContext, giveaway: str, winner: discord.User | None):
        """Picks new winners for an ended giveaway."""
        if not (found := await self._pick(ctx, giveaway)):
            return
        if found.status != "ended":
            await ctx.respond(view=error_view(f"**{found.prize}** hasn't ended yet."), ephemeral=True)
            return
        if winner and winner.id not in found.winner_ids:
            await ctx.respond(
                view=error_view(f"{winner.mention} (`{winner.name}`) didn't win **{found.prize}**."), ephemeral=True
            )
            return
        await ctx.defer(ephemeral=True)
        new = await actions.reroll(self.client, found, [winner.id] if winner else None)
        if new:
            await ctx.respond(view=success_view(f"Rerolled **{found.prize}**: {cards.mentions(new)}."), ephemeral=True)
        else:
            await ctx.respond(view=error_view(f"There's nobody left to win **{found.prize}**."), ephemeral=True)

    @giveaway.command(name="delete")
    @option("giveaway", description="The giveaway to delete.", autocomplete=any_choices)
    async def delete_giveaway(self, ctx: discord.ApplicationContext, giveaway: str):
        """Deletes a giveaway and its message."""
        if not (found := await self._pick(ctx, giveaway)):
            return
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"Delete **{found.prize}** and its message? Its entries go with it."),
                color=config.color.red,
            ),
            ui.ActionRow(
                ui.Button(
                    custom_id=f"giveaway:delete:{found.id}",
                    label="Yes, delete",
                    emoji=emoji.bin_white,
                    style=discord.ButtonStyle.red,
                )
            ),
            timeout=None,
            store=False,
        )
        await ctx.respond(view=view, ephemeral=True)

    @giveaway.command(name="list")
    async def list_giveaways(self, ctx: discord.ApplicationContext):
        """Lists this server's running and scheduled giveaways."""
        assert ctx.guild is not None
        live = await giveaways_db.search_giveaways(ctx.guild.id, ("running", "scheduled"), "", _CHOICES)
        if not live:
            lines = "No giveaways are running. Start one with `/giveaway start` or from the dashboard."
        else:
            rows = []
            for giveaway in sorted(live, key=lambda giveaway: (giveaway.status != "running", giveaway.ends_at)):
                if giveaway.status == "running" and giveaway.message_id:
                    link = f"https://discord.com/channels/{ctx.guild.id}/{giveaway.channel_id}/{giveaway.message_id}"
                    when = f"ends {discord.utils.format_dt(giveaway.ends_at, 'R')}"
                    rows.append(
                        f"{emoji.giveaway} [{giveaway.prize}]({link}) · {when} · `{fmt_count(giveaway.entry_count)}` entered"
                    )
                else:
                    when = f"starts {discord.utils.format_dt(giveaway.starts_at, 'R')}"
                    rows.append(f"{emoji.date} **{giveaway.prize}** · <#{giveaway.channel_id}> · {when}")
            lines = "\n".join(rows)
        view = DesignerView(
            ui.Container(ui.TextDisplay("## Giveaways"), ui.TextDisplay(lines)),
            cards.dashboard_row(ctx.guild.id),
        )
        await ctx.respond(view=view, ephemeral=True)


def setup(client: Client):
    client.add_cog(Giveaways(client))
