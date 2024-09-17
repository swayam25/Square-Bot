import discord
import asyncio
from utils import database as db, emoji
from discord.ext import commands
from discord.commands import slash_command, option

class Tickets(commands.Cog):
    def __init__(self, client):
        self.client = client

# Ticket create
    @slash_command(guild_ids=db.guild_ids(), name="create-ticket")
    @option("reason", description="Enter your reason for creating the ticket", required=False)
    async def create_ticket(self, ctx, reason: str = "No reason provided"):
        """Creates a ticket"""
        await ctx.defer()
        category = discord.utils.get(ctx.guild.categories, name="Tickets")
        if category is None:
            category = await ctx.guild.create_category("Tickets")
        create_ch = await category.create_text_channel(f"ticket-{ctx.author.id}")
        await create_ch.set_permissions(ctx.author, view_channel=True, send_messages=True, read_messages=True, add_reactions=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)
        await create_ch.set_permissions(self.client.user, view_channel=True, send_messages=True, read_messages=True, add_reactions=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)
        await create_ch.set_permissions(ctx.guild.default_role, view_channel=False, send_messages=False, read_messages=False)

        create_em = discord.Embed(
            title=f"{emoji.ticket} Ticket Created",
            description=f"Thank you for creating the ticket. Your problem will be solved soon! Stay tuned!\n" +
                        f"{emoji.bullet} **Author**: {ctx.author.mention}\n" +
                        f"{emoji.bullet} **Reason**: {reason}",
            color=db.theme_color
        )
        create_done_em = discord.Embed(
            title=f"{emoji.ticket} Ticket Created",
            description=f"Successfully created the ticket. ( {create_ch.mention} )",
            color=db.theme_color
        )
        await create_ch.send(ctx.author.mention, embed=create_em)
        await ctx.respond(embed=create_done_em)

        if db.ticket_log_ch(ctx.guild.id) != None:
            logging_ch = await self.client.fetch_channel(db.ticket_log_ch(ctx.guild.id))
            create_log_em = discord.Embed(
                title=f"{emoji.ticket} Ticket Created",
                description=f"{emoji.bullet} **Author**: {ctx.author.mention}\n" +
                            f"{emoji.bullet} **Reason**: {reason}",
                color=db.theme_color
            )
            await logging_ch.send(embed=create_log_em)

# Ticket close
    @slash_command(guild_ids=db.guild_ids(), name="close-ticket")
    async def create_ticker(self, ctx):
        """Closes a created ticket"""
        if (ctx.channel.name == f"ticket-{ctx.author.id}") or (ctx.channel.name.startswith("ticket-") and ctx.author.guild_permissions.manage_channels):
            close_em = discord.Embed(
                title=f"{emoji.ticket2} Closing Ticket",
                description=f"Closing ticket in 5 seconds.\n" +
                            f"{emoji.bullet} **Author**: {ctx.author.mention}",
                color=db.theme_color
            )
            await ctx.respond(embed=close_em)
            await asyncio.sleep(5)
            await ctx.channel.delete()
            if db.ticket_log_ch(ctx.guild.id) != None:
                logging_ch = await self.client.fetch_channel(db.ticket_log_ch(ctx.guild.id))
                close_log_em = discord.Embed(
                    title=f"{emoji.ticket2} Ticket Closed",
                    description=f"{emoji.bullet} **Author**: <@{ctx.channel.name.split("-")[1]}>\n" +
                                f"{emoji.bullet} **Closed By**: {ctx.author.mention}",
                    color=db.theme_color
                )
                await logging_ch.send(embed=close_log_em)
        else:
            error_em = discord.Embed(description=f"{emoji.error} This is not a ticket channel", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

def setup(client):
    client.add_cog(Tickets(client))
