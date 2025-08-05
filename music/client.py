import asyncio
import discord
import lavalink
from core import Client
from utils import config


class LavalinkVoiceClient(discord.VoiceProtocol):
    def __init__(self, client: Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.connect_event = asyncio.Event()

    async def on_voice_server_update(self, data):
        lavalink_data = {"t": "VOICE_SERVER_UPDATE", "d": data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        lavalink_data = {"t": "VOICE_STATE_UPDATE", "d": data}
        await self.lavalink.voice_update_handler(lavalink_data)

    # Connect
    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        await self.channel.guild.change_voice_state(channel=self.channel, self_deaf=True, self_mute=False)
        try:
            self.lavalink: lavalink.Client = self.client.lavalink
        except AttributeError:
            self.client.lavalink = self.lavalink = lavalink.Client(self.client.user.id)
            self.client.lavalink.add_node(
                host=config.lavalink["host"],
                port=config.lavalink["port"],
                password=config.lavalink["password"],
                region=config.lavalink["region"],
                ssl=config.lavalink["secure"],
            )

    # Disconnect
    async def disconnect(self, *, force: bool) -> None:
        await self.channel.guild.change_voice_state(channel=None)
        player: lavalink.DefaultPlayer = self.lavalink.player_manager.get(self.channel.guild.id)
        if player:
            player.channel_id = False
            await player.stop()
        self.cleanup()
