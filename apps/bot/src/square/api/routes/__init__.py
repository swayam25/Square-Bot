from square.api import live
from square.api.routes import guilds, invites, music, settings, system, tickets

handlers = [
    system.health,
    guilds.my_guilds,
    guilds.router,
    settings.router,
    invites.router,
    tickets.router,
    music.router,
    live.live,
]
