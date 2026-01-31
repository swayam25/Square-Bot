import discord
import math
import os
import sys
import zipfile
from core import Client
from core.view import DesignerView
from db.funcs.dev import add_dev, fetch_dev_ids, remove_dev
from db.funcs.guild import add_guild, remove_guild
from discord import ui
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from discord.ui import ActionRow
from io import BytesIO
from utils import check, config, temp
from utils.emoji import Emoji, emoji


class GuildContainer(ui.Container):
    def __init__(self, guilds, page=1, items_per_page=10):
        super().__init__()
        total_pages = max(1, math.ceil(len(guilds) / items_per_page))
        start = (page - 1) * items_per_page
        end = start + items_per_page
        page_guilds = guilds[start:end]
        guilds_list = "\n".join(f"`{i + 1}.` **{g.name}**: `{g.id}`" for i, g in enumerate(page_guilds, start=start))
        self.add_item(ui.TextDisplay("## Guilds List"))
        self.add_item(ui.TextDisplay(guilds_list or "No guilds found."))
        if len(guilds) > items_per_page:
            self.add_item(ui.Separator())
            self.add_item(ui.TextDisplay(f"-# Viewing Page {page}/{total_pages}"))


class GuildListView(DesignerView):
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
        row = ActionRow()
        for btn_emoji, callback in [
            (emoji.start_white, "start"),
            (emoji.previous_white, "previous"),
            (emoji.next_white, "next"),
            (emoji.end_white, "end"),
        ]:
            btn = ui.Button(emoji=btn_emoji, style=discord.ButtonStyle.grey)
            btn.callback = lambda i, action=callback: self.interaction_callback(i, action)
            row.add_item(btn)
        self.add_item(row)

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


class SyncEmojiView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client

    async def build(self) -> None:
        self.clear_items()
        emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        emoji_dict: dict = {}

        for app_emoji in emojis:
            if app_emoji.animated:
                emoji_dict[app_emoji.name] = f"<a:{app_emoji.name}:{app_emoji.id}>"
            else:
                emoji_dict[app_emoji.name] = f"<:{app_emoji.name}:{app_emoji.id}>"
        resp: dict = Emoji.create_custom_emoji_config(emoji_dict)
        default_emojis_used: list[str] = resp.get("default_emojis_used", [])
        extra_keys_ignored: list[str] = resp.get("extra_keys_ignored", [])
        view_items = [
            ui.TextDisplay(f"## Synced {len(emojis)} emojis"),
            ui.TextDisplay(
                f"{emoji.emoji} **Total Emojis**: `{len(emojis)}`\n"
                f"{emoji.bot} **Default Emojis**: `{len(default_emojis_used)}`\n"
                f"{emoji.leave} **Extra Emojis**: `{len(extra_keys_ignored)}`\n"
            ),
        ]
        if default_emojis_used:
            view_items.extend(
                [
                    ui.TextDisplay("### Default Emojis Used"),
                    ui.TextDisplay("".join(f"{getattr(emoji, i)} `{i}`\n" for i in default_emojis_used)),
                ]
            )
        if extra_keys_ignored:
            view_items.extend(
                [
                    ui.TextDisplay("### Ignored Extra Emojis"),
                    ui.TextDisplay("".join(f"{emoji_dict.get(i, emoji.bullet)} `{i}`\n" for i in extra_keys_ignored)),
                ]
            )
            extra_btn = ui.Button(
                emoji=emoji.bin_white,
                label="Delete Extra Emojis",
                style=discord.ButtonStyle.grey,
                custom_id="delete_extra_emojis_btn",
            )

            async def extra_btn_callback(i: discord.Interaction):
                await self.delete_extra_emojis_callback(i, [emoji_dict.get(e) for e in extra_keys_ignored])

            extra_btn.callback = extra_btn_callback
            self.add_item(ui.Container(*view_items))
            self.add_item(ui.ActionRow(extra_btn))
            return  # Early return to avoid re-adding view_items, button row must be at the end.
        self.add_item(ui.Container(*view_items))

    async def delete_extra_emojis_callback(self, interaction: discord.Interaction, emojis: list[str]):
        """Deletes extra emojis."""
        btn = self.get_item("delete_extra_emojis_btn")
        btn.label = "Deleting..."
        btn.emoji = emoji.loading_white
        self.disable_all_items()
        await interaction.edit(view=self)
        for e in emojis:
            obj = e.strip("<>").split(":")
            id = int(obj[-1]) if len(obj) > 1 else None
            if id:
                await self.client.delete_emoji(discord.Object(id=id))
        await self.build()
        await interaction.edit(view=self)


