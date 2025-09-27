import discord
import discord.ui
import math
import os
import sys
import zipfile
from core import Client
from core.view import View
from db.funcs.dev import add_dev, fetch_dev_ids, remove_dev
from db.funcs.guild import add_guild, remove_guild
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from io import BytesIO
from utils import check, config
from utils.emoji import Emoji, emoji


class GuildContainer(discord.ui.Container):
    def __init__(self, guilds, page=1, items_per_page=10):
        super().__init__()
        total_pages = max(1, math.ceil(len(guilds) / items_per_page))
        start = (page - 1) * items_per_page
        end = start + items_per_page
        page_guilds = guilds[start:end]
        guilds_list = "\n".join(f"`{i + 1}.` **{g.name}**: `{g.id}`" for i, g in enumerate(page_guilds, start=start))
        self.add_item(discord.ui.TextDisplay("## Guilds List"))
        self.add_item(discord.ui.TextDisplay(guilds_list or "No guilds found."))
        if len(guilds) > items_per_page:
            self.add_item(discord.ui.Separator())
            self.add_item(discord.ui.TextDisplay(f"-# Viewing Page {page}/{total_pages}"))


class GuildListView(View):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, page: int = 1):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.page = page
        self.items_per_page = 10
        self.build()

    def build(self) -> None:
        self.clear_items()
        guilds = self.client.guilds
        self.add_item(GuildContainer(guilds, page=self.page, items_per_page=self.items_per_page))
        for btn_emoji, callback in [
            (emoji.start_white, "start"),
            (emoji.previous_white, "previous"),
            (emoji.next_white, "next"),
            (emoji.end_white, "end"),
        ]:
            btn = discord.ui.Button(emoji=btn_emoji, style=discord.ButtonStyle.grey)
            btn.callback = lambda i, action=callback: self.interaction_callback(i, action)
            self.add_item(btn)

    async def interaction_callback(self, interaction: discord.Interaction, action: str):
        guilds = self.client.guilds
        total_pages = math.ceil(len(guilds) / self.items_per_page)
        if action == "start":
            self.page = 1
        elif action == "previous":
            self.page = total_pages if self.page <= 1 else self.page - 1
        elif action == "next":
            self.page = 1 if self.page >= total_pages else self.page + 1
        elif action == "end":
            self.page = total_pages
        self.build()
        await interaction.edit(view=self)


