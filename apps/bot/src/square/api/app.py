import logging
import msgspec
from importlib.metadata import version
from litestar import Litestar, Request, Router
from litestar.datastructures import State
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.openapi.spec import Components, SecurityScheme
from litestar.types import Scope
from square.api import live
from square.api.auth import provide_actor, provide_client, secret_guard
from square.api.routes import handlers
from square.core import Client
from square.music.errors import MusicError
from square.settings.errors import SettingError
from typing import Any

log = logging.getLogger(__name__)


def create_app(client: Client | None, *, secret: str, docs: bool) -> Litestar:
    """
    The API app. Every route needs the shared secret.

    Args:
        client (:class:`Client` | None): The running bot. `None` only builds the app, e.g. to export its schema.
        secret (str): The `[api] secret` the dashboard server sends.
        docs (bool): Serve the OpenAPI docs at `/docs`. Off in production.
    """
    if client is not None:
        client.add_listener(live.on_music_update, "on_music_update")
    api = Router(
        path="/",
        route_handlers=handlers,
        guards=[secret_guard(secret)],
        security=[{"secret": []}],
        dependencies={
            "client": Provide(provide_client, sync_to_thread=False),
            "actor": Provide(provide_actor, sync_to_thread=False),
        },
    )
    return Litestar(
        route_handlers=[api],
        state=State({"client": client}),
        openapi_config=_openapi() if docs else None,
        after_exception=[_log_exception],
        # Errors are logged through the bot's own logging, and `debug` stays off so tracebacks never reach a response
        logging_config=None,
        debug=False,
        request_max_body_size=256 * 1024,
    )


def _openapi() -> OpenAPIConfig:
    return OpenAPIConfig(
        title="Square API",
        version=version("square"),
        path="/docs",
        render_plugins=[
            _Scalar(
                version="1.76.0",
                options={
                    "theme": "kepler",
                    "darkMode": True,
                    "hideDarkModeToggle": True,
                    "showOperationId": True,
                    "showDeveloperTools": "never",
                    "authentication": {"preferredSecurityScheme": "secret"},
                    "agent": {"disabled": True},
                    "telemetry": False,
                },
            )
        ],
        # The handler's name becomes the generated client's function name, e.g. `my_guilds` -> `myGuilds()`
        operation_id_creator=lambda handler, _method, _path: handler.handler_name,
        components=Components(
            security_schemes={
                "secret": SecurityScheme(
                    type="http", scheme="bearer", description="The `[api] secret` from config.toml"
                ),
            },
        ),
    )


class _Scalar(ScalarRenderPlugin):
    # Litestar's page links its own branding stylesheet, which overrides Scalar's themes
    def render(self, request: Request, openapi_schema: dict[str, Any]) -> bytes:
        config = msgspec.json.encode({"url": self.get_openapi_json_route(request), **(self.options or {})}).decode()
        return f"""<!doctype html>
<html>
<head>
<title>{openapi_schema["info"]["title"]}</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<div id="app"></div>
<script src="{self.js_url}"></script>
<script>Scalar.createApiReference("#app", {config})</script>
</body>
</html>""".encode()


def _log_exception(exc: Exception, scope: Scope) -> None:
    # Refused settings changes and music controls are answered with a 409/422, not bugs
    if not isinstance(exc, HTTPException | SettingError | MusicError):
        log.error("API request to %s failed", scope["path"], exc_info=exc)
