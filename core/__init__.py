import discord
import lavalink
from core.view import DesignerView
from discord import ui
from discord.ext import commands
from rich.console import Console
from utils import config, temp
from utils.emoji import emoji

console = Console()


class Client(commands.Bot):
    def __init__(self, lavalink: lavalink.Client | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_mentions = discord.AllowedMentions().none()
        self.lavalink = lavalink

    async def on_ready(self):
        console.print(f"[green]✓ Logged in as [cyan]{self.user}[/]")
        data = {
            "ID": self.user.id,
            f"Guild{'' if len(self.guilds) <= 1 else 's'}": len(self.guilds),
            "Latency": f"{round(self.latency * 1000)}ms",
            "Commands Loaded": len(self.all_commands),
        }
        items = list(data.items())
        for i, (key, value) in enumerate(items):
            is_last = i == len(items) - 1
            prefix = "╰" if is_last else "├"
            console.print(f"  [green]{prefix} [bold]{key}[/]: [cyan]{value}[/]")

        restart_msg = temp.get("restart_msg")
        if restart_msg:
            try:
                ch = await self.fetch_channel(restart_msg.get("channel_id"))
                msg = await ch.fetch_message(restart_msg.get("id"))
                await msg.edit(
                    view=DesignerView(
                        ui.Container(
                            ui.TextDisplay(f"{emoji.success} Successfully restarted!"),
                            color=config.color.green,
                        )
                    )
                )
                temp.delete("restart_msg")
            except Exception:
                pass
