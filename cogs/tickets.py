import discord
import asyncio
from utils import database as db, emoji
from discord.ext import commands
from discord.commands import slash_command, Option

class Tickets(commands.Cog):
    def __init__(self, client):
        self.client = client

# Ticket create
    @slash_command(guild_ids=db.guild_ids(), name="create-ticket")
    async def ticket_create(
        self, ctx,
        reason: Option(str, "Enter your reason for creating fhe ticket", required=False)
    ):
        """Creates a ticket"""
        create_ch = await ctx.guild.create_text_channel(f"ticket-{ctx.author.id}")
        await create_ch.set_permissions(ctx.author, view_channel=True, send_messages=True, read_messages=True, add_reactions=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)
        await create_ch.set_permissions(self.client.user, view_channel=True, send_messages=True, read_messages=True, add_reactions=True, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)
        await create_ch.set_permissions(ctx.guild.default_role, view_channel=False, send_messages=False, read_messages=False)

        create_em = discord.Embed(
            title=f"{emoji.ticket} Ticket Created",
            description=f"Thank you for creating the ticket. Your problem will be solved soon! Stay tuned!\n"
                        f"{emoji.bullet} **Author**: {ctx.author.mention}\n"
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

        if db.ticket_log_channel_id(ctx.guild.id) != None:
            logging_ch = await self.client.fetch_channel(db.ticket_log_channel_id(ctx.guild.id))
            create_log_em = discord.Embed(
                title=f"{emoji.ticket} Ticket Created",
                description=f"{emoji.bullet} **Author**: {ctx.author.mention}\n"
                            f"{emoji.bullet} **Reason**: {reason}",
                color=db.theme_color
            )
            await logging_ch.send(embed=create_log_em)

# Ticket close
    @slash_command(guild_ids=db.guild_ids(), name="close-ticket")
    async def ticketClose(self, ctx):
        """Closes a created ticket"""
        if ctx.channel.name == f"ticket-{ctx.author.id}" :
            close_em = discord.Embed(
                title=f"{emoji.restart} Closing Ticket",
                description=f"Closing ticket in 5 seconds.\n"
                            f"{emoji.bullet} **Author**: {ctx.author.mention}",
                color=db.theme_color
            )
            await ctx.respond(embed=close_em)
            await asyncio.sleep(5) 
            await ctx.channel.delete()
            if db.ticket_log_channel_id(ctx.guild.id) != None:
                logging_ch = await self.client.fetch_channel(db.ticket_log_channel_id(ctx.guild.id))
                close_log_em = discord.Embed(
                    title=f"{emoji.ticket2} Ticket Closed",
                    description=f"{emoji.bullet} **Author**: {ctx.author.mention}",
                    color=db.theme_color
                )
                await logging_ch.send(embed=close_log_em)
        else:
            error_em = discord.Embed(description=f"{emoji.error} This is not a ticket channel", color=db.error_color)
            await ctx.respond(embed=error_em, ephemeral=True)

def setup(client):
    client.add_cog(Tickets(client))
