"""
Server settings, one resource per feature so each dashboard page loads and saves only its own.

Every change goes through `square.settings`, the same rules the Discord `/settings` panel uses.
"""

import discord
import logging
from litestar import Request, Response, Router, delete, get, patch, post
from litestar.di import Provide
from litestar.openapi import ResponseSpec
from msgspec import UNSET
from square.api import resolve
from square.api.auth import provide_guild, provide_member
from square.api.schemas import (
    GeneralPatch,
    GeneralSettings,
    InvitePatch,
    InviteSettings,
    LogChannels,
    LogPatch,
    LogSettings,
    MusicPatch,
    MusicSettings,
    Notes,
    Problem,
    TicketPatch,
    TicketSettings,
    id_of,
)
from square.cogs.tickets import cards
from square.core import Client
from square.db import cache
from square.settings import general, invites, logs, music, reset_all, tickets
from square.settings.errors import SettingError
from square.utils.server_log import LogType

log = logging.getLogger(__name__)

REFUSED = {422: ResponseSpec(data_container=Problem, description="The bot refused the change", generate_examples=False)}


def _audit(member: discord.Member, action: str) -> None:
    log.info("Dashboard: %s (%s) %s in %s (%s)", member, member.id, action, member.guild, member.guild.id)


def _notes(*notes: str | None) -> Notes:
    return Notes(notes=[note for note in notes if note])


def _general(guild: discord.Guild) -> GeneralSettings:
    settings = cache.get(guild.id)
    return GeneralSettings(
        autorole_id=id_of(guild.get_role(settings.autorole) if settings.autorole else None),
        media_only_channel_id=id_of(
            guild.get_channel(settings.media_only_channel_id) if settings.media_only_channel_id else None
        ),
    )


@get("/general", summary="Auto role and media-only channel")
async def get_general_settings(guild: discord.Guild) -> GeneralSettings:
    return _general(guild)


@patch("/general", summary="Change the auto role or media-only channel", responses=REFUSED)
async def update_general_settings(guild: discord.Guild, member: discord.Member, data: GeneralPatch) -> GeneralSettings:
    # Resolve everything first, so a bad ID doesn't leave the change half applied
    role = resolve.role(guild, data.autorole_id) if data.autorole_id is not UNSET else UNSET
    channel = (
        resolve.text_channel(guild, data.media_only_channel_id) if data.media_only_channel_id is not UNSET else UNSET
    )
    if role is not UNSET:
        await general.set_autorole(guild, role)
    if channel is not UNSET:
        await general.set_media_only(guild, channel)
    _audit(member, "updated general settings")
    return _general(guild)


@delete("/general", summary="Reset general settings", status_code=200)
async def reset_general_settings(guild: discord.Guild, member: discord.Member) -> GeneralSettings:
    await general.reset(guild)
    _audit(member, "reset general settings")
    return _general(guild)


def _logs(guild: discord.Guild) -> LogSettings:
    channels = cache.get(guild.id).log_channels
    return LogSettings(
        channels=LogChannels(
            **{
                key: str(channel_id)
                for key, channel_id in channels.items()
                # Skips channels deleted since, and keys from log types the bot no longer has
                if key in LogChannels.__struct_fields__ and guild.get_channel(channel_id)
            }
        )
    )


@get("/logs", summary="Where each kind of log goes")
async def get_log_settings(guild: discord.Guild) -> LogSettings:
    return _logs(guild)


@patch("/logs", summary="Send log types to channels, or turn them off", responses=REFUSED)
async def update_log_settings(
    client: Client, guild: discord.Guild, member: discord.Member, data: LogPatch
) -> LogSettings:
    changes = {
        log_type: resolve.text_channel(guild, channel_id)
        for log_type in LogType
        if (channel_id := getattr(data.channels, log_type.key)) is not UNSET
    }
    await logs.set_channels(client, guild, changes)
    _audit(member, "updated log channels")
    return _logs(guild)


