from square.api.routes import guilds, settings, system

handlers = [system.health, guilds.my_guilds, guilds.router, settings.router]
