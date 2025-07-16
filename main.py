import discord
import os
from db import DB
from pyfiglet import Figlet
from rich.console import Console
from rich.progress import Progress, SpinnerColumn
from utils import config

# Vars
status = discord.Status.online
activity = discord.Activity(type=discord.ActivityType.watching, name="Discord")
intents = discord.Intents.all()
client = discord.Bot(status=status, activity=activity, intents=intents, help_command=None)
console = Console()

# Startup printing
figlted_txt = Figlet(font="standard", justify="center").renderText("Discord Bot")
console.print(f"[cyan]{figlted_txt}[/]")


# On ready event
@client.event
async def on_ready():
    console.print(f"[green][bold]✓[/] Logged in as [cyan]{client.user}[/] [ID: {client.user.id}][/]")
    console.print(
        f"[green][bold]✓[/] Connected to {len(client.guilds)} guild{'' if len(client.guilds) <= 1 else 's'}[/]"
    )


# Loading all files
def load_cogs():
    cogs_prog = Progress(
        SpinnerColumn(style="yellow", finished_text="[green bold]✓[/]"),
        "[progress.description]{task.description} [progress.percentage]{task.percentage:>3.1f}%",
    )
    with cogs_prog as prog:
        file_count = len([file for file in os.listdir("./cogs") if file.endswith(".py")])
        task = cogs_prog.add_task("Loading Cogs", total=file_count)
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                prog.update(task, advance=1)
                client.load_extension(f"cogs.{filename[:-3]}")
        prog.update(task, description="[green]Loaded Cogs[/]", completed=file_count)


# Shutdown
async def shutdown():
    """Shutdown the bot gracefully."""
    shutdown_prog = Progress(
        SpinnerColumn(style="yellow", finished_text="[yellow bold]✓[/]"),
        "[progress.description]{task.description}",
    )

    with shutdown_prog as prog:
        task = prog.add_task("Shutting down", total=2)
        await DB().close()
        prog.advance(task, advance=1)
        if not client.is_closed():
            await client.close()
        prog.advance(task, advance=1)
        prog.update(task, description="[yellow]Bot has been shut down[/]", completed=2)


# Main func to run the bot
async def main():
    try:
        await DB().init()
        load_cogs()
        await client.start(config.bot_token)
    finally:
        await shutdown()


# Execute the main func
try:
    client.loop.run_until_complete(main())
except Exception:
    console.print_exception(show_locals=True)