@delete("/logs", summary="Turn every log off", status_code=200)
async def reset_log_settings(client: Client, guild: discord.Guild, member: discord.Member) -> LogSettings:
    await logs.reset(client, guild)
    _audit(member, "reset log channels")
    return _logs(guild)


def _invites(guild: discord.Guild) -> InviteSettings:
    settings = cache.get(guild.id)
    return InviteSettings(tracker=settings.invite_tracker, fake_days=settings.invite_fake_days)


@get("/invites", summary="Invite tracker and fake account age")
async def get_invite_settings(guild: discord.Guild) -> InviteSettings:
    return _invites(guild)


@patch("/invites", summary="Change the invite tracker or fake account age", responses=REFUSED)
async def update_invite_settings(guild: discord.Guild, member: discord.Member, data: InvitePatch) -> InviteSettings:
    if data.fake_days is not UNSET:
        await invites.set_fake_days(guild, data.fake_days)
    if data.tracker is not UNSET:
        await invites.set_tracker(guild, data.tracker)
    _audit(member, "updated invite settings")
    return _invites(guild)


@delete("/invites", summary="Reset invite settings", status_code=200)
async def reset_invite_settings(guild: discord.Guild, member: discord.Member) -> InviteSettings:
    await invites.reset(guild)
    _audit(member, "reset invite settings")
    return _invites(guild)


@delete("/invites/counts", summary="Reset everyone's invite counts", status_code=200)
async def reset_invite_counts(guild: discord.Guild, member: discord.Member) -> InviteSettings:
    await invites.reset_counts(guild)
    _audit(member, "reset invite counts")
    return _invites(guild)


def _music(guild: discord.Guild) -> MusicSettings:
    return MusicSettings(
        request_channel_id=id_of(music.request_channel(guild)),
        stay_channel_id=id_of(music.stay_channel(guild)),
        dj_mode=cache.get(guild.id).dj_mode,
        dj_role_ids=[str(role.id) for role in music.dj_roles(guild)],
    )


@get("/music", summary="Request channel, 24/7 channel and DJ mode")
async def get_music_settings(guild: discord.Guild) -> MusicSettings:
    return _music(guild)


@patch("/music", summary="Change the 24/7 channel or DJ settings", responses=REFUSED)
async def update_music_settings(
    client: Client, guild: discord.Guild, member: discord.Member, data: MusicPatch
) -> MusicSettings:
    # Resolve everything first, so a bad ID doesn't leave the change half applied
    stay_channel = resolve.voice_channel(guild, data.stay_channel_id) if data.stay_channel_id is not UNSET else UNSET
    dj_roles = resolve.roles(guild, data.dj_role_ids) if data.dj_role_ids is not UNSET else UNSET
    if dj_roles is not UNSET:
        await music.set_dj_roles(guild, dj_roles)
    # After the roles, since picking roles turns DJ mode on by itself
    if data.dj_mode is not UNSET:
        await music.set_dj_mode(guild, data.dj_mode)
    if stay_channel is not UNSET:
        await music.set_stay_channel(client, guild, stay_channel)
    _audit(member, "updated music settings")
    return _music(guild)


@delete("/music", summary="Reset music settings, deleting the request channel", status_code=200)
async def reset_music_settings(client: Client, guild: discord.Guild, member: discord.Member) -> Notes:
    note = await music.reset(client, guild, member)
    _audit(member, "reset music settings")
    return _notes(note)


@post("/music/request-channel", summary="Create the music request channel", responses=REFUSED)
async def create_request_channel(client: Client, guild: discord.Guild, member: discord.Member) -> MusicSettings:
    await music.create_request_channel(client, guild)
    _audit(member, "created the music request channel")
    return _music(guild)


@delete("/music/request-channel", summary="Delete the music request channel", status_code=200)
async def remove_request_channel(client: Client, guild: discord.Guild, member: discord.Member) -> Notes:
    note = await music.remove_request_channel(client, guild, member)
    _audit(member, "removed the music request channel")
    return _notes(note)


