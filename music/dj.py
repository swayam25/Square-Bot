import discord
from core.view import DesignerView
from db.funcs.dj import fetch_dj, set_dj_mode, set_dj_roles
from discord import ui
from music.core import SquarePlayer, requester_id
from music.utils import reply
from sonolink.models import Playable
from utils import config
from utils.emoji import emoji

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


class DJView(DesignerView):
    """
    DJ settings card: a mode toggle and a role picker in one container.

    Args:
        ctx (:class:`ApplicationContext`): The invoking command, used to resolve roles and gate the interactions.
        enabled (bool): Whether DJ mode is currently on.
        role_ids (list[int]): The currently configured DJ role IDs.
    """

    def __init__(self, ctx: discord.ApplicationContext, enabled: bool, role_ids: list[int]):
        super().__init__(ctx=ctx, check_author_interaction=True)
        self.ctx = ctx
        self.enabled = enabled
        self.roles = [role for role_id in role_ids if (role := ctx.guild.get_role(role_id))]
        self.build()

    def build(self):
        self.clear_items()
        toggle = ui.Button(
            label="Enabled" if self.enabled else "Disabled",
            emoji=emoji.on if self.enabled else emoji.off,
            style=discord.ButtonStyle.grey,
        )
        toggle.callback = self.toggle_callback
        role_select = ui.Select(
            discord.ComponentType.role_select,
            placeholder="Select DJ roles",
            min_values=0,
            max_values=MAX_ROLES,
            default_values=self.roles,
            custom_id="dj_roles",
        )
        role_select.callback = self.roles_callback
        if not self.enabled:
            note = "Everyone can use every music command while DJ mode is off."
        elif not self.roles:
            note = (
                "Only members with `Manage Server` control playback. Pick roles to add more DJs.\n"
                "-# Everyone else can still queue tracks, drop their own, and vote to skip."
            )
        else:
            note = (
                "Playback controls are DJ only. Everyone else can still queue tracks, drop their own, and vote to skip.\n"
                "-# Members with `Manage Server` always count as DJs."
            )
        self.add_item(
            ui.Container(
                ui.Section(
                    ui.TextDisplay("## DJ Mode"),
                    accessory=toggle,
                ),
                ui.TextDisplay(
                    f"{emoji.role} **DJ Roles**: {', '.join(role.mention for role in self.roles) or emoji.off}"
                ),
                ui.ActionRow(role_select),
                ui.TextDisplay(f"-# {note}"),
            )
        )

    async def toggle_callback(self, interaction: discord.Interaction):
        self.enabled = not self.enabled
        await set_dj_mode(interaction.guild_id, self.enabled)
        self.build()
        await interaction.response.edit_message(view=self)

    async def roles_callback(self, interaction: discord.Interaction):
        role_ids = [int(value) for value in interaction.data["values"]]
        await set_dj_roles(interaction.guild_id, role_ids)
        self.roles = [role for role_id in role_ids if (role := interaction.guild.get_role(role_id))]
        # Picking the first role is the whole point of the command, so don't make enabling it a second step.
        if self.roles and not self.enabled:
            self.enabled = True
            await set_dj_mode(interaction.guild_id, True)
        self.build()
        await interaction.response.edit_message(view=self)
