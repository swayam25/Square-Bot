import discord
from discord import ui
from square.core.settings import SettingsPage, channel_picker, mention_or_off, modal, pencil, role_picker, row, title
from square.db import cache
from square.db.funcs.guild import set_autorole, set_media_only
from square.utils.emoji import emoji


class GeneralPage(SettingsPage):
    name = "General"
    emoji = emoji.settings
    description = "Auto role and media-only channel"
    order = 1

    def _autorole(self) -> discord.Role | None:
        role_id = cache.get(self.guild.id).autorole
        return self.guild.get_role(role_id) if role_id else None

    def _media_only(self) -> discord.abc.GuildChannel | None:
        channel_id = cache.get(self.guild.id).media_only_channel_id
        return self.guild.get_channel(channel_id) if channel_id else None

    def summary(self) -> list[str]:
        return [
            f"{emoji.role} **Auto Role**: {mention_or_off(self._autorole())}",
            f"{emoji.img} **Media Only**: {mention_or_off(self._media_only())}",
        ]

    def build(self) -> list[ui.Item]:
        lines = self.summary()
        return [title("General"), row(lines[0], pencil(self._edit_autorole)), row(lines[1], pencil(self._edit_media))]

    async def _edit_autorole(self, interaction: discord.Interaction) -> None:
        picker = role_picker([role] if (role := self._autorole()) else [])

        async def submit(submitted: discord.Interaction) -> None:
            picked = picker.values or []
            role = picked[0] if picked and isinstance(picked[0], discord.Role) else None
            if role and (role.is_default() or role.managed or role >= self.guild.me.top_role):
                await self.panel.error(submitted, f"I can't give out {role.mention}, it's above my role or managed.")
                return
            await set_autorole(self.guild.id, role.id if role else None)
            await self.panel.refresh(submitted)

        label = ui.Label("Role", picker, description="Given to every member who joins. Leave empty to turn it off.")
        await interaction.response.send_modal(modal("Auto role", label, on_submit=submit))

    async def _edit_media(self, interaction: discord.Interaction) -> None:
        picker = channel_picker([discord.ChannelType.text], self._media_only())

        async def submit(submitted: discord.Interaction) -> None:
            picked = picker.values or []
            channel = picked[0] if picked and isinstance(picked[0], discord.TextChannel) else None
            if channel:
                perms = channel.permissions_for(self.guild.me)
                if not (perms.send_messages and perms.manage_messages):
                    await self.panel.error(
                        submitted, f"I need `Send Messages` and `Manage Messages` in {channel.mention}."
                    )
                    return
            await set_media_only(self.guild.id, channel.id if channel else None)
            await self.panel.refresh(submitted)

        label = ui.Label("Channel", picker, description="Only media and links may be posted here. Empty turns it off.")
        await interaction.response.send_modal(modal("Media-only channel", label, on_submit=submit))

    async def reset(self, interaction: discord.Interaction) -> None:
        await set_autorole(self.guild.id, None)
        await set_media_only(self.guild.id, None)