def _tickets(guild: discord.Guild) -> TicketSettings:
    settings = cache.get(guild.id)
    return TicketSettings(
        enabled=settings.ticket_cmds,
        category_id=id_of(tickets.category(guild)),
        support_role_ids=[str(role.id) for role in cards.support_roles(guild)],
        max_open=settings.ticket_max_open,
        confirm_close=settings.ticket_confirm_close,
        panel_channel_id=id_of(tickets.panel_channel(guild)),
    )


@get("/tickets", summary="Ticket commands, setup and panel")
async def get_ticket_settings(guild: discord.Guild) -> TicketSettings:
    return _tickets(guild)


@patch("/tickets", summary="Change ticket settings", responses=REFUSED)
async def update_ticket_settings(guild: discord.Guild, member: discord.Member, data: TicketPatch) -> TicketSettings:
    settings = cache.get(guild.id)
    if any(
        value is not UNSET for value in (data.category_id, data.support_role_ids, data.max_open, data.confirm_close)
    ):
        # The setup is saved as a whole, like the Discord modal, so fields left out keep their current values
        current = tickets.category(guild)
        await tickets.set_setup(
            guild,
            category=(
                resolve.category(guild, data.category_id)
                if data.category_id is not UNSET
                else current
                if isinstance(current, discord.CategoryChannel)
                else None
            ),
            support_roles=(
                resolve.roles(guild, data.support_role_ids)
                if data.support_role_ids is not UNSET
                else cards.support_roles(guild)
            ),
            max_open=data.max_open if data.max_open is not UNSET else settings.ticket_max_open,
            confirm_close=data.confirm_close if data.confirm_close is not UNSET else settings.ticket_confirm_close,
        )
    if data.enabled is not UNSET:
        await tickets.set_enabled(guild, data.enabled)
    _audit(member, "updated ticket settings")
    return _tickets(guild)


@delete("/tickets", summary="Reset ticket settings, removing the panel", status_code=200)
async def reset_ticket_settings(guild: discord.Guild, member: discord.Member) -> Notes:
    note = await tickets.reset(guild, member)
    _audit(member, "reset ticket settings")
    return _notes(note)


@post("/tickets/panel", summary="Create the ticket panel channel", responses=REFUSED)
async def create_ticket_panel(guild: discord.Guild, member: discord.Member) -> TicketSettings:
    await tickets.create_panel(guild)
    _audit(member, "created the ticket panel")
    return _tickets(guild)


@delete("/tickets/panel", summary="Remove the ticket panel", status_code=200)
async def remove_ticket_panel(guild: discord.Guild, member: discord.Member) -> Notes:
    note = await tickets.remove_panel(guild, member)
    _audit(member, "removed the ticket panel")
    return _notes(note)


@delete("/", summary="Reset every setting", status_code=200)
async def reset_all_settings(client: Client, guild: discord.Guild, member: discord.Member) -> Notes:
    notes = await reset_all(client, guild, member)
    _audit(member, "reset every setting")
    return _notes(*notes)


def _refused(request: Request, exc: SettingError) -> Response[Problem]:
    client: Client | None = request.app.state.client
    guild = client.get_guild(int(request.path_params["guild_id"])) if client else None
    return Response(Problem(detail=resolve.plain(guild, str(exc)) if guild else str(exc)), status_code=422)


router = Router(
    "/guilds/{guild_id:str}/settings",
    tags=["Settings"],
    exception_handlers={SettingError: _refused},
    dependencies={
        "guild": Provide(provide_guild, sync_to_thread=False),
        "member": Provide(provide_member, sync_to_thread=False),
    },
    route_handlers=[
        get_general_settings,
        update_general_settings,
        reset_general_settings,
        get_log_settings,
        update_log_settings,
        reset_log_settings,
        get_invite_settings,
        update_invite_settings,
        reset_invite_settings,
        reset_invite_counts,
        get_music_settings,
        update_music_settings,
        reset_music_settings,
        create_request_channel,
        remove_request_channel,
        get_ticket_settings,
        update_ticket_settings,
        reset_ticket_settings,
        create_ticket_panel,
        remove_ticket_panel,
        reset_all_settings,
    ],
)
