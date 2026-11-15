from square.api import live
from square.api.routes import guilds, invites, music, profile, settings, system, tickets

handlers = [
    system.health,
    guilds.my_guilds,
    guilds.router,
    settings.router,
    profile.router,
    invites.router,
    tickets.router,
    music.router,
    live.live,
]
