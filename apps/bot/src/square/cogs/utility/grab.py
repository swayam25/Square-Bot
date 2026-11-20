import discord
import re
from dataclasses import dataclass
from discord import ui
from io import BytesIO
from square.core import Client
from square.core.view import DesignerView, button, error_view, show_loading
from square.utils.emoji import emoji
from square.utils.helpers import fmt_user

_CUSTOM_EMOJI = re.compile(r"<(a?):(\w{2,32}):(\d{15,21})>")


@dataclass(frozen=True)
class Grabbed:
    id: int
    name: str
    animated: bool = False
    sticker: discord.StickerItem | None = None

    @property
    def partial(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name=self.name, id=self.id, animated=self.animated)

    @property
    def url(self) -> str:
        return self.sticker.url if self.sticker else self.partial.url

    @property
    def file_url(self) -> str:
        """The original upload. Animated emoji URLs point at a WebP copy."""
        if self.sticker:
            return self.sticker.url
        return f"{discord.Asset.BASE}/emojis/{self.id}.{'gif' if self.animated else 'png'}"

    @property
    def kind(self) -> str:
        return "sticker" if self.sticker else "emoji"


def collect_expressions(message: discord.Message) -> list[Grabbed]:
    found: dict[int, Grabbed] = {}
    sources = [message, *(snapshot.message for snapshot in message.snapshots if snapshot.message)]
    for source in sources:
        for animated, name, emoji_id in _CUSTOM_EMOJI.findall(source.content or ""):
            found.setdefault(int(emoji_id), Grabbed(int(emoji_id), name, bool(animated)))
    for reaction in message.reactions:
        if isinstance(reaction.emoji, str) or not reaction.emoji.id:
            continue
        icon = reaction.emoji
        found.setdefault(icon.id, Grabbed(icon.id, icon.name, icon.animated))
    for source in sources:
        for sticker in source.stickers:
            # Lottie is Discord's own vector format: no picture to show and servers can't upload it
            if sticker.format is not discord.StickerFormatType.lottie:
                found.setdefault(sticker.id, Grabbed(sticker.id, sticker.name, sticker=sticker))
    return list(found.values())


class GrabView(DesignerView):
    def __init__(self, client: Client, items: list[Grabbed], guild: discord.Guild | None, manager: bool):
        super().__init__()
        self.client = client
        self.grabbed = items
        self.guild = guild
        self.manager = manager
        self.page = 0
        self.added: set[int] = set()
        self.build()

    def _here(self, item: Grabbed) -> bool:
        if item.sticker:
            return any(sticker.id == item.id for sticker in self.guild.stickers)
        return self.guild.get_emoji(item.id) is not None

    def build(self) -> None:
        self.clear_items()
        item = self.grabbed[self.page]
        rows = [f"{emoji.mention} **Name**: `{item.name}`", f"{emoji.id} **ID**: `{item.id}`"]
        if item.sticker:
            rows.append(f"{emoji.img} **Format**: {item.sticker.format.name.upper()}")
        else:
            rows.append(f"{emoji.img} **Animated**: {'Yes' if item.animated else 'No'}")
        rows.append(f"{emoji.date} **Created**: {discord.utils.format_dt(discord.utils.snowflake_time(item.id), 'R')}")
        if not item.sticker:
            rows.append(f"{emoji.note} **Usage**: `{item.partial}`")
        container = ui.Container(
            ui.Section(
                ui.TextDisplay(f"## {item.kind.title()}"),
                ui.TextDisplay("\n".join(rows)),
                accessory=ui.Thumbnail(item.url),
            )
        )
        total = len(self.grabbed)
        if total > 1:
            container.add_item(ui.Separator())
            container.add_item(ui.TextDisplay(f"-# Viewing Page {self.page + 1}/{total}"))
        self.add_item(container)

        url = ui.Button(label="URL", emoji=emoji.img_white, style=discord.ButtonStyle.link, url=item.file_url)
        actions: list[ui.Button] = []
        if item.id in self.added:
            actions.append(ui.Button(label="Added", emoji=emoji.success, disabled=True))
        elif self.guild and self.manager and not self._here(item):
            actions.append(button(self._add, label="Add to Server", emoji=emoji.add_white))
        if total == 1:
            actions.insert(0, url)
        if actions:
            self.add_item(ui.ActionRow(*actions))

        if total > 1:
            last = total - 1
            nav = [
                button(lambda i, page=page: self._go(i, page), emoji=icon)
                for icon, page in (
                    (emoji.start_white, 0),
                    (emoji.previous_white, last if self.page == 0 else self.page - 1),
                    (emoji.next_white, 0 if self.page == last else self.page + 1),
                    (emoji.end_white, last),
                )
            ]
            nav.insert(2, url)
            self.add_item(ui.ActionRow(*nav))

    async def _go(self, interaction: discord.Interaction, page: int) -> None:
        if not await show_loading(self, interaction):
            return
        self.page = page
        self.build()
        await interaction.edit_original_response(view=self)

    async def _add(self, interaction: discord.Interaction) -> None:
        if not await show_loading(self, interaction):
            return
        problem = await self._upload(interaction, self.grabbed[self.page])
        self.build()
        await interaction.edit_original_response(view=self)
        if problem:
            await interaction.followup.send(view=error_view(problem), ephemeral=True)

    async def _upload(self, interaction: discord.Interaction, item: Grabbed) -> str | None:
        guild = self.guild
        if not interaction.permissions.manage_emojis:
            return f"You need the Manage Expressions permission to add a {item.kind} here."
        if not guild.me.guild_permissions.manage_emojis:
            return f"I need the Manage Expressions permission to add a {item.kind} here."
        if item.sticker:
            if len(guild.stickers) >= guild.sticker_limit:
                return "This server has no free sticker slots."
        elif sum(icon.animated == item.animated for icon in guild.emojis) >= guild.emoji_limit:
            return f"This server has no free {'animated' if item.animated else 'static'} emoji slots."
        reason = f"Grabbed by {fmt_user(interaction.user)}"
        try:
            data = await self.client.http.get_from_cdn(item.file_url)
            if item.sticker:
                full = await item.sticker.fetch()
                await guild.create_sticker(
                    name=item.name,
                    description=getattr(full, "description", None) or None,
                    # Discord only stores this as a search tag, so the name works when the sticker has no emoji
                    emoji=getattr(full, "emoji", None) or item.name,
                    file=discord.File(BytesIO(data), filename=f"{item.id}.{item.sticker.format.file_extension}"),
                    reason=reason,
                )
            else:
                await guild.create_custom_emoji(name=item.name, image=data, reason=reason)
        except discord.NotFound:
            return f"That {item.kind} was deleted, so I can't get its file."
        except discord.HTTPException as error:
            return f"Discord refused the {item.kind}: {(error.text or str(error)).rstrip('.').lower()}."
        self.added.add(item.id)
        return None
