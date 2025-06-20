import discord
from db.funcs.guild import fetch_guild_settings
from discord.ext import commands
from utils import config
from utils.emoji import emoji


class Logs(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Join
    @commands.Cog.listener()
    async def on_member_join(self, user: discord.Member):
        channel_id = (await fetch_guild_settings(user.guild.id)).mod_log_channel_id
        if channel_id is not None:
            join_ch = await self.client.fetch_channel(channel_id)
            join_em = discord.Embed(
                title="Member Joined",
                description=(
                    f"{emoji.user} **Name**: {user.mention} (`{user.name}`)\n"
                    f"{emoji.duration} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}"
                ),
                color=config.color.theme,
            )
            join_em.set_thumbnail(url=f"{user.avatar.url}")
            await join_ch.send(embed=join_em)

    # Leave
    @commands.Cog.listener()
    async def on_member_remove(self, user: discord.Member):
        channel_id = (await fetch_guild_settings(user.guild.id)).mod_log_channel_id
        if channel_id is not None:
            leave_ch = await self.client.fetch_channel(channel_id)
            leave_em = discord.Embed(
                title="Member Left",
                description=(
                    f"{emoji.user_red} **Name**: {user.mention} (`{user.name}`)\n"
                    f"{emoji.duration_red} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}\n"
                    f"{emoji.join_red} **Server Joined**: {discord.utils.format_dt(user.joined_at, 'R')}"
                ),
                color=config.color.red,
            )
            leave_em.set_thumbnail(url=f"{user.avatar.url}")
            await leave_ch.send(embed=leave_em)

    # Ban
    @commands.Cog.listener()
    async def on_member_ban(self, user: discord.Member):
        channel_id = (await fetch_guild_settings(user.guild.id)).mod_log_channel_id
        if channel_id is not None:
            ban_ch = await self.client.fetch_channel(channel_id)
            ban_em = discord.Embed(
                title="Member Banned",
                description=(
                    f"{emoji.user_red} **Name**: {user.mention} (`{user.name}`)\n"
                    f"{emoji.duration_red} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}\n"
                    f"{emoji.duration_red} **Server Joined**: {discord.utils.format_dt(user.joined_at, 'R')}"
                ),
                color=config.color.red,
            )
            ban_em.set_thumbnail(url=f"{user.avatar.url}")
            await ban_ch.send(embed=ban_em)

    # Unban
    @commands.Cog.listener()
    async def on_member_unban(self, user: discord.Member):
        channel_id = (await fetch_guild_settings(user.guild.id)).mod_log_channel_id
        if channel_id is not None:
            unban_ch = await self.client.fetch_channel(channel_id)
            unban_em = discord.Embed(
                title="Member Unbanned",
                description=(
                    f"{emoji.user} **Name**: {user.mention} (`{user.name}`)\n"
                    f"{emoji.duration} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}"
                ),
                color=config.color.theme,
            )
            unban_em.set_thumbnail(url=f"{user.avatar.url}")
            await unban_ch.send(embed=unban_em)

    # Edit
    @commands.Cog.listener()
    async def on_message_edit(self, msg_before: discord.Message, msg_after: discord.Message):
        if msg_before.guild:
            channel_id = (await fetch_guild_settings(msg_before.guild.id)).msg_log_channel_id
            if msg_before.author and msg_after.author == self.client.user:
                return
            elif msg_before.author.bot:
                return
            elif channel_id is not None:
                edit_ch = await self.client.fetch_channel(channel_id)
                edit_em = discord.Embed(
                    title="Message Edited",
                    description=(
                        f"{emoji.owner} **Author**: {msg_before.author.mention}\n"
                        f"{emoji.channel} **Channel**: {msg_before.channel.mention}\n"
                        f"{emoji.msg_link} **Message:** [Jump to Message]({msg_before.jump_url})\n"
                        f"{emoji.msg_red} **Original Message**: {msg_before.content}\n"
                        f"{emoji.msg_edit} **Edited Message**: {msg_after.content}"
                    ),
                    color=config.color.theme,
                )
                if msg_before.attachments:
                    edit_em.description += (
                        f"\n{emoji.img_red} **Removed Attachment**: [Click Here]({msg_before.attachments[0].url})"
                    )
                    edit_em.set_image(url=msg_before.attachments[0].url)
                await edit_ch.send(embed=edit_em)

    # Delete
    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        if msg.guild:
            channel_id = (await fetch_guild_settings(msg.guild.id)).msg_log_channel_id
            if msg.author == self.client.user:
                return
            elif msg.author.bot:
                return
            elif channel_id is not None:
                del_ch = await self.client.fetch_channel(channel_id)
                del_em = discord.Embed(
                    title="Message Deleted",
                    description=(
                        f"{emoji.owner_red} **Author**: {msg.author.mention}\n"
                        f"{emoji.channel_red} **Channel**: {msg.channel.mention}\n"
                        f"{emoji.msg_red} **Message**: {msg.content}"
                    ),
                    color=config.color.red,
                )
                if msg.attachments:
                    del_em.description += f"\n{emoji.img_red} **Attachment(s)**: {', '.join([f'[Click Here]({attachment.url})' for attachment in msg.attachments])}"
                await del_ch.send(embed=del_em)
                # Deleted Attachments
                if msg.attachments:
                    del_list: list = []
                    for attachment in msg.attachments:
                        del_em = discord.Embed(
                            title="Attachment Deleted",
                            description=(
                                f"{emoji.owner_red} **Author**: {msg.author.mention}\n"
                                f"{emoji.channel_red} **Channel**: {msg.channel.mention}\n"
                                f"{emoji.img_red} **Attachment**: [Click Here]({attachment.url})"
                            ),
                            color=config.color.red,
                        )
                        del_em.set_image(url=attachment.url)
                        del_list.append(del_em)
                    await del_ch.send(
                        embeds=del_list
                    )  # Limited to send 10 embeds because of discord limitations, user: discord.Members are also limited to 10 attachments per message so this will work fine.

    # Bulk delete
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, msgs: list[discord.Message]):
        if msgs[0].guild:
            channel_id = (await fetch_guild_settings(msgs[0].guild.id)).msg_log_channel_id
            if msgs[0].author == self.client.user:
                return
            elif msgs[0].author.bot:
                return
            elif channel_id is not None:
                bulk_ch = await self.client.fetch_channel(channel_id)
                bulk_em = discord.Embed(
                    title="Bulk Message Deleted",
                    description=f"{emoji.owner_red} **Author**: {msgs[0].author.mention}\n"
                    f"{emoji.channel_red} **Channel**: {msgs[0].channel.mention}\n"
                    f"{emoji.msg_red} **Messages Deleted**: {len(msgs)}",
                    color=config.color.red,
                )
                await bulk_ch.send(embed=bulk_em)


def setup(client: discord.Bot):
    client.add_cog(Logs(client))
