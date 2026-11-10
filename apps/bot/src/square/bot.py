import asyncio
import discord
import logging
import sys
from importlib.metadata import metadata, version
from square.cogs import extensions
from square.core import Client
from square.db import DB
from square.imaging import assets
from square.music import lyrics
from square.utils import config, invites

log = logging.getLogger("square")

intents = discord.Intents.all()
intents.presences = False

client = Client(
    status=discord.Status.online,
    activity=discord.CustomActivity(name=f"/help | Square v{version('square')}"),
    intents=intents,
    description=metadata("square")["Summary"],
    command_prefix="",
    help_command=None,
    # Every command works on server data, so none are offered in DMs where `ctx.guild` would be missing
    default_command_contexts={discord.InteractionContextType.guild},
)
invites.setup(client)

LOGO = r"""
       ::  @@:@-
   =*#####*===*##:
  *#-:=+=--+*==- -@:
 --:##+=+#######- ---
:++##  @@  :--: +##*=
#==-:#= -+*=:@@:## @@@
:-@:##:*#*=:-=*##+ -=
 ::**:##:=###**=:===
  :+ -#==#+++#*=*+
    @:#*:--=*-- :
     -#====
"""

NAME = r"""
 ____
/ ___|  __ _ _   _  __ _ _ __ ___
\___ \ / _` | | | |/ _` | '__/ _ \
 ___) | (_| | |_| | (_| | | |  __/
|____/ \__, |\__,_|\__,_|_|  \___|
          |_|
"""


def log_banner() -> None:
    """Logs the startup banner: the logo with the name centered beside it, version after the name."""
    art = LOGO.strip("\n").splitlines()
    name = NAME.strip("\n").splitlines()
    width = max(map(len, art))
    top = (len(art) - len(name)) // 2
    ver = f"v{version('square')}"
    for i, logo in enumerate(art):
        j = i - top
        right = name[j] if 0 <= j < len(name) else ""
        if j == len(name) - 1:
            right += f" {ver}"
        log.info(
            f"{logo.ljust(width)}    {right}".rstrip(),
            extra={"style": "cyan", "accent": ver, "highlighter": None, "no_wrap": True},
        )


def load_cogs() -> None:
    for name in extensions():
        client.load_extension(name)
    log.info("Loaded %d cogs", len(client.cogs))


async def shutdown() -> None:
    """Shuts the bot down gracefully."""
    await DB().close()
    await lyrics.close()
    await assets.close()
    if not client.is_closed():
        await client.close()
    log.info("Shut down")


async def main() -> None:
    try:
        await DB().init()
        load_cogs()
        async with client:
            await client.start(config.bot_token)
    finally:
        await shutdown()


def run() -> None:
    log_banner()
    try:
        if sys.platform == "win32":
            asyncio.run(main())
        else:
            import uvloop  # Faster event loop; it doesn't support Windows

            uvloop.run(main())
    except KeyboardInterrupt:
        log.warning("Keyboard interrupt received")
    except Exception:
        log.exception("Bot crashed")
