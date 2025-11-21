import lavalink
from discord import AllowedMentions
from discord.ext import commands
from rich.console import Console

console = Console()


class Client(commands.Bot):
    def __init__(self, lavalink: lavalink.Client | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_mentions = AllowedMentions().none()
        self.lavalink = lavalink

    async def on_ready(self):
        console.print(f"[green][bold]✓[/] Logged in as [cyan]{self.user}[/] [ID: {self.user.id}][/]")
        console.print(
            f"[green][bold]✓[/] Connected to {len(self.guilds)} guild{'' if len(self.guilds) <= 1 else 's'}[/]"
        )
