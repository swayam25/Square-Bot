import discord
import logging
import math
import random
import sonolink
from discord.ext import commands, tasks
from square.core.view import success_view
from square.utils import temp

log = logging.getLogger("square")

STATUSES = (
    "Wearing a disguise today",
    "Not a robot (citation needed)",
    "Lurking professionally",
)


class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.status_line = random.choice(STATUSES)
        super().__init__(*args, activity=discord.CustomActivity(name=self.status_line), **kwargs)
        self.allowed_mentions = discord.AllowedMentions().none()
        self.sonolink: sonolink.Client = sonolink.Client(self)

    @tasks.loop(minutes=15)
    async def rotate_status(self):
        if self.rotate_status.current_loop == 0:
            return
        self.status_line = random.choice([line for line in STATUSES if line != self.status_line])
        await self.change_presence(activity=discord.CustomActivity(name=self.status_line))

    async def on_ready(self):
        if not self.rotate_status.is_running():
            self.rotate_status.start()
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
