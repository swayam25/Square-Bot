import asyncio
import datetime
import discord
import io
from db.funcs.guild import fetch_guild_settings
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from utils import config
from utils.emoji import emoji
from utils.view import View


async def close_ticket(
    channel: discord.TextChannel,
    author: discord.Member,
    send_function,
    closed_by: discord.User | discord.Member | None = None,
):
    """Helper function to close a ticket."""
    view = View(
        discord.ui.Container(
            discord.ui.TextDisplay(
                f"Closing ticket {discord.utils.format_dt(datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=5), 'R')}\n"
                f"{emoji.owner_red} **Author**: {author.mention}"
                + (f"\n{emoji.user_red} **Closed By**: {closed_by.mention}" if closed_by else "")
            ),
            color=config.color.red,
        )
    )
    await send_function(view=view)
    transcript_task = asyncio.create_task(TicketTranscript(channel).create())
    await asyncio.sleep(5)
    file = await transcript_task
    await channel.delete()
    log_ch_id = (await fetch_guild_settings(channel.guild.id)).ticket_log_channel_id
    if log_ch_id is not None:
        logging_ch = await channel.guild.fetch_channel(log_ch_id)
        view = View(
            discord.ui.Container(
                discord.ui.Section(
                    discord.ui.TextDisplay("## Ticket Closed"),
                    discord.ui.TextDisplay(
                        f"{emoji.owner_red} **Author**: <@{channel.name.split('-')[1]}>\n{emoji.user_red} **Closed By**: {author.mention}"
                    ),
                ),
                color=config.color.red,
            )
        )
        await logging_ch.send(view=view, file=file)


class TicketTranscript:
    """
    Class to create a transcript of a ticket channel.

    Attributes:
        channel (discord.TextChannel): The ticket channel to create a transcript for.
    """

    def __init__(self, channel: discord.TextChannel):
        self.channel = channel

    async def create(self) -> discord.File:
        """Creates a transcript of the ticket channel."""
        messages = await self.channel.history(limit=500).flatten()
        with io.StringIO() as file:
            for message in reversed(messages):
                if message.content:
                    file.write(f"{message.author}: {message.content}\n")
                else:
                    file.write(f"{message.author}: Embed/Attachment\n")
            file.seek(0)
            return discord.File(file, filename=f"ticket_{self.channel.id}.txt")


class TicketView(View):
    def __init__(self, ctx: discord.ApplicationContext | None = None, reason: str = "No reason provided"):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.reason = reason
        if ctx:
            self.build()

    # Interaction check
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.guild_permissions.manage_channels:
            return True
        else:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.error} You don't have `Manage Channels` permission to use this command."
                    ),
                    color=config.color.red,
                )
            )
            await interaction.response.send_message(view=view, ephemeral=True)
            return False

    # Build
    def build(self):
        """Builds the ticket view."""
        if self.ctx and hasattr(self.ctx, "author") and self.ctx.author:
            author_mention = self.ctx.author.mention
        else:
            author_mention = "Unknown"
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    "## Ticket Created\nThank you for creating the ticket. Your problem will be solved soon! Stay tuned!"
                ),
                discord.ui.TextDisplay(
                    f"{emoji.user} **Author**: {author_mention}\n{emoji.description} **Reason**: {self.reason}"
                ),
            )
        )
        for label, btn_emoji, callback in (
            ("Close", emoji.lock_white, self.close_ticket),
            ("Transcript", emoji.description_white, self.ticket_transcript),
        ):
            btn = discord.ui.Button(
                label=label,
                emoji=btn_emoji,
                style=discord.ButtonStyle.grey,
                custom_id=f"ticket_{label.lower()}",
            )
            btn.callback = callback
            self.add_item(btn)

    # Ticket close button
    async def close_ticket(self, interaction: discord.Interaction):
        self.disable_all_items()
        await interaction.edit(view=self)
        await close_ticket(interaction.channel, interaction.user, interaction.followup.send, closed_by=interaction.user)

    # Ticket summary
    async def ticket_transcript(self, interaction: discord.Interaction):
        button: discord.ui.Button = self.get_item("ticket_transcript")
        button.disabled = True
        await interaction.edit(view=self)
        await interaction.channel.trigger_typing()
        file = await TicketTranscript(interaction.channel).create()
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.user} **Requested by**: {interaction.user.mention}"),
            )
        )
        await interaction.followup.send(view=view, file=file)
        await asyncio.sleep(2)
        button.disabled = False
        await interaction.message.edit(view=self)


