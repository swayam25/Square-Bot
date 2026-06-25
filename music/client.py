import discord
import lavalink
from core import Client
from discord.voice import VoiceProtocol
from lavalink.errors import ClientError
from utils import config


class LavalinkVoiceClient(VoiceProtocol):
    def __init__(self, client: Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False

        if self.client.lavalink is None:
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                host=config.lavalink["host"],
                port=config.lavalink["port"],
                password=config.lavalink["password"],
                region=config.lavalink["region"],
                ssl=config.lavalink["secure"],
            )
        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        await self.lavalink.voice_update_handler({"t": "VOICE_SERVER_UPDATE", "d": data})

    async def on_voice_state_update(self, data):
        channel_id = data["channel_id"]
        if not channel_id:
            await self._destroy()
            return
        self.channel = self.client.get_channel(int(channel_id))
        await self.lavalink.voice_update_handler({"t": "VOICE_STATE_UPDATE", "d": data})

    async def connect(
        self, *, timeout: float, reconnect: bool, self_deaf: bool = True, self_mute: bool = False
    ) -> None:
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_deaf=self_deaf, self_mute=self_mute)

    async def disconnect(self, *, force: bool = False) -> None:
        player: lavalink.DefaultPlayer = self.lavalink.player_manager.get(self.channel.guild.id)
        if not force and (not player or not player.is_connected):
            return
        await self.channel.guild.change_voice_state(channel=None)
        if player:
            player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()
        if self._destroyed:
            return
        self._destroyed = True
        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass
