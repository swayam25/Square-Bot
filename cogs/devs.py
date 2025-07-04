import discord
import discord.ui
import math
import os
import sys
import zipfile
from db.funcs.dev import add_dev, fetch_dev_ids, remove_dev
from db.funcs.guild import add_guild, remove_guild
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from io import BytesIO
from utils import check, config
from utils.emoji import Emoji, emoji


class GuildListView(discord.ui.View):
    def __init__(self, client: discord.Bot, ctx: discord.ApplicationContext, page: int, timeout: int):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.client = client
        self.ctx = ctx
        self.page = page
        self.items_per_page = 10
        self.interaction_check = lambda i: check.author_interaction_check(ctx, i)

    # Start
    @discord.ui.button(emoji=f"{emoji.start_white}", custom_id="start", style=discord.ButtonStyle.grey)
    async def start_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page = 1
        em = GuildListEmbed(self.client, self.page).get_embed()
        await interaction.response.edit_message(embed=em, view=self)

    # Previous
    @discord.ui.button(emoji=f"{emoji.previous_white}", custom_id="previous", style=discord.ButtonStyle.grey)
    async def previous_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        pages = math.ceil(len(self.client.guilds) / self.items_per_page)
        if self.page <= 1:
            self.page = pages
        else:
            self.page -= 1
        em = GuildListEmbed(self.client, self.page).get_embed()
        await interaction.response.edit_message(embed=em, view=self)

    # Next
    @discord.ui.button(emoji=f"{emoji.next_white}", custom_id="next", style=discord.ButtonStyle.grey)
    async def next_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        pages = math.ceil(len(self.client.guilds) / self.items_per_page)
        if self.page >= pages:
            self.page = 1
        else:
            self.page += 1
        em = GuildListEmbed(self.client, self.page).get_embed()
        await interaction.response.edit_message(embed=em, view=self)

    # End
    @discord.ui.button(emoji=f"{emoji.end_white}", custom_id="end", style=discord.ButtonStyle.grey)
    async def end_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.page = math.ceil(len(self.client.guilds) / self.items_per_page)
        em = GuildListEmbed(self.client, self.page).get_embed()
        await interaction.response.edit_message(embed=em, view=self)


class GuildListEmbed(discord.Embed):
    def __init__(self, client: discord.Bot, page: int):
        super().__init__(title="Guilds List", color=config.color.theme)
        self.client = client
        self.page = page
        self.items_per_page = 10

    def get_guilds(self):
        guilds = self.client.guilds
        start = (self.page - 1) * self.items_per_page
        end = start + self.items_per_page
        return guilds[start:end]

    def get_guilds_list(self):
        guilds_list = ""
        for num, guild in enumerate(self.get_guilds(), start=self.items_per_page * (self.page - 1) + 1):
            guilds_list += f"`{num}.` **{guild.name}** - `{guild.id}`\n"
        return guilds_list

    def get_footer(self):
        total_pages = math.ceil(len(self.client.guilds) / self.items_per_page)
        return f"Viewing Page {self.page}/{total_pages}"

    def get_embed(self):
        self.description = self.get_guilds_list()
        self.set_footer(text=self.get_footer())
        return self


