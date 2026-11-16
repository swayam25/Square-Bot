from litestar import Request, Response
from litestar.openapi import ResponseSpec
from square.api import resolve
from square.api.resolve import SettingError
from square.api.schemas import Problem
from square.core import Client

REFUSED = {422: ResponseSpec(data_container=Problem, description="The bot refused the change", generate_examples=False)}


def refused(request: Request, exc: SettingError) -> Response[Problem]:
    client: Client | None = request.app.state.client
    guild = client.get_guild(int(request.path_params["guild_id"])) if client else None
    return Response(Problem(detail=resolve.plain(guild, str(exc)) if guild else str(exc)), status_code=422)
