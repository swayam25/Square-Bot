import math
from litestar import get
from litestar.datastructures import State
from square.api.schemas import Health
from square.core import Client


@get("/health", summary="Bot status", tags=["System"])
async def health(state: State) -> Health:
    client: Client | None = state.client
    if client is None or not client.is_ready():
        return Health(ready=False, guilds=0, latency_ms=None)
    latency = round(client.latency * 1000) if math.isfinite(client.latency) else None
    return Health(ready=True, guilds=len(client.guilds), latency_ms=latency)
