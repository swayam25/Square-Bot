from square.api import live
from square.api.routes import (
    automod,
    autorole,
    giveaways,
    guilds,
    invites,
    messages,
    music,
    profile,
    settings,
    starboard,
    system,
    tickets,
    warnings,
)

handlers = [
    system.bot_emojis,
    guilds.my_guilds,
    guilds.router,
    settings.router,
    profile.router,
    messages.router,
    invites.router,
    tickets.router,
    giveaways.router,
    starboard.router,
    automod.router,
    warnings.router,
    autorole.router,
    music.router,
    live.live,
]
