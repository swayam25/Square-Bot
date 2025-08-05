import discord
from core import Client
from core.view import View
from db.funcs.guild import fetch_guild_settings
from discord.ext import commands
from utils import config
from utils.emoji import emoji


class Logs(commands.Cog):
    def __init__(self, client: Client):
        self.client = client
        self.allowed_mentions = discord.AllowedMentions(
            users=False,
            roles=False,
            everyone=False,
        )

    # Join
    @commands.Cog.listener()
    async def on_member_join(self, user: discord.Member):
        channel_id = (await fetch_guild_settings(user.guild.id)).mod_log_channel_id
        if channel_id is not None:
            join_ch = await self.client.fetch_channel(channel_id)
            view = View(
                discord.ui.Container(
                    discord.ui.Section(
                        discord.ui.TextDisplay("## Member Joined"),
                        discord.ui.TextDisplay(
                            f"{emoji.user} **Name**: {user.mention} (`{user.name}`)\n"
                            f"{emoji.duration} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}"
                        ),
                        accessory=discord.ui.Thumbnail(user.avatar.url if user.avatar else ""),
                    ),
                )
            )
            await join_ch.send(view=view, allowed_mentions=self.allowed_mentions)

    # Leave
    @commands.Cog.listener()
    async def on_member_remove(self, user: discord.Member):
        channel_id = (await fetch_guild_settings(user.guild.id)).mod_log_channel_id
        if channel_id is not None:
            leave_ch = await self.client.fetch_channel(channel_id)
            view = View(
                discord.ui.Container(
                    discord.ui.Section(
                        discord.ui.TextDisplay("## Member Left"),
                        discord.ui.TextDisplay(
                            f"{emoji.user_red} **Name**: {user.mention} (`{user.name}`)\n"
                            f"{emoji.duration_red} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}\n"
                            f"{emoji.join_red} **Server Joined**: {discord.utils.format_dt(user.joined_at, 'R')}"
                        ),
                        accessory=discord.ui.Thumbnail(user.avatar.url if user.avatar else ""),
                    ),
                    color=config.color.red,
                )
            )
            await leave_ch.send(view=view, allowed_mentions=self.allowed_mentions)

    # Ban
    @commands.Cog.listener()
    async def on_member_ban(self, user: discord.Member):
        channel_id = (await fetch_guild_settings(user.guild.id)).mod_log_channel_id
        if channel_id is not None:
            ban_ch = await self.client.fetch_channel(channel_id)
            view = View(
                discord.ui.Container(
                    discord.ui.Section(
                        discord.ui.TextDisplay("## Member Banned"),
                        discord.ui.TextDisplay(
                            f"{emoji.user_red} **Name**: {user.mention} (`{user.name}`)\n"
                            f"{emoji.duration_red} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}\n"
                            f"{emoji.duration_red} **Server Joined**: {discord.utils.format_dt(user.joined_at, 'R')}"
                        ),
                        accessory=discord.ui.Thumbnail(user.avatar.url if user.avatar else ""),
                    ),
                    color=config.color.red,
                )
            )
            await ban_ch.send(view=view, allowed_mentions=self.allowed_mentions)

    # Unban
    @commands.Cog.listener()
    async def on_member_unban(self, user: discord.Member):
        channel_id = (await fetch_guild_settings(user.guild.id)).mod_log_channel_id
        if channel_id is not None:
            unban_ch = await self.client.fetch_channel(channel_id)
            view = View(
                discord.ui.Container(
                    discord.ui.Section(
                        discord.ui.TextDisplay("## Member Unbanned"),
                        discord.ui.TextDisplay(
                            f"{emoji.user} **Name**: {user.mention} (`{user.name}`)\n"
                            f"{emoji.duration} **Account Created**: {discord.utils.format_dt(user.created_at, 'R')}"
                        ),
                        accessory=discord.ui.Thumbnail(user.avatar.url if user.avatar else ""),
                    ),
                )
            )
            await unban_ch.send(view=view, allowed_mentions=self.allowed_mentions)

    # Edit
    @commands.Cog.listener()
    async def on_message_edit(self, msg_before: discord.Message, msg_after: discord.Message):
        if msg_before.guild:
            channel_id = (await fetch_guild_settings(msg_before.guild.id)).msg_log_channel_id
            if any(
                [
                    msg_before.author == self.client.user,
                    msg_after.author == self.client.user,
                    msg_before.author.bot,
                    msg_after.author.bot,
                    msg_before.content == msg_after.content,
                ]
            ):
                return
            elif channel_id is not None:
                edit_ch = await self.client.fetch_channel(channel_id)
                items: list[discord.ui.Item] = [
                    discord.ui.TextDisplay("## Message Edited"),
                    discord.ui.TextDisplay(
                        f"{emoji.owner} **Author**: {msg_before.author.mention}\n"
                        f"{emoji.channel} **Channel**: {msg_before.channel.mention}\n"
                        f"{emoji.msg_red} **Original Message**: {msg_before.content}\n"
                        f"{emoji.msg_edit} **Edited Message**: {msg_after.content}"
                    ),
                ]
                if msg_before.attachments:
                    items.append(discord.ui.TextDisplay(f"## Removed Attachment [`{len(msg_before.attachments)}`]"))
                    items.append(
                        discord.ui.MediaGallery(
                            discord.MediaGalleryItem(url=media.url) for media in msg_before.attachments
                        )
                    )
                view = View(
                    discord.ui.Container(*items),
                    discord.ui.Button(label="Jump to Message", url=msg_before.jump_url, style=discord.ButtonStyle.link),
                )
                await edit_ch.send(view=view, allowed_mentions=self.allowed_mentions)

    # Delete
    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        if msg.guild:
            channel_id = (await fetch_guild_settings(msg.guild.id)).msg_log_channel_id
            if msg.author == self.client.user or msg.author.bot:
                return
            elif channel_id is not None:
                del_ch = await self.client.fetch_channel(channel_id)
                items: list[discord.ui.Item] = [
                    discord.ui.TextDisplay("## Message Deleted"),
                    discord.ui.TextDisplay(
                        f"{emoji.owner_red} **Author**: {msg.author.mention}\n"
                        f"{emoji.channel_red} **Channel**: {msg.channel.mention}\n"
                        f"{emoji.msg_red} **Message**: {msg.content}"
                    ),
                ]
                if msg.attachments:
                    items.append(discord.ui.TextDisplay(f"## Deleted Attachment [`{len(msg.attachments)}`]"))
                    items.append(
                        discord.ui.MediaGallery(discord.MediaGalleryItem(url=media.url) for media in msg.attachments)
                    )
                view = View(discord.ui.Container(*items, color=config.color.red))
                await del_ch.send(view=view, allowed_mentions=self.allowed_mentions)

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
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay("## Bulk Message Deleted"),
                        discord.ui.TextDisplay(
                            f"{emoji.owner_red} **Author**: {msgs[0].author.mention}\n"
                            f"{emoji.channel_red} **Channel**: {msgs[0].channel.mention}\n"
                            f"{emoji.msg_red} **Messages Deleted**: {len(msgs)}"
                        ),
                        color=config.color.red,
                    )
                )
                await bulk_ch.send(view=view, allowed_mentions=self.allowed_mentions)


def setup(client: Client):
    client.add_cog(Logs(client))
