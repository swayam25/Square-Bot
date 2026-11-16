from square.api import live
from square.api.routes import giveaways, guilds, invites, messages, music, profile, settings, system, tickets

handlers = [
    system.health,
    guilds.my_guilds,
    guilds.router,
    settings.router,
    profile.router,
    messages.router,
    invites.router,
    tickets.router,
    giveaways.router,
    music.router,
    live.live,
]
