import asyncio
import discord
import hashlib
import json
import os
import zipfile
from discord import ui
from discord.commands import SlashCommandGroup, option
from io import BytesIO
from square.core import Client
from square.core.view import DesignerView, error_view, show_loading, success_view
from square.utils import check, config
from square.utils.emoji import create_custom_emoji_config, emoji, get_emoji_names, reload_emoji, update_emoji

upload_cache_path = "./.cache/emoji_uploads.json"


def _load_upload_cache() -> dict[str, dict]:
    """What each emoji was last uploaded from: `{name: {"id": emoji ID, "sha256": image hash}}`."""
    try:
        with open(upload_cache_path, encoding="utf8") as cache_file:
            return dict(json.load(cache_file))
    except FileNotFoundError, json.JSONDecodeError:
        return {}


def _save_upload_cache(uploads: dict[str, dict]) -> None:
    os.makedirs(os.path.dirname(upload_cache_path), exist_ok=True)
    with open(upload_cache_path, "w", encoding="utf8") as cache_file:
        json.dump(uploads, cache_file, indent=4)


class SyncEmojiView(DesignerView):
    def __init__(self, client: Client, ctx: discord.ApplicationContext, unchanged: int = 0):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.client = client
        self.unchanged = unchanged

    async def build(self) -> None:
        self.clear_items()
        emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        emoji_dict: dict = {}

        for app_emoji in emojis:
            if app_emoji.animated:
                emoji_dict[app_emoji.name] = f"<a:{app_emoji.name}:{app_emoji.id}>"
            else:
                emoji_dict[app_emoji.name] = f"<:{app_emoji.name}:{app_emoji.id}>"
        resp: dict = create_custom_emoji_config(emoji_dict)
        reload_emoji()
        default_emojis_used: list[str] = resp.get("default_emojis_used", [])
        extra_keys_ignored: list[str] = resp.get("extra_keys_ignored", [])

        color = config.color.orange if extra_keys_ignored else None
        view_items = [
            ui.TextDisplay(f"## Synced {len(emojis)} emojis"),
            ui.TextDisplay(
                f"{emoji.bullet} **Total Emojis**: `{len(emojis)}`\n"
                + (f"{emoji.bullet} **Unchanged, Skipped**: `{self.unchanged}`\n" if self.unchanged else "")
                + f"{emoji.bullet} **Default Emojis**: `{len(default_emojis_used)}`\n"
                f"{emoji.bullet} **Extra Emojis**: `{len(extra_keys_ignored)}`\n"
            ),
        ]
        if default_emojis_used:
            view_items.extend(
                [
                    ui.Separator(),
                    ui.TextDisplay("### Default Emojis Used"),
                    ui.TextDisplay("".join(f"{getattr(emoji, i)} `{i}`\n" for i in default_emojis_used)),
                ]
            )
        if extra_keys_ignored:
            view_items.extend(
                [
                    ui.Separator(),
                    ui.TextDisplay("### Extra Emojis"),
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
            self.add_item(ui.Container(*view_items, **({"color": color} if color else {})))
            self.add_item(ui.ActionRow(extra_btn))
            return  # Early return to avoid re-adding view_items, button row must be at the end.
        self.add_item(ui.Container(*view_items, **({"color": color} if color else {})))

    async def delete_extra_emojis_callback(self, interaction: discord.Interaction, emojis: list[str]):
        """Deletes extra emojis."""
        if not await show_loading(self, interaction, "Deleting..."):
            return
        for e in emojis:
            obj = e.strip("<>").split(":")
            id = int(obj[-1]) if len(obj) > 1 else None
            if id:
                await self.client.delete_emoji(discord.Object(id=id))
        await self.build()
        await interaction.edit(view=self)


class Emojis:
    """The `/emoji` command group: upload, sync, check and download app emojis."""

    client: Client

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
            view = error_view("No emojis found in the app.")
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
        progress = (completed / total) * 100 if total else 100
        bar_length = 15
        filled_length = int(bar_length * completed // total) if total else bar_length
        bar = f"{str(emoji.filled_bar) * filled_length}{str(emoji.empty_bar) * (bar_length - filled_length)}"
        return DesignerView(
            ui.Container(
                ui.TextDisplay(f"{emoji.loading} Uploading `{completed}/{total}` emojis.\n{bar} `{progress:.2f}%`"),
            )
        )

    async def _silent_sync(self) -> None:
        """Fetch current app emojis, write the config, and refresh the in-memory emoji singleton."""
        app_emojis: list[discord.AppEmoji] = await self.client.fetch_emojis()
        emoji_dict: dict = {
            e.name: (f"<a:{e.name}:{e.id}>" if e.animated else f"<:{e.name}:{e.id}>") for e in app_emojis
        }
        create_custom_emoji_config(emoji_dict)
        reload_emoji()

    async def _sync_emoji_view(self, ctx: discord.ApplicationContext, unchanged: int = 0) -> SyncEmojiView:
        """Runs a full emoji sync and returns the summary view with the delete extra emojis button."""
        view = SyncEmojiView(self.client, ctx, unchanged)
        await view.build()
        return view

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
                    view = error_view("Zip file contains more than one top-level directory.")
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
                    view = error_view("No `.png` or `.gif` emoji files found in the zip.")
                    await ctx.respond(view=view, ephemeral=True)
                    return
                emoji_images: dict[str, bytes] = {}
                for emoji_path in emoji_files:
                    _emoji = emoji_path.split("/")[-1][:-4]
                    if len(_emoji) > 32:
                        view = error_view(f"Emoji name `{_emoji}` is too long (max 32 characters).")
                        await ctx.respond(view=view, ephemeral=True)
                        return
                    emoji_images[_emoji] = zip_file.read(emoji_path)
            zip_buffer.close()

            existing = {e.name: e for e in await self.client.fetch_emojis()}
            uploads = _load_upload_cache()
            hashes = {name: hashlib.sha256(image).hexdigest() for name, image in emoji_images.items()}
            # The ID check re-uploads an emoji replaced or deleted outside this command, whatever its hash says
            changed = {
                name: image
                for name, image in emoji_images.items()
                if name not in existing or uploads.get(name, {}) != {"id": existing[name].id, "sha256": hashes[name]}
            }
            unchanged = len(emoji_images) - len(changed)

            msg = await ctx.respond(view=self.emoji_prog_view(len(changed)))

            # py-cord runs one request per route at a time, so more than one delete and one create in flight gains
            # nothing. It would only delete emojis earlier, leaving them missing for longer.
            semaphore = asyncio.Semaphore(2)
            completed = 0
            failed: dict[str, str] = {}

            async def upload_one(name: str, image: bytes) -> None:
                nonlocal completed
                async with semaphore:
                    try:
                        if name in existing:
                            await self.client.delete_emoji(existing[name])
                        uploaded = await self.client.create_emoji(name=name, image=image)
                        uploads[name] = {"id": uploaded.id, "sha256": hashes[name]}
                        # Patch the singleton immediately so progress edits never render a deleted emoji ID
                        update_emoji(
                            uploaded.name,
                            f"<a:{uploaded.name}:{uploaded.id}>"
                            if uploaded.animated
                            else f"<:{uploaded.name}:{uploaded.id}>",
                        )
                    except Exception as e:
                        failed[name] = str(e)
                    finally:
                        completed += 1

            uploading = asyncio.gather(*(upload_one(name, image) for name, image in changed.items()))
            last_shown = 0
            while not uploading.done():
                if completed != last_shown:
                    last_shown = completed
                    await msg.edit(view=self.emoji_prog_view(len(changed), completed))
                await asyncio.sleep(1)
            await uploading
            _save_upload_cache(uploads)

            view = DesignerView(
                ui.Container(
                    ui.TextDisplay(f"{emoji.loading} Uploaded {len(changed) - len(failed)} emojis. *Syncing...*"),
                )
            )
            await msg.edit(view=view)
            await msg.edit(view=await self._sync_emoji_view(ctx, unchanged))
            if failed:
                view = DesignerView(
                    ui.Container(
                        ui.TextDisplay("### Failed Emojis"),
                        ui.TextDisplay(
                            "".join(f"{emoji.bullet_red} `{name}`: {err}\n" for name, err in failed.items())
                        ),
                        color=config.color.red,
                    )
                )
                await ctx.respond(view=view, ephemeral=True)
        elif file.filename.endswith((".png", ".gif")):
            # Handle single PNG or GIF file upload
            if len(file.filename[:-4]) > 32:
                view = error_view(f"Emoji name `{file.filename[:-4]}` is too long (max 32 characters).")
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
                await self._silent_sync()
                view = success_view(f"Uploaded emoji {emoji_md} `{file.filename[:-4]}`.")
                await ctx.respond(view=view)
            except Exception as e:
                view = error_view(f"Failed to upload emoji `{file.filename[:-4]}`.\n{e}")
                await ctx.respond(view=view, ephemeral=True)
            png_buffer.close()
        else:
            view = error_view("Please upload a valid zip file or a single `.png`/`.gif` file.")
            await ctx.respond(view=view, ephemeral=True)

    # Check emoji zip file
    @emoji.command(name="check-zip")
    @check.is_dev()
    @option("file", description="Upload emojis zip file.", type=discord.Attachment)
    async def check_emoji_zip(self, ctx: discord.ApplicationContext, file: discord.Attachment):
        """Checks the uploaded zip file for emojis."""
        await ctx.defer()
        if not file.filename.endswith(".zip"):
            view = error_view("Please upload a valid zip file.")
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
                view = error_view("No `.png` emoji files found in the zip.")
                await ctx.respond(view=view, ephemeral=True)
                return

            expected_emojis = set(get_emoji_names())
            found_emojis = set(emoji_names)
            missing_emojis = expected_emojis - found_emojis
            extra_emojis = found_emojis - expected_emojis

            missing_list = "\n".join([f"{emoji.bullet} `{name}`" for name in sorted(missing_emojis)])
            extra_list = "\n".join([f"{emoji.bullet_red} `{name}`" for name in sorted(extra_emojis)])

            if missing_emojis:
                color = config.color.red
            elif extra_emojis:
                color = config.color.orange
            else:
                color = config.color.green
            view = DesignerView(
                ui.Container(
                    ui.TextDisplay("## Emoji Zip Check"),
                    ui.TextDisplay(
                        f"Found `{len(emoji_files)}` emoji files in the zip. Expected `{len(expected_emojis)}` emojis."
                    ),
                    ui.Separator(),
                    ui.TextDisplay(
                        ("### Missing Emojis\n" + missing_list)
                        if missing_list
                        else f"{emoji.success} No missing emojis."
                    ),
                    ui.Separator(),
                    ui.TextDisplay(
                        ("### Extra Emojis\n" + extra_list) if extra_list else f"{emoji.success} No extra emojis."
                    ),
                    color=color,
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
            view = error_view("No emojis found in the app.")
            await ctx.respond(view=view, ephemeral=True)
            return
        else:
            await ctx.respond(view=await self._sync_emoji_view(ctx))