class Devs(commands.Cog):
    def __init__(self, client: Client):
        self.client = client

    # On start
    @commands.Cog.listener("on_ready")
    async def when_bot_gets_ready(self):
        start_log_ch = await self.client.fetch_channel(config.system_channel_id)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Logged in as **{self.client.user}** with ID `{self.client.user.id}`"),
                color=config.color.green,
            )
        )
        await start_log_ch.send(view=view)

    # On guild joined
    @commands.Cog.listener("on_guild_join")
    async def when_guild_joined(self, guild: discord.Guild):
        await add_guild(guild.id)
        join_log_ch = await self.client.fetch_channel(config.system_channel_id)
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Someone Added Me!"),
                ui.TextDisplay(
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
        view = DesignerView(
            ui.Container(
                ui.TextDisplay("## Someone Removed Me!"),
                ui.TextDisplay(
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
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Added {user.mention} to dev."),
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
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.success} Removed {user.mention} from dev"),
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
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Devs List"),
                    ui.TextDisplay(devs_list or "No devs found."),
                )
            )
        else:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} No devs found."),
                    color=config.color.red,
                )
            )
        await ctx.respond(view=view)

    # Restart
    @slash_command(guild_ids=config.owner_guild_ids, name="restart")
    @check.is_dev()
    async def restart(self, ctx: discord.ApplicationContext):
        """Restarts the bot."""
        await self.client.change_presence(
            status=discord.Status.idle,
            activity=discord.CustomActivity(name="Restarting..."),
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.loading} Restarting..."),
            )
        )
        msg = await ctx.respond(view=view)
        temp.set("restart_msg", {"channel_id": msg.channel.id, "id": (await msg.original_message()).id})
        await self.client.wait_until_ready()
        await self.client.close()
        os.system("clear")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # Reload cogs
    @slash_command(guild_ids=config.owner_guild_ids, name="reload-cogs")
    @check.is_dev()
    async def reload_cogs(self, ctx: discord.ApplicationContext):
        """Reloads the bot cogs."""
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.reload} Reloaded Cogs"),
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
        await self.client.change_presence(
            status=discord.Status.dnd,
            activity=None,
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.shutdown} Bot is now shutdown."),
            )
        )
        await ctx.respond(view=view)
        await self.client.wait_until_ready()
        await self.client.close()

    # Set status
    @slash_command(guild_ids=config.owner_guild_ids, name="status")
    @check.is_dev()
    @option("status", description="Set the bot status", choices=["Online", "Idle", "DND", "Invisible"])
    @option("activity", description="Set the bot activity", max_length=128)
    async def set_status(self, ctx: discord.ApplicationContext, status: str, activity: str = None):
        """Sets the bot status."""
        await self.client.change_presence(
            status=discord.Status[status.lower()],
            activity=discord.CustomActivity(name=activity) if activity else self.client.activity,
        )
        view = DesignerView(
            ui.Container(
                ui.TextDisplay(
                    f"{emoji.success} Status updated to `{status}`\n" + (f"```\n{activity}\n```" if activity else "")
                ),
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
            guild_list_view = DesignerView(container)
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
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I can't leave the owner guild."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
        else:
            await guild.leave()
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Left the guild **{guild.name}** with ID `{guild.id}`"),
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
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} I can't create an invite link for the owner guild"),
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
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} No emojis found in the app."),
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
                        if app_emoji.animated:
                            zip_file.writestr(f"{app_emoji.name}.gif", await response.read())
                        else:
                            zip_file.writestr(f"{app_emoji.name}.png", await response.read())

        zip_buffer.seek(0)
        await ctx.respond(file=discord.File(fp=zip_buffer, filename="emojis.zip"))

    def emoji_prog_view(self, total: int, completed: int = 0) -> DesignerView:
        progress = (completed / total) * 100
        bar_length = 15
        filled_length = int(bar_length * completed // total)
        bar = f"{emoji.filled_bar * filled_length}{emoji.empty_bar * (bar_length - filled_length)}"
        return DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.loading} Uploading `{completed}/{total}` emojis.\n{bar} `{progress:.2f}%`"),
            )
        )

    # Upload app emojis
    @emoji.command(name="upload")
    @check.is_dev()
    @option("file", description="Upload emojis zip file or single png or gif file.", type=discord.Attachment)
    async def upload_app_emojis(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Uploads emojis to the app from a .zip file or single .png/.gif file."""
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
                    view = DesignerView(
                        ui.Container(
                            ui.TextDisplay(f"{emoji.error} Zip file contains more than one top-level directory."),
                            color=config.color.red,
                        )
                    )
                    await ctx.respond(view=view, ephemeral=True)
                    return
                if len(top_dirs) == 1:
                    base_dir = list(top_dirs)[0]
                    emoji_files = [
                        f for f in file_entries if f.startswith(base_dir + "/") and f.endswith((".png", ".gif"))
                    ]
                else:
                    emoji_files = [f for f in file_entries if "/" not in f and f.endswith((".png", ".gif"))]
                if not emoji_files:
                    view = DesignerView(
                        ui.Container(
                            ui.TextDisplay(f"{emoji.error} No `.png` or `.gif` emoji files found in the zip."),
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
                        view = DesignerView(
                            ui.Container(
                                ui.TextDisplay(f"{emoji.error} Emoji name `{_emoji}` is too long (max 32 characters)."),
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
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.success} Uploaded {len(emoji_files)} emojis."),
                    color=config.color.green,
                )
            )
            await msg.edit(view=view)
        elif file.filename.endswith((".png", ".gif")):
            # Handle single PNG or GIF file upload
            if len(file.filename[:-4]) > 32:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(
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
                uploaded_emoji = await self.client.create_emoji(name=file.filename[:-4], image=png_buffer.read())
                emoji_md = (
                    f"<a:{uploaded_emoji.name}:{uploaded_emoji.id}>"
                    if uploaded_emoji.animated
                    else f"<:{uploaded_emoji.name}:{uploaded_emoji.id}>"
                )
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.success} Uploaded emoji {emoji_md} `{file.filename[:-4]}`."),
                        color=config.color.green,
                    )
                )
                await ctx.respond(view=view)
            except Exception as e:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.error} Failed to upload emoji `{file.filename[:-4]}`.\n{e}"),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
            png_buffer.close()
        else:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Please upload a valid zip file or a single .png/.gif file."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)

    # Check emoji zip file
    @emoji.command(name="check-zip")
    @check.is_dev()
    @option("file", description="Upload emojis zip file.", type=discord.Attachment)
    async def check_emoji_zip(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Checks the uploaded zip file for emojis."""
        await ctx.defer()
        if not file.filename.endswith(".zip"):
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} Please upload a valid zip file."),
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
                emoji_files = [f for f in file_entries if f.startswith(base_dir + "/") and f.endswith((".png", ".gif"))]
                emoji_names = [f.split("/")[-1][:-4] for f in emoji_files]
            else:
                emoji_files = [f for f in file_entries if "/" not in f and f.endswith((".png", ".gif"))]
                emoji_names = [f[:-4] for f in emoji_files]

            if not emoji_files:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay(f"{emoji.error} No `.png` emoji files found in the zip."),
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
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Emoji Zip Check"),
                    ui.TextDisplay(
                        f"Found `{len(emoji_files)}` emoji files in the zip. Expected `{len(expected_emojis)}` emojis."
                    ),
                    ui.TextDisplay(
                        ("### Missing Emojis\n" + missing_list)
                        if missing_list
                        else f"{emoji.success} No missing emojis."
                    ),
                    ui.TextDisplay(
                        ("### Extra Emojis\n" + extra_list) if extra_list else f"{emoji.success} No extra emojis."
                    ),
                    color=config.color.green if not missing_emojis and not extra_emojis else config.color.red,
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
        if not emojis:
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.error} No emojis found in the app."),
                    color=config.color.red,
                )
            )
            await ctx.respond(view=view, ephemeral=True)
            return
        else:
            view = SyncEmojiView(self.client, ctx)
            await view.build()
            await ctx.respond(view=view)


def setup(client: Client):
    client.add_cog(Devs(client))
