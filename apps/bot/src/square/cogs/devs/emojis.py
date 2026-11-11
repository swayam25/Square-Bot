import asyncio
import contextlib
import discord
import hashlib
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from discord import ui
from discord.commands import slash_command
from pathlib import Path
from square.core import Client
from square.core.view import DesignerView, button, show_loading
from square.utils import check, config
from square.utils.emoji import (
    EMOJI_DIR,
    create_custom_emoji_config,
    emoji,
    get_emoji_names,
    reload_emoji,
    update_emoji,
)

# Discord re-encodes emojis, so its copy can't show whether a file changed. The hash of the uploaded file can.
UPLOADS = Path(".cache/emoji_uploads.json")
_NAME = re.compile(r"[A-Za-z0-9_]{2,32}")
_MAX_BYTES = 256 * 1024
_NAMES_SHOWN = 12


def _markdown(app_emoji: discord.AppEmoji) -> str:
    return f"<{'a' if app_emoji.animated else ''}:{app_emoji.name}:{app_emoji.id}>"


def _names(names: Iterable[str]) -> str:
    names = sorted(names)
    shown = ", ".join(f"`{name}`" for name in names[:_NAMES_SHOWN])
    return shown + (f" +{len(names) - _NAMES_SHOWN} more" if len(names) > _NAMES_SHOWN else "")


@dataclass(slots=True)
class Snapshot:
    """`emojis/` next to the app's emojis. What's out of sync is worked out from these, without more requests."""

    files: dict[str, bytes]
    hashes: dict[str, str]
    skipped: dict[str, str]
    remote: dict[str, discord.AppEmoji]
    uploads: dict[str, dict]

    @property
    def new(self) -> list[str]:
        return [name for name in self.files if name not in self.remote]

    @property
    def edited(self) -> list[str]:
        return [
            name
            for name in self.files
            if name in self.remote
            and self.uploads.get(name) != {"id": self.remote[name].id, "sha256": self.hashes[name]}
        ]

    @property
    def removed(self) -> list[discord.AppEmoji]:
        # A skipped file keeps its emoji
        return [
            app_emoji for name, app_emoji in self.remote.items() if name not in self.files and name not in self.skipped
        ]

    @property
    def pending(self) -> bool:
        # No files at all means a missing folder, not "delete every emoji"
        return bool(self.files) and bool(self.new or self.edited or self.removed)


def _read_assets() -> tuple[dict[str, bytes], dict[str, str], dict[str, str], dict[str, dict]]:
    """The emoji files with their hashes, the ones Discord would refuse and why, and the upload record."""
    files: dict[str, bytes] = {}
    skipped: dict[str, str] = {}
    for path in sorted(EMOJI_DIR.iterdir()):
        if path.suffix not in (".png", ".gif"):
            continue
        if not _NAME.fullmatch(path.stem):
            skipped[path.stem] = "2-32 letters, digits or underscores"
        elif path.stem in files:
            skipped[path.stem] = "both a .png and a .gif"
        elif path.stat().st_size > _MAX_BYTES:
            skipped[path.stem] = "over 256 KB"
        else:
            files[path.stem] = path.read_bytes()
    try:
        uploads = dict(json.loads(UPLOADS.read_text()))
    except FileNotFoundError, json.JSONDecodeError:
        uploads = {}
    return files, {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}, skipped, uploads


async def scan(client: Client) -> Snapshot:
    (files, hashes, skipped, uploads), remote = await asyncio.gather(
        asyncio.to_thread(_read_assets), client.fetch_emojis()
    )
    return Snapshot(files, hashes, skipped, {app_emoji.name: app_emoji for app_emoji in remote}, uploads)


async def apply(client: Client, snap: Snapshot, step: Callable[[], None]) -> dict[str, str]:
    """
    Makes the app's emojis match the files, updating `snap` as it goes, then applies them to the bot.

    Returns:
        dict[str, str]: The emojis that failed, with Discord's reason.
    """
    failed: dict[str, str] = {}
    # py-cord sends one request per route at a time, so more than a delete and a create in flight isn't faster
    slots = asyncio.Semaphore(2)

    async def delete(app_emoji: discord.AppEmoji) -> None:
        async with slots:
            try:
                update_emoji(app_emoji.name, None)
                await client.delete_emoji(app_emoji)
                del snap.remote[app_emoji.name]
            except discord.HTTPException as exc:
                failed[app_emoji.name] = exc.text or str(exc)
            step()

    async def upload(name: str) -> None:
        async with slots:
            try:
                if old := snap.remote.pop(name, None):
                    await client.delete_emoji(old)
                created = await client.create_emoji(name=name, image=snap.files[name])
                update_emoji(name, _markdown(created))
                snap.remote[name] = created
                snap.uploads[name] = {"id": created.id, "sha256": snap.hashes[name]}
            except discord.HTTPException as exc:
                failed[name] = exc.text or str(exc)
            step()

    await asyncio.gather(*map(delete, snap.removed), *map(upload, snap.new + snap.edited))
    snap.uploads = {name: record for name, record in snap.uploads.items() if name in snap.remote}
    UPLOADS.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(UPLOADS.write_text, json.dumps(snap.uploads, indent=4))
    create_custom_emoji_config({name: _markdown(app_emoji) for name, app_emoji in snap.remote.items()})
    reload_emoji()
    return failed


