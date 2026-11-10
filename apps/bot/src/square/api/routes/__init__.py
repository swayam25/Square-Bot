from square.api import live
from square.api.routes import guilds, music, settings, system

handlers = [system.health, guilds.my_guilds, guilds.router, settings.router, music.router, live.live]
