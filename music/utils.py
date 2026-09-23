import discord
import re
from core.view import DesignerView
from discord import ui
from music import store
from music.core import SquarePlayer
from utils import config
from utils.emoji import emoji


def get_source(source_name: str | None) -> dict:
    """
    Resolves the emoji and accent color for a music source.

    Args:
        source_name (str | None): The track's source name (e.g. ``"youtube"``).

    Returns:
        dict: A mapping with the resolved ``emoji`` markdown and ``color`` accent.
    """
    _sources = {
        "spotify": {"emoji": "spotify", "color": config.color.green},
        "youtube": {"emoji": "youtube", "color": config.color.red},
        "soundcloud": {"emoji": "soundcloud", "color": config.color.orange},
        "_": {"emoji": "music", "color": config.color.theme},
    }

    meta = _sources.get(source_name, _sources["_"])
    return {"emoji": getattr(emoji, meta["emoji"]), "color": meta["color"]}


def container(content: str, color: int | None = None) -> DesignerView:
    """
    Wraps a text string into a :class:`DesignerView` container.

    Args:
        content (str): The text to display inside the container.
        color (int | None): Optional accent color for the container border.

    Returns:
        :class:`DesignerView`: A view containing the styled container.
    """
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
    """
    Sends an ephemeral message to the invoker.

    Works for both slash command contexts and button/select interactions, using followup if the response has already been sent.

    Args:
        source (:class:`ApplicationContext` | :class:`Interaction`): The invoking command or interaction.
        content (str): The message text.
        color (int | None): Optional accent color for the container.
    """
    view = container(content, color)
    interaction = source.interaction if isinstance(source, discord.ApplicationContext) else source
    if interaction.response.is_done():
        await interaction.followup.send(view=view, ephemeral=True)
    else:
        await interaction.response.send_message(view=view, ephemeral=True)


async def music_log(guild_id: int, content: str, *, color: int | None = None) -> None:
    """
    Posts a self-deleting log message to the guild's player channel.

    The message auto-deletes after 5 seconds. Does nothing if no player channel is set.

    Args:
        guild_id (int): The guild whose player channel receives the log.
        content (str): The message text.
        color (int | None): Optional accent color for the container.
    """
    channel = store.play_ch(guild_id)
    if not channel:
        return
    try:
        await channel.send(view=container(content, color), delete_after=5)
    except discord.HTTPException:
        # Missing send permission in the player channel must not break the player action itself.
        pass


def split_log_text(content: str) -> tuple[str, str]:
    """
    Splits a confirmation message into its leading emoji and the rest, lowercased.

    A log line reads "<emoji> @user paused the player.", so the emoji is handed back rather than dropped along with
    the sentence case, letting the caller put it in front of the mention.

    Args:
        content (str): The message text, optionally starting with a custom or unicode emoji.

    Returns:
        tuple[str, str]: The leading emoji, empty when there is none, and the remaining lowercased text.
    """
    content = content.strip()
    # Custom emoji, or a run of non-ASCII symbols: anything ASCII is real text, not a prefix worth lifting out.
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
    """
    Gate for all player and queue button interactions.

    Verifies that something is currently playing, the user is in a voice channel, and the user is in the same voice channel as the bot.

    Args:
        view (:class:`DesignerView`): The view whose items are disabled on failure.
        player (:class:`SquarePlayer`): The active player for the guild.
        interaction (:class:`Interaction`): The incoming button or select interaction.

    Returns:
        bool: True if all checks pass, False otherwise (response already sent).
    """
    if getattr(view, "live", True) is False:
        # Already-disabled buttons; swallow the race rather than stripping the card below.
        try:
            await interaction.response.defer()
        except discord.HTTPException:
            pass  # Acknowledged elsewhere, or the token expired. Either way the press is spent.
        return False
    if not player or not player.current:
        view.disable_all_items()
        await interaction.response.edit_message(view=view)
        await interaction.followup.send(
            view=container(f"{emoji.error} Nothing is being played at the current moment.", config.color.red),
            ephemeral=True,
        )
        return False
    elif not interaction.user.voice:
        await interaction.response.send_message(
            view=container(f"{emoji.error} Join a voice channel first.", config.color.red), ephemeral=True
        )
        return False
    elif player.connected and interaction.user.voice.channel.id != player.channel.id:
        await interaction.response.send_message(
            view=container(f"{emoji.error} You are not in my voice channel.", config.color.red), ephemeral=True
        )
        return False
    else:
        return True
