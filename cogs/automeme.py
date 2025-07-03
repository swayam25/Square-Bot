import asyncio
import discord
from db.funcs.guild import fetch_guild_settings
from discord.ext import commands, tasks
from utils.helpers import meme_embed


class AutoMeme(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.auto_meme.start()

    @tasks.loop(minutes=10)
    async def auto_meme(self):
        """Automatically posts memes in the configured channel."""
        guilds = self.client.guilds
        for guild in guilds:
            settings = await fetch_guild_settings(guild.id)
            if settings.auto_meme_channel_id:
                channel = guild.get_channel(settings.auto_meme_channel_id)
                if channel and channel.permissions_for(guild.me).send_messages:
                    meme = await meme_embed()
                    if meme:
                        try:
                            await channel.send(embed=meme)
                        except discord.HTTPException as e:
                            if e.status == 429:  # Rate limit error
                                retry_after = e.retry_after if hasattr(e, "retry_after") else 60
                                await asyncio.sleep(retry_after)
                                try:
                                    await channel.send(embed=meme)
                                except discord.HTTPException:
                                    pass
                        except Exception:
                            pass

    @auto_meme.before_loop
    async def before_auto_meme(self):
        """Wait until the bot is ready before starting the auto meme task."""
        await self.client.wait_until_ready()


def setup(client: commands.Bot):
    client.add_cog(AutoMeme(client))