class Devs(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # On start
    @commands.Cog.listener("on_ready")
    async def when_bot_gets_ready(self):
        start_log_ch = await self.client.fetch_channel(config.system_channel_id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    f"{emoji.success} Logged in as **{self.client.user}** with ID `{self.client.user.id}`"
                ),
                color=config.color.green,
            )
        )
        await start_log_ch.send(view=view)

    # On guild joined
    @commands.Cog.listener("on_guild_join")
    async def when_guild_joined(self, guild: discord.Guild):
        await add_guild(guild.id)
        join_log_ch = await self.client.fetch_channel(config.system_channel_id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay("## Someone Added Me!"),
                discord.ui.TextDisplay(
                    f"{emoji.server} **Name**: {guild.name}\n"
                    f"{emoji.id} **ID**: `{guild.id}`\n"
                    f"{emoji.members} **Total Members**: `{guild.member_count} ({len([m for m in guild.members if not m.bot])} Humans | {len([m for m in guild.members if m.bot])} Bots)`"
                ),
            )
        )
        await join_log_ch.send(view=view)

    # On guild leave
    @commands.Cog.listener("on_guild_remove")
    async def when_removed_from_guild(self, guild: discord.Guild):
        await remove_guild(guild.id)
        leave_log_ch = await self.client.fetch_channel(config.system_channel_id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay("## Someone Removed Me!"),
                discord.ui.TextDisplay(
                    f"{emoji.server_red} **Name**: {guild.name}\n"
                    f"{emoji.id_red} **ID**: `{guild.id}`\n"
                    f"{emoji.members_red} **Total Members**: `{guild.member_count} ({len([m for m in guild.members if not m.bot])} Humans | {len([m for m in guild.members if m.bot])} Bots)`"
                ),
                color=config.color.red,
            )
        )
        await leave_log_ch.send(view=view)

    # Dev slash cmd group
    dev = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="dev", description="Developer related commands.")

    # Add dev
    @dev.command(name="add")
    @check.is_owner()
    @option("user", description="Mention the user whom you want to add to dev")
    async def add_dev(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Adds a bot dev."""
        await add_dev(user.id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Added {user.mention} to dev."),
                color=config.color.green,
            ),
        )
        await ctx.respond(view=view)

    # Remove dev
    @dev.command(name="remove")
    @check.is_owner()
    @option("user", description="Mention the user whom you want to remove from dev")
    async def remove_dev(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Removes a bot dev."""
        await remove_dev(user.id)
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Removed {user.mention} from dev"),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

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
        if devs_list:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay("## Devs List"),
                    discord.ui.TextDisplay(devs_list or "No devs found."),
                )
            )
        else:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} No devs found."),
                    color=config.color.red,
                )
            )
        await ctx.respond(view=view)

    # Restart
    @slash_command(guild_ids=config.owner_guild_ids, name="restart")
    @check.is_dev()
    async def restart(self, ctx: discord.ApplicationContext):
        """Restarts the bot."""
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.restart} Restarting..."),
            )
        )
        await ctx.respond(view=view)
        await self.client.wait_until_ready()
        await self.client.close()
        os.system("clear")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # Reload cogs
    @slash_command(guild_ids=config.owner_guild_ids, name="reload-cogs")
    @check.is_dev()
    async def reload_cogs(self, ctx: discord.ApplicationContext):
        """Reloads the bot cogs."""
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.restart} Reloaded Cogs."),
            )
        )
        await ctx.respond(view=view, ephemeral=True, delete_after=2)
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                self.client.reload_extension(f"cogs.{filename[:-3]}")

    # Shutdown
    @slash_command(guild_ids=config.owner_guild_ids, name="shutdown")
    @check.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext):
        """Shutdowns the bot."""
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.shutdown} Bot shutdown."),
            )
        )
        await ctx.respond(view=view)
        await self.client.wait_until_ready()
        await self.client.close()

    # Set status
    @slash_command(guild_ids=config.owner_guild_ids, name="status")
    @check.is_dev()
    @option("type", description="Choose bot status type", choices=["Game", "Streaming", "Listening", "Watching"])
    @option("status", description="Enter new status of bot")
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
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Status changed to **{type}** as `{status}`"),
                color=config.color.green,
            )
        )
        await ctx.respond(view=view)

    # Guild slash cmd group
    guild = SlashCommandGroup(guild_ids=config.owner_guild_ids, name="guild", description="Guild related commands.")

    # List guild
    @guild.command(name="list")
    @check.is_owner()
    async def list_guilds(self, ctx: discord.ApplicationContext):
        """Shows all guilds."""
        guild_list_view = None
        if len(self.client.guilds) > 10:
            guild_list_view = GuildListView(self.client, ctx)
        else:
            guilds = self.client.guilds
            container = GuildContainer(guilds)
            guild_list_view = View(container)
        await ctx.respond(view=guild_list_view)

    # Leave guild
    @guild.command(name="leave")
    @check.is_owner()
    @option(
        "guild",
        description="Enter the guild name",
        autocomplete=lambda self, ctx: [
            guild.name for guild in self.client.guilds if not any(guild.id == g for g in config.owner_guild_ids)
        ],
    )
    async def leave_guild(self, ctx: discord.ApplicationContext, guild: discord.Guild):
        """Leaves a guild."""
        if any(guild.id == g for g in config.owner_guild_ids):
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} I can't leave the owner guild."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await guild.leave()
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.success} Left the guild **{guild.name}** with ID `{guild.id}`"),
                )
            )
            await ctx.respond(view=view)

    # Guild invite
    @guild.command(name="invite")
    @check.is_owner()
    @option(
        "guild",
        description="Enter the guild name",
        autocomplete=lambda self, ctx: [
            guild.name for guild in self.client.guilds if not any(guild.id == g for g in config.owner_guild_ids)
        ],
    )
    async def guild_inv(self, ctx: discord.ApplicationContext, guild: discord.Guild):
        """Creates an invite link for the guild."""
        if any(guild.id == g for g in config.owner_guild_ids):
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} I can't create an invite link for the owner guild"),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
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
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} No emojis found in the app."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for app_emoji in emojis:
                async with self.client.http._HTTPClient__session.get(app_emoji.url) as response:
                    if response.status == 200:
                        zip_file.writestr(f"{app_emoji.name}.png", await response.read())

        zip_buffer.seek(0)
        await ctx.respond(file=discord.File(fp=zip_buffer, filename="emojis.zip"))

    def emoji_prog_view(self, total: int, completed: int = 0) -> View:
        progress = (completed / total) * 100
        bar_length = 15
        filled_length = int(bar_length * completed // total)
        bar = f"{emoji.filled_bar * filled_length}{emoji.empty_bar * (bar_length - filled_length)}"
        return View(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    f"{emoji.upload} Uploading `{completed}/{total}` emojis.\n{bar} `{progress:.2f}%`"
                ),
            )
        )

    # Upload app emojis
    @emoji.command(name="upload")
    @check.is_dev()
    @option("file", description="Upload emojis zip file or single png file.", type=discord.Attachment)
    async def upload_app_emojis(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Uploads all emojis to the app (supports .zip files with .png emojis or a single .png file)."""
        await ctx.defer()
        if file.filename.endswith(".zip"):
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
                    view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay(
                                f"{emoji.error} Zip file contains more than one top-level directory."
                            ),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view, ephemeral=True)
                    return
                if len(top_dirs) == 1:
                    base_dir = list(top_dirs)[0]
                    emoji_files = [f for f in file_entries if f.startswith(base_dir + "/") and f.endswith(".png")]
                else:
                    emoji_files = [f for f in file_entries if "/" not in f and f.endswith(".png")]
                if not emoji_files:
                    view = View(
                        discord.ui.Container(
                            discord.ui.TextDisplay(f"{emoji.error} No `.png` emoji files found in the zip."),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view, ephemeral=True)
                    return
                view = self.emoji_prog_view(len(emoji_files))
                msg = await ctx.respond(view=view)
                for emoji_path in emoji_files:
                    _emoji = emoji_path.split("/")[-1][:-4]
                    if len(_emoji) > 32:
                        view = View(
                            discord.ui.Container(
                                discord.ui.TextDisplay(
                                    f"{emoji.error} Emoji name `{_emoji}` is too long (max 32 characters)."
                                ),
                                color=config.color.red,
                            )
                        )
                        await ctx.respond(view=view, ephemeral=True)
                        return
                    try:
                        await self.client.create_emoji(name=_emoji, image=zip_file.read(emoji_path))
                    except Exception:
                        await self.client.delete_emoji(
                            [emoji for emoji in await self.client.fetch_emojis() if emoji.name == _emoji][0]
                        )
                        await self.client.create_emoji(name=_emoji, image=zip_file.read(emoji_path))
                    await msg.edit(view=self.emoji_prog_view(len(emoji_files), emoji_files.index(emoji_path) + 1))
            zip_buffer.close()
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.success} Uploaded {len(emoji_files)} emojis."),
                    color=config.color.green,
                )
            )
            await msg.edit(view=view)
        elif file.filename.endswith(".png"):
            # Handle single PNG file upload
            if len(file.filename[:-4]) > 32:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay(
                            f"{emoji.error} Emoji name `{file.filename[:-4]}` is too long (max 32 characters)."
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
                return
            png_buffer = BytesIO()
            await file.save(png_buffer)
            png_buffer.seek(0)
            try:
                await self.client.create_emoji(name=file.filename[:-4], image=png_buffer.read())
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay(f"{emoji.success} Uploaded emoji `{file.filename[:-4]}`."),
                        color=config.color.green,
                    )
                )
                await ctx.respond(view=view)
            except Exception as e:
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay(f"{emoji.error} Failed to upload emoji `{file.filename[:-4]}`.\n{e}"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
            png_buffer.close()
        else:
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} Please upload a valid zip file or a single png file."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    async def delete_extra_emojis_callback(self, view: View, interaction: discord.Interaction, emojis: list[str]):
        """Deletes extra emojis."""
        view.disable_all_items()
        await interaction.edit(view=view)
        for e in emojis:
            obj = e.strip("<>").split(":")
            id = int(obj[-1]) if len(obj) > 1 else None
            if id:
                await self.client.delete_emoji(discord.Object(id=id))
        view = View(
            discord.ui.Container(
                discord.ui.TextDisplay(f"{emoji.success} Deleted extra emojis."),
                color=config.color.green,
            )
        )
        await interaction.followup.send(view=view, ephemeral=True)

    # Check emoji zip file
    @emoji.command(name="check-zip")
    @check.is_dev()
    @option("file", description="Upload emojis zip file.", type=discord.Attachment)
    async def check_emoji_zip(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Checks the uploaded zip file for emojis."""
        await ctx.defer()
        if not file.filename.endswith(".zip"):
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} Please upload a valid zip file."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
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
                view = View(
                    discord.ui.Container(
                        discord.ui.TextDisplay(f"{emoji.error} No `.png` emoji files found in the zip."),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
                return

            # Get expected emoji names from Emoji class
            expected_emojis = set(Emoji.get_emoji_names())
            found_emojis = set(emoji_names)

            # Find missing and extra emojis
            missing_emojis = expected_emojis - found_emojis
            extra_emojis = found_emojis - expected_emojis

            missing_list = "\n".join([f"{emoji.bullet} `{name}`" for name in sorted(missing_emojis)])
            extra_list = "\n".join([f"{emoji.bullet_red} `{name}`" for name in sorted(extra_emojis)])
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay("## Emoji Zip Check"),
                    discord.ui.TextDisplay(
                        f"Found `{len(emoji_files)}` emoji files in the zip. Expected `{len(expected_emojis)}` emojis."
                    ),
                    discord.ui.TextDisplay(missing_list if missing_list else "No missing emojis."),
                    discord.ui.TextDisplay(extra_list if extra_list else "No extra emojis."),
                )
            )
            await ctx.respond(view=view)

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
            view = View(
                discord.ui.Container(
                    discord.ui.TextDisplay(f"{emoji.error} No emojis found in the app."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return

        for app_emoji in emojis:
            if app_emoji.animated:
                emoji_dict[app_emoji.name] = f"<a:{app_emoji.name}:{app_emoji.id}>"
            else:
                emoji_dict[app_emoji.name] = f"<:{app_emoji.name}:{app_emoji.id}>"

        resp: dict = Emoji.create_custom_emoji_config(emoji_dict)
        default_emojis_used = resp.get("default_emojis_used", [])
        extra_keys_ignored = resp.get("extra_keys_ignored", [])
        view_items = [
            discord.ui.TextDisplay(f"{emoji.restart} Synced {len(emojis)} emojis."),
        ]
        if default_emojis_used:
            view_items.append(discord.ui.TextDisplay("**Default Emojis Used**"))
            view_items.append(discord.ui.Separator())
            view_items.extend([discord.ui.TextDisplay(f"{getattr(emoji, i)} `{i}`") for i in default_emojis_used])
        if extra_keys_ignored:
            view_items.append(discord.ui.TextDisplay("**Ignored Extra Emojis**"))
            view_items.append(discord.ui.Separator())
            view_items.extend(
                [discord.ui.TextDisplay(f"{emoji_dict.get(i, emoji.bullet)} `{i}`") for i in extra_keys_ignored]
            )
            view = View(
                discord.ui.Container(*view_items),
                discord.ui.Button(
                    emoji=emoji.bin_white,
                    label="Delete Extra Emojis",
                    style=discord.ButtonStyle.grey,
                ),
                ctx=ctx,
                check_author_interaction=True,
            )
            view.children[-1].callback = lambda i: self.delete_extra_emojis_callback(
                view, i, [emoji_dict.get(e) for e in extra_keys_ignored]
            )
            await ctx.respond(view=view)
            return
        view = View(discord.ui.Container(*view_items))
        await ctx.respond(view=view)


def setup(client: Client):
    client.add_cog(Devs(client))
