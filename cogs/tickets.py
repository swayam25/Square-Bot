import asyncio
import discord
import io
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from utils import database as db
from utils.emoji import emoji


class TicketTranscript:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel

    async def create(self):
        messages = await self.channel.history(limit=500).flatten()
        with io.StringIO() as file:
            for message in reversed(messages):
                timestamp = message.created_at.strftime("%H:%M:%S %d-%m-%Y")
                if message.content:
                    file.write(f"[{timestamp}] {message.author}: {message.content}\n")
                else:
                    file.write(f"[{timestamp}] {message.author}: Embed/Attachment\n")
            file.seek(0)
            return discord.File(file, filename=f"ticket_{self.channel.id}.txt")


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # Interaction check
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.guild_permissions.manage_channels:
            return True
        else:
            ticket_check_em = discord.Embed(
                description=f"{emoji.error} You don't have `Manage Channels` permission to use this command.",
                color=db.error_color,
            )
            await interaction.response.send_message(embed=ticket_check_em, ephemeral=True)
            return False

    # Ticket close button
    @discord.ui.button(label="Close", emoji=emoji.lock, style=discord.ButtonStyle.grey, custom_id="close_ticket")
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        close_em = discord.Embed(
            title=f"{emoji.ticket2} Closing Ticket",
            description="Closing ticket in 5 seconds.\n"
            + f"{emoji.bullet} **Author**: <@{interaction.channel.name.split('-')[1]}>\n"
            + f"{emoji.bullet} **Closed By**: {interaction.user.mention}",
            color=db.theme_color,
        )
        await interaction.followup.send(embed=close_em)
        await asyncio.sleep(5)
        await interaction.channel.delete()
        if db.ticket_log_ch(interaction.guild.id) is not None:
            logging_ch = await interaction.channel.guild.fetch_channel(db.ticket_log_ch(interaction.guild.id))
            close_log_em = discord.Embed(
                title=f"{emoji.ticket2} Ticket Closed",
                description=f"{emoji.bullet} **Author**: <@{interaction.channel.name.split('-')[1]}>\n"
                + f"{emoji.bullet} **Closed By**: {interaction.user.mention}",
                color=db.theme_color,
            )
            await logging_ch.send(embed=close_log_em)

    # Ticket summary
    @discord.ui.button(
        label="Transcript", emoji=emoji.embed, style=discord.ButtonStyle.grey, custom_id="ticket_summary"
    )
    async def ticket_summary(self, button: discord.ui.Button, interaction: discord.Interaction):
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.trigger_typing()
        file = await TicketTranscript(interaction.channel).create()
        await interaction.followup.send(
            embed=discord.Embed(description=f"**Requested by**: {interaction.user.mention}", color=db.theme_color),
            file=file,
        )
        await asyncio.sleep(2)
        button.disabled = False
        await interaction.message.edit(view=self)


class Tickets(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Ticket slash cmd group
    ticket = SlashCommandGroup(guild_ids=db.guild_ids(), name="ticket", description="Ticket related commands.")

    # Ticket create
    @ticket.command(name="create")
    @option("reason", description="Enter your reason for creating the ticket", required=False)
    async def create_ticket(self, ctx: discord.ApplicationContext, reason: str = "No reason provided"):
        """Creates a ticket."""
        if db.ticket_cmds(ctx.guild.id) is False:
            error_em = discord.Embed(description=f"{emoji.error} Ticket commands are disabled", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)
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

            create_em = discord.Embed(
                title=f"{emoji.ticket} Ticket Created",
                description="Thank you for creating the ticket. Your problem will be solved soon! Stay tuned!\n"
                + f"{emoji.bullet} **Author**: {ctx.author.mention}\n"
                + f"{emoji.bullet} **Reason**: {reason}",
                color=db.theme_color,
            )
            await create_ch.send(ctx.author.mention, embed=create_em, view=TicketView())
            create_done_em = discord.Embed(
                title=f"{emoji.ticket} Ticket Created",
                description=f"Successfully created {create_ch.mention}.",
                color=db.theme_color,
            )
            await ctx.respond(embed=create_done_em)

            if db.ticket_log_ch(ctx.guild.id) is not None:
                logging_ch = await self.client.fetch_channel(db.ticket_log_ch(ctx.guild.id))
                create_log_em = discord.Embed(
                    title=f"{emoji.ticket} Ticket Created",
                    description=f"{emoji.bullet} **Author**: {ctx.author.mention}\n"
                    + f"{emoji.bullet} **Reason**: {reason}",
                    color=db.theme_color,
                )
                await logging_ch.send(embed=create_log_em)

    # Ticket close
    @ticket.command(name="close")
    async def close_ticket(self, ctx: discord.ApplicationContext):
        """Closes a created ticket."""
        if db.ticket_cmds(ctx.guild.id) is False:
            error_em = discord.Embed(description=f"{emoji.error} Ticket commands are disabled", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            if (ctx.channel.name == f"ticket-{ctx.author.id}") or (
                ctx.channel.name.startswith("ticket-") and ctx.author.guild_permissions.manage_channels
            ):
                close_em = discord.Embed(
                    title=f"{emoji.ticket2} Closing Ticket",
                    description="Closing ticket in 5 seconds.\n" + f"{emoji.bullet} **Author**: {ctx.author.mention}",
                    color=db.theme_color,
                )
                await ctx.respond(embed=close_em)
                await asyncio.sleep(5)
                await ctx.channel.delete()
                if db.ticket_log_ch(ctx.guild.id) is not None:
                    logging_ch = await self.client.fetch_channel(db.ticket_log_ch(ctx.guild.id))
                    close_log_em = discord.Embed(
                        title=f"{emoji.ticket2} Ticket Closed",
                        description=f"{emoji.bullet} **Author**: <@{ctx.channel.name.split('-')[1]}>\n"
                        + f"{emoji.bullet} **Closed By**: {ctx.author.mention}",
                        color=db.theme_color,
                    )
                    await logging_ch.send(embed=close_log_em)
            else:
                error_em = discord.Embed(
                    description=f"{emoji.error} This is not a ticket channel", color=db.error_color
                )
                await ctx.respond(embed=error_em, ephemeral=True)

    # Ticket transcript
    @ticket.command(name="transcript")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def transcript_ticket(self, ctx: discord.ApplicationContext):
        """Transcript an opened ticket."""
        if (ctx.channel.name == f"ticket-{ctx.author.id}") or (
            ctx.channel.name.startswith("ticket-") and ctx.author.guild_permissions.manage_channels
        ):
            await ctx.defer()
            file = await TicketTranscript(ctx.channel).create()
            await ctx.respond(file=file)
        else:
            error_em = discord.Embed(description=f"{emoji.error} This is not a ticket channel", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

    # Add ticket view on restart
    @commands.Cog.listener()
    async def on_ready(self):
        self.client.add_view(TicketView())


def setup(client: discord.Bot):
    client.add_cog(Tickets(client))
