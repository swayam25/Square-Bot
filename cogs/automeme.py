import asyncio
import discord
from db.funcs.guild import fetch_guild_settings
from discord.ext import commands, tasks


class AutoMeme(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.auto_meme.start()

    @tasks.loop(minutes=10)
    async def auto_meme(self):
        """Automatically posts memes in the configured channel."""
        guilds = self.client.guilds
        for guild in guilds:
            settings = await fetch_guild_settings(guild.id)  # Fetch guild settings from the database
            if settings.auto_meme["channel_id"]:  # Check if auto meme is enabled
                channel = guild.get_channel(settings.auto_meme["channel_id"])
                # Check if the channel exists and the bot has permission to send messages
                if channel and channel.permissions_for(guild.me).send_messages:
                    from utils.helpers import meme_view

                    meme = await meme_view(settings.auto_meme["subreddit"])
                    # Check if the meme is valid, and if the meme is NSFW or the channel is NSFW
                    if meme and (meme["nsfw"] is False or channel.is_nsfw()):
                        try:
                            await channel.send(view=meme["view"])
                        except discord.HTTPException as e:
                            if e.status == 429:  # Rate limit error
                                retry_after = e.retry_after if hasattr(e, "retry_after") else 60
                                # Wait for the `retry_after` time before trying again
                                await asyncio.sleep(retry_after)
                                try:
                                    await channel.send(view=meme["view"])
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
