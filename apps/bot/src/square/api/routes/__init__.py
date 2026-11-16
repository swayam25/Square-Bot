from square.api import live
from square.api.routes import guilds, invites, messages, music, profile, settings, system, tickets

handlers = [
    system.health,
    guilds.my_guilds,
    guilds.router,
    settings.router,
    profile.router,
    messages.router,
    invites.router,
    tickets.router,
    music.router,
    live.live,
]
