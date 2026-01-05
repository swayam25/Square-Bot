import discord
import os
import toml
from core import Client
from db import DB
from pyfiglet import Figlet
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from utils import config

# Metadata
with open("pyproject.toml") as f:
    data = toml.load(f)

# Vars
status = discord.Status.online
activity = discord.CustomActivity(name="Helping users!")
intents = discord.Intents.all()
client = Client(
    status=status,
    activity=activity,
    intents=intents,
    description=data["project"]["description"],
    command_prefix="",
    help_command=None,
)
console = Console()

# Startup printing
figlted_txt = Figlet(font="standard").renderText(str(data["project"]["name"]).title())
console.print(f"[cyan]{figlted_txt.removesuffix('\n')} [yellow bold]v{data['project']['version']}[/]\n")


# Loading all files
def load_cogs():
    cogs_prog = Progress(
        SpinnerColumn(style="yellow", finished_text="[green]✓[/]"),
        TextColumn("[progress.description]{task.description} [cyan]{task.completed}/{task.total}[/]"),
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
        SpinnerColumn(style="yellow", finished_text="[yellow]✓[/]"),
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
    console.print_exception()
