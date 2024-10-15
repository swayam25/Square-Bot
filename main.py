import discord
import os
from utils import database as db
from rich import print
from rich.progress import Progress, SpinnerColumn
from pyfiglet import Figlet
from discord.ext import commands

# Discord vars
status = discord.Status.online if not db.lockdown(status_only=True) else discord.Status.dnd
activity = discord.Activity(type=discord.ActivityType.listening, name="Discord") if not db.lockdown(status_only=True) else discord.Activity(type=discord.ActivityType.playing, name="Maintenance")
intents = discord.Intents.all()
client = commands.Bot(status=status, activity=activity, intents=intents, help_command=None)

# Startup printing
figlted_txt = Figlet(font="standard", justify="center").renderText("Discord Bot")
print(f"[cyan]{figlted_txt}[/]")

# Loading all files
cogs_progress_bar = Progress(
    SpinnerColumn(style="yellow", finished_text="[green bold]✓[/]"),
    "[progress.description]{task.description} [progress.percentage]{task.percentage:>3.1f}%"
)
with cogs_progress_bar as progress:
    file_count = len([file for file in os.listdir("./cogs") if file.endswith(".py")])
    task = cogs_progress_bar.add_task("Loading Cogs", total=file_count)
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            progress.update(task, advance=1)
            client.load_extension(f"cogs.{filename[:-3]}")
    progress.update(task, description="[green]Loaded Cogs[/]")

# On connect event
@client.event
async def on_connect():
    if client.auto_sync_commands:
        await client.sync_commands()

# On ready event
@client.event
async def on_ready():
    print(f"[green][bold]✓[/] Logged in as {client.user} [ID: {client.user.id}][/]")
    print(f"[green][bold]✓[/] Connected to {len(client.guilds)} guild{'' if len(client.guilds) <= 1 else 's'}[/]")

# Starting bot
try:
    client.run(db.discord_api_token())
except Exception as e:
    print(f"[red][bold]✗[/] Unable to login due to {e}[/]")
