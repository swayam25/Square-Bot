import discord
import logging
import math
import sonolink
from discord.ext import commands
from square.core.view import success_view
from square.utils import temp

log = logging.getLogger("square")


class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_mentions = discord.AllowedMentions().none()
        self.sonolink: sonolink.Client = sonolink.Client(self)

    async def on_ready(self):
        # Latency stays `inf` until Discord acknowledges the first heartbeat
        latency = f"{round(self.latency * 1000)} ms" if math.isfinite(self.latency) else "—"
        log.info(
            "Logged in as %s · %d guilds · %s · %d commands",
            self.user,
            len(self.guilds),
            latency,
            len(self.application_commands),
        )

        restart_msg = temp.get("restart_msg")
        if restart_msg:
            try:
                ch = await self.fetch_channel(restart_msg.get("channel_id"))
                msg = await ch.fetch_message(restart_msg.get("id"))
                await msg.edit(view=success_view("Successfully restarted!"))
            except Exception:
                log.exception("Failed to edit the restart message")
            temp.delete("restart_msg")