class EmojiPanel(DesignerView):
    """What a sync would change, the files that need attention, and the buttons to sync or check again."""

    def __init__(self, ctx: discord.ApplicationContext, client: Client, snap: Snapshot):
        super().__init__(ctx=ctx, check_author_interaction=True, timeout=600)
        self.bot = client  # `client` is taken by py-cord's view
        self.snap = snap
        self.report: str | None = None
        self.render()

    def render(self, syncing: str | None = None) -> None:
        """Draws the panel. `syncing` is the progress shown on the Sync button while a sync runs."""
        self.clear_items()
        snap, known = self.snap, set(get_emoji_names())
        changes = (
            ("New", snap.new),
            ("Edited", snap.edited),
            ("Removed", [app_emoji.name for app_emoji in snap.removed]),
        )
        issues = (
            ("No file", [name for name in known if name not in snap.files and name not in snap.skipped]),
            ("Not in code", [name for name in snap.files if name not in known]),
        )
        items: list[ui.Item] = [ui.TextDisplay("## Emojis")]
        if self.report:
            items.append(ui.TextDisplay(self.report))
        if not snap.files:
            items.append(ui.TextDisplay(f"{emoji.error} No emoji files in `{EMOJI_DIR}`."))
        elif snap.pending:
            lines = (f"{emoji.bullet} **{label}**: {_names(names)}" for label, names in changes if names)
            items.append(ui.TextDisplay("### Pending\n" + "\n".join(lines)))
        elif not self.report:
            items.append(ui.TextDisplay(f"{emoji.success} Everything is in sync."))
        problems = [f"{emoji.bullet_red} **{label}**: {_names(names)}" for label, names in issues if names]
        problems += [f"{emoji.bullet_red} **Skipped** `{name}`: {why}" for name, why in snap.skipped.items()]
        if problems:
            items.append(ui.TextDisplay("### Issues\n" + "\n".join(problems)))
        items.append(ui.TextDisplay(f"-# `{len(snap.files)}` files · `{len(snap.remote)}` app emojis"))
        self.add_item(ui.Container(*items))
        self.add_item(
            ui.ActionRow(
                button(
                    self._sync,
                    label=syncing or "Sync",
                    emoji=emoji.loading_white if syncing else emoji.sync_white,
                    custom_id="emoji:sync",
                    disabled=bool(syncing) or not snap.pending,
                ),
                button(
                    self._recheck,
                    label="Refresh",
                    emoji=emoji.reload_white,
                    custom_id="emoji:refresh",
                    disabled=bool(syncing),
                ),
            )
        )

    async def _recheck(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self, interaction, "Checking..."):
            return
        self.snap, self.report = await scan(self.bot), None
        self.render()
        await interaction.edit_original_response(view=self)

    async def _sync(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self, interaction, "Syncing..."):
            return
        # Rescanned so files edited since the panel opened are included
        self.snap = snap = await scan(self.bot)
        counts = {"new": len(snap.new), "edited": len(snap.edited), "removed": len(snap.removed)}
        total, done = sum(counts.values()), 0

        def step() -> None:
            nonlocal done
            done += 1

        syncing = asyncio.ensure_future(apply(self.bot, snap, step)) if snap.pending else None
        shown = -1
        while syncing and not syncing.done():
            if done != shown:
                shown = done
                # Redrawn each time so the text and buttons pick up emojis replaced since the last edit
                self.render(syncing=f"Syncing {done}/{total}")
                # Between deleting an emoji and uploading its new file, a button showing it fails the edit. Progress is
                # only cosmetic, so that tick is skipped and the next one shows the new emoji.
                with contextlib.suppress(discord.HTTPException):
                    await interaction.edit_original_response(view=self)
            await asyncio.wait({syncing}, timeout=1.5)
        failed = await syncing if syncing else {}

        summary = ", ".join(f"{count} {label}" for label, count in counts.items() if count) or "nothing to change"
        self.report = f"{emoji.error if failed else emoji.success} Synced: {summary}."
        if failed:
            self.report += "\n" + "\n".join(
                f"{emoji.bullet_red} `{name}`: {why}" for name, why in list(failed.items())[:_NAMES_SHOWN]
            )
        self.render()
        await interaction.edit_original_response(view=self)


class Emojis:
    client: Client

    @slash_command(guild_ids=config.owner_guild_ids, name="emoji")
    @check.is_dev()
    async def emoji_panel(self, ctx: discord.ApplicationContext):
        """Checks the app's emojis against emojis/ and syncs them."""
        await ctx.defer()
        await ctx.respond(view=EmojiPanel(ctx, self.client, await scan(self.client)))
