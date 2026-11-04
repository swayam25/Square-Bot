import discord
from discord import ui
from square.core.settings import SettingsPage, channel_picker, modal, pencil, title
from square.db import cache
from square.db.funcs.logs import remove_log_channel, set_all_log_channels
from square.utils.emoji import emoji
from square.utils.server_log import LogType


class LogsPage(SettingsPage):
    name = "Logs"
    emoji = emoji.description
    description = "Where each kind of log is sent"
    order = 2

    def summary(self) -> list[str]:
        channels = cache.get(self.guild.id).log_channels
        return [f"{emoji.description} **Log Channels**: {len(channels)} of {len(LogType)} set"]

    def build(self) -> list[ui.Item]:
        channels = cache.get(self.guild.id).log_channels
        lines = "\n".join(
            f"{emoji.bullet} **{log_type.label.removesuffix(' Log')}**: "
            + (f"<#{channel_id}>" if (channel_id := channels.get(log_type.key)) else str(emoji.off))
            for log_type in LogType
        )
        return [title("Logs"), ui.Section(ui.TextDisplay(lines), accessory=pencil(self._edit))]

    async def _edit(self, interaction: discord.Interaction) -> None:
        types = ui.Select(
            options=[discord.SelectOption(label=log_type.label, value=log_type.key) for log_type in LogType],
            min_values=1,
            max_values=len(LogType),
        )
        picker = channel_picker([discord.ChannelType.text])

        async def submit(submitted: discord.Interaction) -> None:
            keys = [str(key) for key in types.values or []]
            picked = picker.values or []
            channel = picked[0] if picked and isinstance(picked[0], discord.TextChannel) else None
            if channel:
                perms = channel.permissions_for(self.guild.me)
                if not (perms.send_messages and perms.manage_webhooks):
                    # Logs are posted through a webhook named after the bot
                    await self.panel.error(
                        submitted, f"I need `Send Messages` and `Manage Webhooks` in {channel.mention}."
                    )
                    return
                await set_all_log_channels(self.guild.id, keys, channel.id)
            else:
                for key in keys:
                    await remove_log_channel(self.guild.id, key)
            self.panel.bot.dispatch("log_channels_update", self.guild.id)
            await self.panel.refresh(submitted)

        await interaction.response.send_modal(
            modal(
                "Log channels",
                ui.Label("Log types", types),
                ui.Label("Channel", picker, description="Leave empty to turn the picked log types off."),
                on_submit=submit,
            )
        )

    async def reset(self, interaction: discord.Interaction) -> None:
        await remove_log_channel(self.guild.id)
        self.panel.bot.dispatch("log_channels_update", self.guild.id)
