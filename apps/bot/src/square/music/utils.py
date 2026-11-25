import discord
import re
from collections.abc import Coroutine
from discord import ui
from square.core.view import DesignerView, error_view
from square.music import store
from square.music.core import SquarePlayer
from square.utils import config
from square.utils.emoji import emoji
from typing import Any


def get_source(source_name: str | None) -> dict:
    _sources = {
        "spotify": {"emoji": emoji.spotify, "color": 0x1ED760},
        "youtube": {"emoji": emoji.youtube, "color": 0xFF0000},
        "soundcloud": {"emoji": emoji.soundcloud, "color": 0xFF5500},
        "applemusic": {"emoji": emoji.applemusic, "color": 0xFA233B},
        "deezer": {"emoji": emoji.deezer, "color": 0xA238FF},
        "bandcamp": {"emoji": emoji.bandcamp, "color": 0x408294},
        "twitch": {"emoji": emoji.twitch, "color": 0x9146FF},
        "vimeo": {"emoji": emoji.vimeo, "color": 0x1AB7EA},
        "_": {"emoji": emoji.music, "color": config.color.theme},
    }

    return _sources.get(source_name, _sources["_"])


def container(content: str, color: int | None = None) -> DesignerView:
    c = ui.Container(ui.TextDisplay(content))
    if color is not None:
        c.color = color
    return DesignerView(c)


async def reply(
    source: discord.ApplicationContext | discord.Interaction,
    content: str,
    *,
    color: int | None = None,
) -> None:
    view = container(content, color)
    interaction = source.interaction if isinstance(source, discord.ApplicationContext) else source
    if interaction.response.is_done():
        await interaction.followup.send(view=view, ephemeral=True)
    else:
        await interaction.response.send_message(view=view, ephemeral=True)


async def delete_quietly(message: discord.Message | discord.PartialMessage) -> None:
    try:
        await message.delete()
    except discord.HTTPException:
        pass


def music_log(guild_id: int, content: str, *, color: int | None = None) -> Coroutine[Any, Any, None]:
    """
    Posts a self-deleting log message to the guild's player channel.

    The message auto-deletes after 5 seconds. Does nothing if no player channel is set.

    The channel is looked up at call time rather than when the send runs, so a log gathered
    alongside a teardown still lands after the teardown has flushed the store.

    Args:
        guild_id (int): The guild whose player channel receives the log.
        content (str): The message text.
        color (int | None): Optional accent color for the container.
    """
    return _send_log(store.play_ch(guild_id), content, color)


async def _send_log(channel: discord.abc.Messageable | None, content: str, color: int | None) -> None:
    if not channel:
        return
    try:
        await channel.send(view=container(content, color), delete_after=5)
    except discord.HTTPException:
        pass


def split_log_text(content: str) -> tuple[str, str]:
    content = content.strip()
    match = re.match(r"^(<a?:[^:]+:\d+>|[^\x00-\x7f\w]+)\s*", content)
    if not match:
        return "", _decapitalize(content)
    rest = content[match.end() :]
    return match.group(1), (_decapitalize(rest) if rest else content)


def _decapitalize(text: str) -> str:
    """
    Lowercases the opening word so it can follow a mention, unless it carries its own capital.

    "I need the `Connect` permission." has to survive as "I", and an acronym as itself.
    """
    first = text.split(" ", 1)[0].rstrip(".,:;!?")
    if not first or first.isupper() or not first[:1].isalpha():
        return text
    return text[0].lower() + text[1:]


async def music_interaction_check(view: DesignerView, player: SquarePlayer, interaction: discord.Interaction) -> bool:
    if getattr(view, "live", True) is False:
        try:
            await interaction.response.defer()
        except discord.HTTPException:
            pass
        return False
    if not player or not player.current:
        view.disable_all_items()
        await interaction.response.edit_message(view=view)
        await interaction.followup.send(
            view=error_view("Nothing is being played at the current moment."),
            ephemeral=True,
        )
        return False
    elif not interaction.user.voice:
        await interaction.response.send_message(view=error_view("Join a voice channel first."), ephemeral=True)
        return False
    elif player.connected and interaction.user.voice.channel.id != player.channel.id:
        await interaction.response.send_message(view=error_view("You are not in my voice channel."), ephemeral=True)
        return False
    else:
        return True
