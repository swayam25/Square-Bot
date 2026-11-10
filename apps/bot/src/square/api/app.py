import logging
from importlib.metadata import version
from litestar import Litestar, Router
from litestar.datastructures import State
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.openapi.spec import Components, SecurityScheme
from litestar.types import Scope
from square.api.auth import provide_actor, provide_client, secret_guard
from square.api.routes import handlers
from square.core import Client

log = logging.getLogger(__name__)


def create_app(client: Client | None, *, secret: str, docs: bool) -> Litestar:
    """
    The API app. Every route needs the shared secret.

    Args:
        client (:class:`Client` | None): The running bot. `None` only builds the app, e.g. to export its schema.
        secret (str): The `[api] secret` the dashboard server sends.
        docs (bool): Serve the OpenAPI docs at `/docs`. Off in production.
    """
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
        render_plugins=[ScalarRenderPlugin()],
        components=Components(
            security_schemes={
                "secret": SecurityScheme(
                    type="http", scheme="bearer", description="The `[api] secret` from config.toml"
                ),
            },
        ),
    )


def _log_exception(exc: Exception, scope: Scope) -> None:
    if not isinstance(exc, HTTPException):
        log.error("API request to %s failed", scope["path"], exc_info=exc)