class Tickets(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Ticket slash cmd group
    ticket = SlashCommandGroup(name="ticket", description="Ticket related commands.")

    # Ticket create
    @ticket.command(name="create")
    @option("reason", description="Enter your reason for creating the ticket", required=False)
    async def create_ticket(self, ctx: discord.ApplicationContext, reason: str = "No reason provided"):
        """Creates a ticket."""
        ticket_status = (await fetch_guild_settings(ctx.guild.id)).ticket_cmds
        if not ticket_status:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} Ticket commands are disabled"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await ctx.defer()
            category = discord.utils.get(ctx.guild.categories, name="Tickets")
            if category is None:
                category = await ctx.guild.create_category("Tickets")
                await category.set_permissions(ctx.guild.default_role, view_channel=False)
                await category.set_permissions(ctx.guild.me, view_channel=True)
            create_ch = await category.create_text_channel(f"ticket-{ctx.author.id}")
            await create_ch.set_permissions(
                ctx.author,
                view_channel=True,
                send_messages=True,
                read_messages=True,
                add_reactions=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                external_emojis=True,
            )
            await create_ch.set_permissions(
                ctx.guild.me,
                view_channel=True,
                send_messages=True,
                read_messages=True,
                add_reactions=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                external_emojis=True,
            )
            await create_ch.set_permissions(
                ctx.guild.default_role, view_channel=False, send_messages=False, read_messages=False
            )

            view = TicketView(
                ctx=ctx,
                reason=reason,
            )
            await create_ch.send(view=view)
            done_view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        f"{emoji.success} Successfully created {create_ch.mention}.",
                    ),
                    color=config.color.green,
                )
            )
            await ctx.respond(view=done_view)

            log_ch_id = (await fetch_guild_settings(ctx.guild.id)).ticket_log_channel_id
            if log_ch_id is not None:
                logging_ch = await self.client.fetch_channel(log_ch_id)
                log_view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Ticket Created"),
                        discord.ui.TextDisplay(f"{emoji.user} **Author**: {ctx.author.mention}"),
                        discord.ui.TextDisplay(f"{emoji.description} **Reason**: {reason}"),
                    )
                )
                await logging_ch.send(view=log_view)

    # Ticket close
    @ticket.command(name="close")
    async def close_ticket(self, ctx: discord.ApplicationContext):
        """Closes a created ticket."""
        ticket_status = (await fetch_guild_settings(ctx.guild.id)).ticket_cmds
        if not ticket_status:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} Ticket commands are disabled"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            if (ctx.channel.name == f"ticket-{ctx.author.id}") or (
                ctx.channel.name.startswith("ticket-") and ctx.author.guild_permissions.manage_channels
            ):
                await ctx.defer()
                await close_ticket(ctx.channel, ctx.author, ctx.respond)
            else:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay(f"{emoji.error} This is not a ticket channel"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)

    # Ticket transcript
    @ticket.command(name="transcript")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def transcript_ticket(self, ctx: discord.ApplicationContext):
        """Transcript an opened ticket."""
        if (ctx.channel.name == f"ticket-{ctx.author.id}") or (
            ctx.channel.name.startswith("ticket-") and ctx.author.guild_permissions.manage_channels
        ):
            await ctx.defer()
            file = await TicketTranscript(ctx.channel).create()
            await ctx.respond(file=file)
        else:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} This is not a ticket channel"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Add ticket view on restart
    @commands.Cog.listener()
    async def on_ready(self):
        self.client.add_view(TicketView())


def setup(client: discord.Bot):
    client.add_cog(Tickets(client))
