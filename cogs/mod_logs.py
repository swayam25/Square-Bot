import discord
from utils import database as db, emoji
from discord.ext import commands

class Logs(commands.Cog):
    def __init__(self, client):
        self.client = client

# Join
    @commands.Cog.listener()
    async def on_member_join(self, user):
        if db.mod_log_ch(user.guild.id) != None:
            join_ch = await self.client.fetch_channel(db.mod_log_ch(user.guild.id))
            join_em = discord.Embed(
                title=f"{emoji.plus} Member Joined",
                description=f"{emoji.bullet} **Name**: {user.mention}\n" +
                            f"{emoji.bullet} **Account Created**: {discord.utils.format_dt(user.created_at, "R")}", color=db.theme_color)
            join_em.set_thumbnail(url=f"{user.avatar.url}")
            await join_ch.send(embed=join_em)

# Leave
    @commands.Cog.listener()
    async def on_member_remove(self, user):
        if db.mod_log_ch(user.guild.id) != None:
            leave_ch = await self.client.fetch_channel(db.mod_log_ch(user.guild.id))
            leave_em = discord.Embed(
                title=f"{emoji.minus} Member Left",
                description=f"{emoji.bullet} **Name**: {user.mention}\n" +
                            f"{emoji.bullet} **Account Created**: {discord.utils.format_dt(user.created_at, "R")}", color=db.theme_color)
            leave_em.set_thumbnail(url=f"{user.avatar.url}")
            await leave_ch.send(embed=leave_em)


# Ban
    @commands.Cog.listener()
    async def on_member_ban(self, user):
        if db.mod_log_ch(user.guild.id) != None:
            ban_ch = await self.client.fetch_channel(db.mod_log_ch(user.guild.id))
            ban_em = discord.Embed(
                title=f"{emoji.mod2} Member Banned",
                description=f"{emoji.bullet} **Name**: {user.mention}\n" +
                            f"{emoji.bullet} **Account Created**: {discord.utils.format_dt(user.created_at, "R")}", color=db.theme_color)
            ban_em.set_thumbnail(url=f"{user.avatar.url}")
            await ban_ch.send(embed=ban_em)

# Unban
    @commands.Cog.listener()
    async def on_member_unban(self, user):
        if db.mod_log_ch(user.guild.id) != None:
            unban_ch = await self.client.fetch_channel(db.mod_log_ch(user.guild.id))
            unban_em = discord.Embed(
                title=f"{emoji.mod} Member Unbanned",
                description=f"{emoji.bullet} **Name**: {user.mention}\n" +
                            f"{emoji.bullet} **Account Created**: {discord.utils.format_dt(user.created_at, "R")}", color=db.theme_color)
            unban_em.set_thumbnail(url=f"{user.avatar.url}")
            await unban_ch.send(embed=unban_em)

# Edit
    @commands.Cog.listener()
    async def on_message_edit(self, msg_before, msg_after):
        msg_ch = db.msg_log_ch(msg_before.guild.id)
        if msg_before.author and msg_after.author == self.client.user:
            return
        elif msg_before.author.bot:
            return
        elif msg_ch != None:
            edit_ch= await self.client.fetch_channel(msg_ch)
            edit_em = discord.Embed(
                title=f"{emoji.edit} Message Edited",
                description=f"{emoji.bullet} **Author**: {msg_before.author.mention}\n" +
                            f"{emoji.bullet} **Channel**: {msg_before.channel.mention}\n" +
                            f"{emoji.bullet} **Original Message**: {msg_before.content}\n" +
                            f"{emoji.bullet} **Edited Message**: {msg_after.content}",
                color=db.theme_color)
            if msg_before.attachments:
                edit_em.description += f"\n{emoji.bullet} **Removed Attachment**: [Click Here]({msg_before.attachments[0].url})"
                edit_em.set_image(url=msg_before.attachments[0].url)
            await edit_ch.send(embed=edit_em)

# Delete
    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        msg_ch = db.msg_log_ch(msg.guild.id)
        if msg.author == self.client.user:
            return
        elif msg.author.bot:
            return
        elif msg_ch != None:
            del_ch = await self.client.fetch_channel(msg_ch)
            del_em = discord.Embed(
                title=f"{emoji.bin} Message Deleted",
                description=f"{emoji.bullet} **Author**: {msg.author.mention}\n" +
                            f"{emoji.bullet} **Channel**: {msg.channel.mention}\n" +
                            f"{emoji.bullet} **Message**: {msg.content}",
                color=db.theme_color)
            if msg.attachments:
                del_em.description += f"\n{emoji.bullet} **Attachment(s)**: {', '.join([f'[Click Here]({attachment.url})' for attachment in msg.attachments])}"
            await del_ch.send(embed=del_em)
            # Deleted Attachments
            if msg.attachments:
                del_list: list = []
                for attachment in msg.attachments:
                    del_em = discord.Embed(
                        title=f"{emoji.bin} Attachment Deleted",
                        description=f"{emoji.bullet} **Author**: {msg.author.mention}\n" +
                                    f"{emoji.bullet} **Channel**: {msg.channel.mention}\n" +
                                    f"{emoji.bullet} **Attachment**: [Click Here]({attachment.url})",
                        color=db.theme_color)
                    del_em.set_image(url=attachment.url)
                    del_list.append(del_em)
                await del_ch.send(embeds=del_list) # Limited to send 10 embeds because of discord limitations, users are also limited to 10 attachments per message so this will work fine.

# Bulk delete
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, msgs):
        msg_ch = db.msg_log_ch(msgs[0].guild.id)
        if msgs[0].author == self.client.user:
            return
        elif msgs[0].author.bot:
            return
        elif msg_ch != None:
            bulk_ch = await self.client.fetch_channel(msg_ch)
            bulk_em = discord.Embed(
                title=f"{emoji.bin} Bulk Message Deleted",
                description=f"{emoji.bullet} **Author**: {msgs[0].author.mention}\n" +
                            f"{emoji.bullet} **Channel**: {msgs[0].channel.mention}\n" +
                            f"{emoji.bullet} **Messages Deleted**: {len(msgs)}",
                color=db.theme_color)
            await bulk_ch.send(embed=bulk_em)

def setup(client):
    client.add_cog(Logs(client))
