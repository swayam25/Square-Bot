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
                            f"{emoji.bullet} **Account Created**: {user.created_at.__format__(db.datetime_format())}", color=db.theme_color)
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
                            f"{emoji.bullet} **Account Created**: {user.created_at.__format__(db.datetime_format())}", color=db.theme_color)
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
                            f"{emoji.bullet} **Account Created**: {user.created_at.__format__(db.datetime_format())}", color=db.theme_color)
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
                            f"{emoji.bullet} **Account Created**: {user.created_at.__format__(db.datetime_format())}", color=db.theme_color)
            unban_em.set_thumbnail(url=f"{user.avatar.url}")
            await unban_ch.send(embed=unban_em)

# Edit
    @commands.Cog.listener()
    async def on_message_edit(self, msg_before, msg_after):
        if msg_before.author and msg_after.author == self.client.user:
            pass
        elif db.mod_log_ch(msg_before.guild.id) != None:
            edit_ch= await self.client.fetch_channel(db.mod_log_ch(msg_before.guild.id))
            edit_em = discord.Embed(
                title=f"{emoji.edit} Message Edited",
                description=f"{emoji.bullet} **Author**: {msg_before.author.mention}\n" +
                            f"{emoji.bullet} **Original Message**: {msg_before.content}\n" +
                            f"{emoji.bullet} **Edited Message**: {msg_after.content}", color=db.theme_color)
            await edit_ch.send(embed=edit_em)

# Delete
    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        if msg.author == self.client.user:
            pass
        elif db.mod_log_ch(msg.guild.id) != None:
            del_ch = await self.client.fetch_channel(db.mod_log_ch(msg.guild.id))
            del_em = discord.Embed(
                title=f"{emoji.bin} Message Deleted",
                description=f"{emoji.bullet} **Author**: {msg.author.mention}\n" +
                            f"{emoji.bullet} **Message**: {msg.content}", color=db.theme_color)
            await del_ch.send(embed=del_em)

def setup(client):
    client.add_cog(Logs(client))
