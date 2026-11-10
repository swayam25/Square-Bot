import asyncio
import contextlib
import logging
import uvicorn
from collections.abc import Generator
from square.api.app import create_app
from square.core import Client
from square.utils import config

log = logging.getLogger(__name__)


class _Server(uvicorn.Server):
    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None]:
        # The bot owns Ctrl-C and stops the API from its own shutdown
        yield


_server: _Server | None = None
_task: asyncio.Task[None] | None = None


def start(client: Client) -> None:
    """Serves the API on the bot's own event loop, so routes read live bot state. Skipped without `[api]` in config."""
    global _server, _task
    if config.api is None:
        log.info("API disabled, add [api] to config.toml to enable it")
        return
    app = create_app(client, secret=config.api.secret, docs=config.api.docs)
    _server = _Server(
        uvicorn.Config(
            app,
            host=config.api.host,
            port=config.api.port,
            log_config=None,
            access_log=log.isEnabledFor(logging.DEBUG),
            server_header=False,
            proxy_headers=False,
            timeout_graceful_shutdown=5,
            ws_max_size=64 * 1024,  # Subscribe messages are tiny
        )
    )
    _task = asyncio.create_task(_serve(_server), name="api")


async def _serve(server: _Server) -> None:
    try:
        await server.serve()
    except SystemExit:
        # uvicorn exits when it can't bind the port. The bot stays up without the API
        log.error("API couldn't start on %s:%d", server.config.host, server.config.port)


async def stop() -> None:
    if _server is None or _task is None:
        return
    _server.should_exit = True
    await _task