class Devs(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client = client

    # On start
    @commands.Cog.listener("on_ready")
    async def when_bot_gets_ready(self):
        start_log_ch = await self.client.fetch_channel(config.system_channel_id)
        start_log_em = discord.Embed(
            description=f"{emoji.success} Logged in as **{self.client.user}** with ID `{self.client.user.id}`",
            color=config.color.green,
        )
        await start_log_ch.send(embed=start_log_em)

    # On guild joined
    @commands.Cog.listener("on_guild_join")
    async def when_guild_joined(self, guild: discord.Guild):
        await add_guild(guild.id)
        join_log_ch = await self.client.fetch_channel(config.system_channel_id)
        join_log_em = discord.Embed(
            title="Someone Added Me!",
            description=(
                f"{emoji.server} **Name**: {guild.name}\n"
                f"{emoji.id} **ID**: `{guild.id}`\n"
                f"{emoji.members} **Total Members**: `{guild.member_count} ({len([m for m in guild.members if not m.bot])} Humans | {len([m for m in guild.members if m.bot])} Bots)`"
            ),
            color=config.color.theme,
        )
        await join_log_ch.send(embed=join_log_em)

    # On guild leave
    @commands.Cog.listener("on_guild_remove")
    async def when_removed_from_guild(self, guild: discord.Guild):
        await remove_guild(guild.id)
        leave_log_ch = await self.client.fetch_channel(config.system_channel_id)
        leave_log_em = discord.Embed(
            title="Someone Removed Me!",
            description=(
                f"{emoji.server_red} **Name**: {guild.name}\n"
                f"{emoji.id_red} **ID**: `{guild.id}`\n"
                f"{emoji.members_red} **Total Members**: `{guild.member_count} ({len([m for m in guild.members if not m.bot])} Humans | {len([m for m in guild.members if m.bot])} Bots)`"
            ),
            color=config.color.red,
        )
        await leave_log_ch.send(embed=leave_log_em)

    # Dev slash cmd group
    dev = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="dev", description="Developer related commands.")

    # Add dev
    @dev.command(name="add")
    @option("user", description="Mention the user whom you want to add to dev")
    @check.is_owner()
    async def add_dev(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Adds a bot dev."""
        await add_dev(user.id)
        done_em = discord.Embed(description=f"{emoji.success} Added {user.mention} to dev.", color=config.color.green)
        await ctx.respond(embed=done_em)

    # Remove dev
    @dev.command(name="remove")
    @option("user", description="Mention the user whom you want to remove from dev")
    @check.is_owner()
    async def remove_dev(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Removes a bot dev."""
        await remove_dev(user.id)
        done_em = discord.Embed(
            description=f"{emoji.success} Removed {user.mention} from dev",
            color=config.color.green,
        )
        await ctx.respond(embed=done_em)

    # List devs
    @dev.command(name="list")
    @check.is_owner()
    async def list_devs(self, ctx: discord.ApplicationContext):
        """Shows bot devs."""
        num = 0
        devs_list = ""
        dev_ids = await fetch_dev_ids()
        for ids in dev_ids:
            num += 1
            dev_mention = f"<@{ids}>"
            devs_list += f"`{num}.` {dev_mention}\n"
        dev_em = discord.Embed(title="Devs List", description=devs_list, color=config.color.theme)
        await ctx.respond(embed=dev_em)

    # Restart
    @slash_command(guild_ids=config.owner_guild_ids, name="restart")
    @check.is_dev()
    async def restart(self, ctx: discord.ApplicationContext):
        """Restarts the bot."""
        restart_em = discord.Embed(description=f"{emoji.restart} Restarting...", color=config.color.theme)
        await ctx.respond(embed=restart_em)
        await self.client.wait_until_ready()
        await self.client.close()
        os.system("clear")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # Reload cogs
    @slash_command(guild_ids=config.owner_guild_ids, name="reload-cogs")
    @check.is_dev()
    async def reload_cogs(self, ctx: discord.ApplicationContext):
        """Reloads the bot cogs."""
        reload_em = discord.Embed(description=f"{emoji.restart} Reloaded Cogs.", color=config.color.theme)
        await ctx.respond(embed=reload_em, ephemeral=True, delete_after=2)
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                self.client.reload_extension(f"cogs.{filename[:-3]}")

    # Shutdown
    @slash_command(guild_ids=config.owner_guild_ids, name="shutdown")
    @check.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext):
        """Shutdowns the bot."""
        shutdown_em = discord.Embed(description=f"{emoji.shutdown} Bot shutdown.", color=config.color.red)
        await ctx.respond(embed=shutdown_em)
        await self.client.wait_until_ready()
        await self.client.close()

    # Set status
    @slash_command(guild_ids=config.owner_guild_ids, name="status")
    @option("type", description="Choose bot status type", choices=["Game", "Streaming", "Listening", "Watching"])
    @option("status", description="Enter new status of bot")
    @check.is_dev()
    async def set_status(self, ctx: discord.ApplicationContext, type: str, status: str):
        """Sets custom bot status."""
        if type == "Game":
            await self.client.change_presence(activity=discord.Game(name=status))
        elif type == "Streaming":
            await self.client.change_presence(activity=discord.Streaming(name=status, url=config.support_server_url))
        elif type == "Listening":
            await self.client.change_presence(
                activity=discord.Activity(type=discord.ActivityType.listening, name=status)
            )
        elif type == "Watching":
            await self.client.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=status)
            )
        status_em = discord.Embed(
            description=f"{emoji.success} Status changed to **{type}** as `{status}`",
            color=config.color.green,
        )
        await ctx.respond(embed=status_em)

    # Guild slash cmd group
    guild = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="guild", description="Guild related commands.")

    # List guild
    @guild.command(name="list")
    @check.is_owner()
    async def list_guilds(self, ctx: discord.ApplicationContext):
        """Shows all guilds."""
        guild_list_em = GuildListEmbed(self.client, 1).get_embed()
        guild_list_view = None
        if len(self.client.guilds) > 10:
            guild_list_view = GuildListView(self.client, ctx, 1, timeout=60)
        await ctx.respond(embed=guild_list_em, view=guild_list_view)

    # Leave guild
    @guild.command(name="leave")
    @option(
        "guild",
        description="Enter the guild name",
        autocomplete=lambda self, ctx: [
            guild.name for guild in self.client.guilds if not any(guild.id == g for g in config.owner_guild_ids)
        ],
    )
    @check.is_owner()
    async def leave_guild(self, ctx: discord.ApplicationContext, guild: discord.Guild):
        """Leaves a guild."""
        if any(guild.id == g for g in config.owner_guild_ids):
            error_em = discord.Embed(
                description=f"{emoji.error} I can't leave the owner guild.", color=config.color.red
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            await guild.leave()
            leave_em = discord.Embed(
                description=f"{emoji.success} Left the guild **{guild.name}** with ID `{guild.id}`",
                color=config.color.green,
            )
            await ctx.respond(embed=leave_em)

    # Guild invite
    @guild.command(name="invite")
    @option(
        "guild",
        description="Enter the guild name",
        autocomplete=lambda self, ctx: [
            guild.name for guild in self.client.guilds if not any(guild.id == g for g in config.owner_guild_ids)
        ],
    )
    @check.is_owner()
    async def guild_inv(self, ctx: discord.ApplicationContext, guild: discord.Guild):
        """Creates an invite link for the guild."""
        if any(guild.id == g for g in config.owner_guild_ids):
            error_em = discord.Embed(
                description=f"{emoji.error} I can't create an invite link for the owner guild",
                color=config.color.red,
            )
            await ctx.respond(embed=error_em, ephemeral=True)
        else:
            invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=0)
            await ctx.respond(invite.url)

    # Emoji slash cmd group
    emoji = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="emoji", description="Emoji related commands.")

    # Download app emojis
    @emoji.command(name="download")
    @check.is_dev()
    async def download_app_emojis(self, ctx: discord.ApplicationContext):
        """Downloads all emojis from the app."""
        await ctx.defer()
        emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        if not emojis:
            no_emojis_em = discord.Embed(
                description=f"{emoji.error} No emojis found in the app.", color=config.color.red
            )
            await ctx.respond(embed=no_emojis_em, ephemeral=True)
            return

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for app_emoji in emojis:
                async with self.client.http._HTTPClient__session.get(app_emoji.url) as response:
                    if response.status == 200:
                        zip_file.writestr(f"{app_emoji.name}.png", await response.read())

        zip_buffer.seek(0)
        await ctx.respond(file=discord.File(fp=zip_buffer, filename="emojis.zip"))

    def emoji_prog_embed(self, total: int, completed: int = 0) -> discord.Embed:
        """Creates an embed for emoji upload progress."""
        progress = (completed / total) * 100
        bar_length = 15
        filled_length = int(bar_length * completed // total)
        bar = f"{emoji.filled_bar * filled_length}{emoji.empty_bar * (bar_length - filled_length)}"
        return discord.Embed(
            description=f"{emoji.upload} Uploading `{completed}/{total}` emojis.\n{bar} `{progress:.2f}%`",
            color=config.color.theme,
        )

    # Upload app emojis
    @emoji.command(name="upload")
    @option("file", description="Upload emojis zip file.", type=discord.Attachment)
    @check.is_dev()
    async def upload_app_emojis(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Uploads all emojis to the app (only supports .zip files with .png emojis)."""
        await ctx.defer()
        if not file.filename.endswith(".zip"):
            error_em = discord.Embed(
                description=f"{emoji.error} Please upload a valid zip file.", color=config.color.red
            )
            await ctx.respond(embed=error_em, ephemeral=True)
            return
        zip_buffer = BytesIO()
        await file.save(zip_buffer)
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            namelist = zip_file.namelist()
            file_entries = [n for n in namelist if not n.endswith("/")]
            top_dirs = set()
            for n in namelist:
                parts = n.split("/")
                if len(parts) > 1 and parts[0]:
                    top_dirs.add(parts[0])
            if len(top_dirs) > 1:
                error_em = discord.Embed(
                    description=f"{emoji.error} Zip file contains more than one top-level directory.",
                    color=config.color.red,
                )
                await ctx.respond(embed=error_em, ephemeral=True)
                return
            if len(top_dirs) == 1:
                base_dir = list(top_dirs)[0]
                emoji_files = [f for f in file_entries if f.startswith(base_dir + "/") and f.endswith(".png")]
            else:
                emoji_files = [f for f in file_entries if "/" not in f and f.endswith(".png")]
            if not emoji_files:
                error_em = discord.Embed(
                    description=f"{emoji.error} No `.png` emoji files found in the zip.",
                    color=config.color.red,
                )
                await ctx.respond(embed=error_em, ephemeral=True)
                return
            embed = self.emoji_prog_embed(len(emoji_files))
            msg = await ctx.respond(embed=embed)
            for emoji_path in emoji_files:
                _emoji = emoji_path.split("/")[-1][:-4]
                if len(_emoji) > 32:
                    error_em = discord.Embed(
                        description=f"{emoji.error} Emoji name `{_emoji}` is too long (max 32 characters).",
                        color=config.color.red,
                    )
                    await ctx.respond(embed=error_em, ephemeral=True)
                    return
                try:
                    await self.client.create_emoji(name=_emoji, image=zip_file.read(emoji_path))
                except Exception:
                    await self.client.delete_emoji(
                        [emoji for emoji in await self.client.fetch_emojis() if emoji.name == _emoji][0]
                    )
                    await self.client.create_emoji(name=_emoji, image=zip_file.read(emoji_path))
                await msg.edit(embed=self.emoji_prog_embed(len(emoji_files), emoji_files.index(emoji_path) + 1))
        zip_buffer.close()
        upload_em = discord.Embed(
            description=f"{emoji.success} Uploaded {len(emoji_files)} emojis.",
            color=config.color.green,
        )
        await msg.edit(embed=upload_em)

    async def delete_extra_emojis_callback(
        self, view: discord.ui.View, interaction: discord.Interaction, emojis: dict[str, str]
    ):
        """Deletes extra emojis."""
        await interaction.response.defer()
        view.disable_all_items()
        await interaction.message.edit(view=view)
        for extra_emoji in emojis:
            extra_emoji = extra_emoji.strip("<>").split(":")
            em = int(extra_emoji[2])
            await self.client.delete_emoji(discord.Object(id=em))
        delete_em = discord.Embed(
            description=f"{emoji.success} Deleted extra emojis.",
            color=config.color.green,
        )
        await interaction.followup.send(embed=delete_em, ephemeral=True)

    # Check emoji zip file
    @emoji.command(name="check-zip")
    @option("file", description="Upload emojis zip file.", type=discord.Attachment)
    @check.is_dev()
    async def check_emoji_zip(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Checks the uploaded zip file for emojis."""
        await ctx.defer()
        if not file.filename.endswith(".zip"):
            error_em = discord.Embed(
                description=f"{emoji.error} Please upload a valid zip file.", color=config.color.red
            )
            await ctx.respond(embed=error_em, ephemeral=True)
            return

        zip_buffer = BytesIO()
        await file.save(zip_buffer)
        zip_buffer.seek(0)

        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            namelist = zip_file.namelist()
            # Handle both flat structure and directory structure
            file_entries = [n for n in namelist if not n.endswith("/")]
            top_dirs = set()
            for n in namelist:
                parts = n.split("/")
                if len(parts) > 1 and parts[0]:
                    top_dirs.add(parts[0])

            if len(top_dirs) == 1:
                base_dir = list(top_dirs)[0]
                emoji_files = [f for f in file_entries if f.startswith(base_dir + "/") and f.endswith(".png")]
                emoji_names = [f.split("/")[-1][:-4] for f in emoji_files]
            else:
                emoji_files = [f for f in file_entries if "/" not in f and f.endswith(".png")]
                emoji_names = [f[:-4] for f in emoji_files]

            if not emoji_files:
                error_em = discord.Embed(
                    description=f"{emoji.error} No `.png` emoji files found in the zip.",
                    color=config.color.red,
                )
                await ctx.respond(embed=error_em, ephemeral=True)
                return

            # Get expected emoji names from Emoji class
            expected_emojis = set(Emoji.get_emoji_names())
            found_emojis = set(emoji_names)

            # Find missing and extra emojis
            missing_emojis = expected_emojis - found_emojis
            extra_emojis = found_emojis - expected_emojis

            em = discord.Embed(
                title="Emoji Zip Check",
                description=f"Found `{len(emoji_files)}` emoji files in the zip.\nExpected `{len(expected_emojis)}` emojis.",
                color=config.color.theme,
            )

            if missing_emojis:
                missing_list = "\n".join([f"{emoji.bullet} `{name}`" for name in sorted(missing_emojis)])
                if len(missing_list) > 1024:
                    missing_list = missing_list[:1020] + "..."
                em.add_field(name=f"Missing Emojis (`{len(missing_emojis)}`)", value=missing_list, inline=False)

            if extra_emojis:
                extra_list = "\n".join([f"{emoji.bullet_red} `{name}`" for name in sorted(extra_emojis)])
                if len(extra_list) > 1024:
                    extra_list = extra_list[:1020] + "..."
                em.add_field(name=f"Extra Emojis (`{len(extra_emojis)}`)", value=extra_list, inline=False)

            await ctx.respond(embed=em)

        zip_buffer.close()

    # Sync app emojis
    @emoji.command(name="sync")
    @check.is_dev()
    async def sync_app_emojis(self, ctx: discord.ApplicationContext):
        """Syncs all emojis from the app."""
        await ctx.defer()
        emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        emoji_dict: dict = {}
        if not emojis:
            no_emojis_em = discord.Embed(
                description=f"{emoji.error} No emojis found in the app.", color=config.color.red
            )
            await ctx.respond(embed=no_emojis_em, ephemeral=True)
            return

        for app_emoji in emojis:
            if app_emoji.animated:
                emoji_dict[app_emoji.name] = f"<a:{app_emoji.name}:{app_emoji.id}>"
            else:
                emoji_dict[app_emoji.name] = f"<:{app_emoji.name}:{app_emoji.id}>"

        resp: dict = Emoji.create_custom_emoji_config(emoji_dict)
        sync_em = discord.Embed(
            description=f"{emoji.restart} Synced {len(emojis)} emojis.",
            color=config.color.theme,
        )

        # Add info about keys that use default emojis (no custom emoji available)
        if resp.get("default_emojis_used"):
            sync_em.add_field(
                name="Default Emojis Used",
                value="\n".join([f"{getattr(emoji, i)} `{i}`" for i in resp["default_emojis_used"]]),
                inline=False,
            )

        # Handle extra emojis
        if resp.get("extra_keys_ignored"):
            sync_em.add_field(
                name="Ignored Extra Emojis",
                value="\n".join([f"{emoji_dict.get(i, emoji.bullet)} `{i}`" for i in resp["extra_keys_ignored"]]),
                inline=False,
            )
            view = discord.ui.View(
                discord.ui.Button(
                    emoji=emoji.bin_white,
                    label="Delete Extra Emojis",
                    style=discord.ButtonStyle.grey,
                ),
                timeout=60,
                disable_on_timeout=True,
            )
            view.interaction_check = lambda i: check.author_interaction_check(ctx, i)
            view.children[0].callback = lambda i: self.delete_extra_emojis_callback(view, i, resp["extra_keys_ignored"])
            await ctx.respond(embed=sync_em, view=view)
            return
        await ctx.respond(embed=sync_em)


def setup(client: discord.Bot):
    client.add_cog(Devs(client))
