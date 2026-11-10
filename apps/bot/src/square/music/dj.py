import discord
from sonolink.models import Playable
from square.db.funcs.dj import fetch_dj
from square.music.core import SquarePlayer, requester_id
from square.music.utils import reply
from square.utils import config
from square.utils.emoji import emoji

MAX_ROLES = 5


def listeners(player: SquarePlayer) -> list[discord.Member]:
    """
    Returns the members the player is playing to: everyone sharing its voice channel, bots and deafened aside.

    A deafened member can't hear what a skip vote is about, and a skip needs every listener to agree, so one idling
    there would block every vote. They are barred from voting to match, keeping both sides of the tally to the same
    people, which is what stops a vote asking for fewer votes than it has already counted.
    """
    if not player.connected:
        return []
    return [m for m in player.channel.members if not m.bot and m.voice and not (m.voice.deaf or m.voice.self_deaf)]


def votes_needed(listener_count: int) -> int:
    """
    Votes required to carry a skip: everyone still listening, counting the member who called the vote.

    Guarded at one so a momentarily empty channel can't hand back a threshold that nothing needs to clear.
    """
    return max(1, listener_count)


async def is_dj(member: discord.Member, player: SquarePlayer | None = None) -> bool:
    """
    Whether a member may use the DJ-restricted playback controls.

    Server managers always qualify, and so does everyone while DJ mode is off. With it on, DJ roles widen that
    baseline rather than being the switch themselves, so enabling it without one leaves managers in sole control.
    A member listening alone counts too, so an empty channel never locks its only occupant out.

    Args:
        member (:class:`Member`): The member to check.
        player (:class:`SquarePlayer` | None): The guild's player, used for the alone-in-voice case.
    """
    if member.guild_permissions.manage_guild:
        return True
    enabled, role_ids = await fetch_dj(member.guild.id)
    if not enabled:
        return True
    # Resolve against live roles so a deleted role, whose row outlives it, can't hand anyone DJ rights.
    role_ids = [role_id for role_id in role_ids if member.guild.get_role(role_id)]
    if any(role.id in role_ids for role in member.roles):
        return True
    return player is not None and listeners(player) == [member]


async def require_dj(
    source: discord.ApplicationContext | discord.Interaction,
    player: SquarePlayer,
    *,
    track: Playable | None = None,
) -> bool:
    """
    Gate for DJ-restricted actions, answering the member ephemerally when they aren't allowed.

    Passing a track also lets whoever requested it act on their own track.

    Args:
        source (:class:`ApplicationContext` | :class:`Interaction`): The invoking command or interaction.
        player (:class:`SquarePlayer`): The active player for the guild.
        track (:class:`Playable` | None): The track being acted on, if the action is scoped to one.

    Returns:
        bool: True when the action may proceed.
    """
    member = source.author if isinstance(source, discord.ApplicationContext) else source.user
    if await is_dj(member, player):
        return True
    if track is not None and requester_id(player, track) == member.id:
        return True
    await reply(source, f"{emoji.error} Only a DJ can do that.", color=config.color.red)
    return False
