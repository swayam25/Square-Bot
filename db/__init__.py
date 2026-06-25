from aerich import Command
from rich.progress import Progress, SpinnerColumn
from tortoise import Tortoise  # kept for close_connections
from utils.config import db_url

TORTOISE_ORM = {
    "connections": {
        "default": db_url,
    },
    "apps": {"models": {"models": ["db.schema", "aerich.models"], "default_connection": "default"}},
}


class DB:
    """Database class to handle Tortoise ORM initialization and connection management."""

    async def init(self):
        """Initialize the database connection and generate schemas."""
        db_prog = Progress(
            SpinnerColumn(style="yellow", finished_text="[green]✓[/]"),
            "[progress.description]{task.description}",
        )

        with db_prog as prog:
            db_task = prog.add_task("Initializing Database", total=1)
            command = Command(tortoise_config=TORTOISE_ORM, app="models", location="./migrations")
            await command.init()
            try:
                await command.upgrade(run_in_transaction=True)
            except Exception:
                await command.init_db(safe=True)
                await command.upgrade(run_in_transaction=True)
            prog.update(db_task, description="[green]Initialized Database[/]", completed=1)

    async def close(self):
        """Close the database connection."""
        await Tortoise.close_connections()
