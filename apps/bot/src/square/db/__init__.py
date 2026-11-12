import logging
from aerich import Command
from square.db import cache
from square.utils.config import db_url
from tortoise import Tortoise

log = logging.getLogger(__name__)

TORTOISE_ORM = {
    "connections": {
        "default": db_url,
    },
    "apps": {"models": {"models": ["square.db.schema", "aerich.models"], "default_connection": "default"}},
}


class DB:
    async def init(self):
        command = Command(tortoise_config=TORTOISE_ORM, app="models", location="./migrations")
        await command.init()
        applied = await command.upgrade(run_in_transaction=True)
        await cache.load()
        if applied:
            log.info("Database ready, applied %d migration(s): %s", len(applied), ", ".join(applied))
        else:
            log.info("Database ready, migrations up to date")

    async def close(self):
        await Tortoise.close_connections()
