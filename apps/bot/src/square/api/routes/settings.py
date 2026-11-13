import asyncio
import discord
import logging
from collections import defaultdict
from collections.abc import Mapping
from litestar import Request, Response, Router, delete, get, patch, post
from litestar.di import Provide
from litestar.openapi import ResponseSpec
from msgspec import UNSET
from square.api import resolve
from square.api.auth import provide_guild, provide_member
from square.api.resolve import SettingError
from square.api.schemas import (
    AutoroleUser,
    GeneralPatch,
    GeneralSettings,
    InvitePatch,
    InviteSettings,
    LogChannels,
    LogPatch,
    LogSettings,
    ModulePatch,
    ModuleSettings,
    MusicPatch,
    MusicSettings,
    Notes,
    Problem,
    TicketPatch,
    TicketSettings,
    id_of,
    person_of,
)
from square.api.users import find_user
from square.cogs.tickets import cards
from square.cogs.tickets.panel import post as post_panel
from square.cogs.tickets.panel import unbind as unbind_panel
from square.core import Client
from square.db import cache
from square.db.funcs import dj as dj_db
from square.db.funcs import guild as guild_db
from square.db.funcs import invites as invites_db
from square.db.funcs import logs as logs_db
from square.db.funcs import tickets as tickets_db
from square.db.funcs.guild import remove_guild
from square.modules import Module
from square.music import request, stay
from square.music.core import can_play_in, get_player
from square.music.player import release_guild, render_player, stop_player
from square.music.utils import delete_quietly
from square.utils.invites import refresh as refresh_invites
from square.utils.server_log import LogType

log = logging.getLogger(__name__)

REFUSED = {422: ResponseSpec(data_container=Problem, description="The bot refused the change", generate_examples=False)}


def _audit(member: discord.Member, action: str) -> None:
    log.info("Dashboard: %s (%s) %s in %s (%s)", member, member.id, action, member.guild, member.guild.id)


def _notes(guild: discord.Guild, *notes: str | None) -> Notes:
    return Notes(notes=[resolve.plain(guild, note) for note in notes if note])


def _role_ids(guild: discord.Guild, role_ids: list[int]) -> list[str]:
    return [str(role_id) for role_id in role_ids if guild.get_role(role_id)]


async def _general(client: Client, guild: discord.Guild) -> GeneralSettings:
    settings = cache.get(guild.id)
    user_ids = list(settings.autorole_users)
    users = await asyncio.gather(*(find_user(client, guild, user_id) for user_id in user_ids))
    return GeneralSettings(
        autorole_ids=_role_ids(guild, settings.autorole_ids),
        autorole_bot_ids=_role_ids(guild, settings.autorole_bot_ids),
        autorole_split=settings.autorole_split,
        autorole_users=[
            AutoroleUser(
                user=person_of(user_id, user),
                member=isinstance(user, discord.Member),
                role_ids=_role_ids(guild, settings.autorole_users[user_id]),
            )
            for user_id, user in zip(user_ids, users, strict=True)
        ],
        media_only_channel_id=id_of(
            guild.get_channel(settings.media_only_channel_id) if settings.media_only_channel_id else None
        ),
    )


def _givable(guild: discord.Guild, role_ids: list[str]) -> list[int]:
    roles = resolve.roles(guild, role_ids)
    for role in roles:
        if role.managed or role >= guild.me.top_role:
            raise SettingError(f"I can't give out {role.mention}, it's above my role or managed.")
    return [role.id for role in roles]


async def _reset_general(guild: discord.Guild) -> None:
    await guild_db.set_autoroles(guild.id, humans=[], bots=[], split=False)
    await guild_db.set_autorole_users(guild.id, {})
    await guild_db.set_media_only(guild.id, None)


@get("/general", summary="Auto roles and media-only channel")
async def get_general_settings(client: Client, guild: discord.Guild) -> GeneralSettings:
    return await _general(client, guild)


@patch("/general", summary="Change the auto roles or media-only channel", responses=REFUSED)
async def update_general_settings(
    client: Client, guild: discord.Guild, member: discord.Member, data: GeneralPatch
) -> GeneralSettings:
    # Resolve and check everything first, so a refusal doesn't leave the change half applied
    humans = _givable(guild, data.autorole_ids) if data.autorole_ids is not UNSET else None
    bots = _givable(guild, data.autorole_bot_ids) if data.autorole_bot_ids is not UNSET else None
    split = data.autorole_split if data.autorole_split is not UNSET else None
    users = None
    if data.autorole_users is not UNSET:
        if len({entry.user_id for entry in data.autorole_users}) != len(data.autorole_users):
            raise SettingError("Each person can only be listed once.")
        users = {int(entry.user_id): _givable(guild, entry.role_ids) for entry in data.autorole_users}
    channel = (
        resolve.text_channel(guild, data.media_only_channel_id) if data.media_only_channel_id is not UNSET else UNSET
    )
    if channel:
        perms = channel.permissions_for(guild.me)
        if not (perms.send_messages and perms.manage_messages):
            raise SettingError(f"I need `Send Messages` and `Manage Messages` in {channel.mention}.")

    if humans is not None or bots is not None or split is not None:
        await guild_db.set_autoroles(guild.id, humans=humans, bots=bots, split=split)
    if users is not None:
        await guild_db.set_autorole_users(guild.id, users)
    if channel is not UNSET:
        await guild_db.set_media_only(guild.id, channel.id if channel else None)
    _audit(member, "updated general settings")
    return await _general(client, guild)


@delete("/general", summary="Reset general settings", status_code=200)
async def reset_general_settings(client: Client, guild: discord.Guild, member: discord.Member) -> GeneralSettings:
    await _reset_general(guild)
    _audit(member, "reset general settings")
    return await _general(client, guild)


def _logs(guild: discord.Guild) -> LogSettings:
    channels = cache.get(guild.id).log_channels
    return LogSettings(
        channels=LogChannels(
            **{
                key: str(channel_id)
                for key, channel_id in channels.items()
                if key in LogChannels.__struct_fields__ and guild.get_channel(channel_id)
            }
        )
    )


async def _set_log_channels(
    client: Client, guild: discord.Guild, changes: Mapping[LogType, discord.TextChannel | None]
) -> None:
    for channel in {channel for channel in changes.values() if channel}:
        perms = channel.permissions_for(guild.me)
        if not (perms.send_messages and perms.manage_webhooks):
            raise SettingError(f"I need `Send Messages` and `Manage Webhooks` in {channel.mention}.")

    by_channel: defaultdict[discord.TextChannel, list[str]] = defaultdict(list)
    for log_type, channel in changes.items():
        if channel:
            by_channel[channel].append(log_type.key)
        else:
            await logs_db.remove_log_channel(guild.id, log_type.key)
    for channel, keys in by_channel.items():
        await logs_db.set_all_log_channels(guild.id, keys, channel.id)
    client.dispatch("log_channels_update", guild.id)


async def _reset_logs(client: Client, guild: discord.Guild) -> None:
    await logs_db.remove_log_channel(guild.id)
    client.dispatch("log_channels_update", guild.id)


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
    await _set_log_channels(client, guild, changes)
    _audit(member, "updated log channels")
    return _logs(guild)


@delete("/logs", summary="Turn every log off", status_code=200)
async def reset_log_settings(client: Client, guild: discord.Guild, member: discord.Member) -> LogSettings:
    await _reset_logs(client, guild)
    _audit(member, "reset log channels")
    return _logs(guild)


def _invites(guild: discord.Guild) -> InviteSettings:
    settings = cache.get(guild.id)
    return InviteSettings(fake_days=settings.invite_fake_days)


async def _reset_invites(guild: discord.Guild) -> None:
    await invites_db.set_fake_days(guild.id, 7)


@get("/invites", summary="Fake account age")
async def get_invite_settings(guild: discord.Guild) -> InviteSettings:
    return _invites(guild)


@patch("/invites", summary="Change the fake account age", responses=REFUSED)
async def update_invite_settings(guild: discord.Guild, member: discord.Member, data: InvitePatch) -> InviteSettings:
    if data.fake_days is not UNSET:
        await invites_db.set_fake_days(guild.id, data.fake_days)
    _audit(member, "updated invite settings")
    return _invites(guild)


@delete("/invites", summary="Reset the fake account age", status_code=200)
async def reset_invite_settings(guild: discord.Guild, member: discord.Member) -> InviteSettings:
    await _reset_invites(guild)
    _audit(member, "reset invite settings")
    return _invites(guild)


@delete("/invites/counts", summary="Reset everyone's invite counts", status_code=200)
async def reset_invite_counts(guild: discord.Guild, member: discord.Member) -> InviteSettings:
    await invites_db.reset_invites(guild.id)
    _audit(member, "reset invite counts")
    return _invites(guild)


def _channel(guild: discord.Guild, channel_id: int | None) -> discord.abc.GuildChannel | None:
    return guild.get_channel(channel_id) if channel_id else None


def _music(guild: discord.Guild) -> MusicSettings:
    settings = cache.get(guild.id)
    return MusicSettings(
        request_channel_id=id_of(_channel(guild, request.channel_id(guild.id))),
        stay_channel_id=id_of(_channel(guild, stay.channel_id(guild.id))),
        dj_mode=settings.dj_mode,
        # Resolved against live roles, so a deleted role's leftover row never shows up
        dj_role_ids=[str(role_id) for role_id in settings.dj_roles if guild.get_role(role_id)],
    )


async def _remove_request_channel(client: Client, guild: discord.Guild, actor: discord.abc.User) -> str | None:
    channel_id = request.channel_id(guild.id)
    if channel_id is None:
        return None
    # Unbind first, so deleting the channel doesn't race the listener that watches for it
    await request.unbind(guild.id)
    note = None
    if (channel := guild.get_channel(channel_id)) is not None:
        try:
            await channel.delete(reason=f"Music channel removed by {actor}")
        except discord.HTTPException:
            note = f"I couldn't delete {channel.mention}, so it's yours to remove."
    await release_guild(client, guild.id)
    return note


async def _clear_stay_channel(client: Client, guild: discord.Guild) -> None:
    if stay.channel_id(guild.id) is None:
        return
    await stay.unbind(guild.id)
    if (player := get_player(client, guild.id)) is None:
        return
    if player.current:
        # Re-arms sonolink's disconnect timer, which 24/7 was holding off
        player.cancel_empty_timer()
        player._check_inactivity()
    else:
        await stop_player(player, guild, force=True)


async def _reset_music(client: Client, guild: discord.Guild, actor: discord.abc.User) -> str | None:
    note = await _remove_request_channel(client, guild, actor)
    await _clear_stay_channel(client, guild)
    await dj_db.remove_dj(guild.id)
    client.dispatch("music_update", guild.id)
    return note


@get("/music", summary="Request channel, 24/7 channel and DJ mode")
async def get_music_settings(guild: discord.Guild) -> MusicSettings:
    return _music(guild)


@patch("/music", summary="Change the 24/7 channel or DJ settings", responses=REFUSED)
async def update_music_settings(
    client: Client, guild: discord.Guild, member: discord.Member, data: MusicPatch
) -> MusicSettings:
    # Resolve and check everything first, so a refusal doesn't leave the change half applied
    stay_channel = resolve.voice_channel(guild, data.stay_channel_id) if data.stay_channel_id is not UNSET else UNSET
    dj_roles = resolve.roles(guild, data.dj_role_ids) if data.dj_role_ids is not UNSET else UNSET
    if stay_channel and not can_play_in(stay_channel):
        raise SettingError(f"I need the `Connect` and `Speak` permissions in {stay_channel.mention}.")

    if dj_roles is not UNSET:
        await dj_db.set_dj_roles(guild.id, [role.id for role in dj_roles])
        if dj_roles and not cache.get(guild.id).dj_mode:
            await dj_db.set_dj_mode(guild.id, True)
    # After the roles, so an explicit choice wins over the switch above
    if data.dj_mode is not UNSET:
        await dj_db.set_dj_mode(guild.id, data.dj_mode)
    if dj_roles is not UNSET or data.dj_mode is not UNSET:
        client.dispatch("music_update", guild.id)
    if stay_channel is None:
        await _clear_stay_channel(client, guild)
    elif stay_channel is not UNSET:
        await stay.bind(guild.id, stay_channel.id)
        try:
            await stay.join(client, guild.id)
        except Exception:
            stay.schedule_rejoin(client, guild.id)
    _audit(member, "updated music settings")
    return _music(guild)


@delete("/music", summary="Reset music settings, deleting the request channel", status_code=200)
async def reset_music_settings(client: Client, guild: discord.Guild, member: discord.Member) -> Notes:
    note = await _reset_music(client, guild, member)
    _audit(member, "reset music settings")
    return _notes(guild, note)


@post("/music/request-channel", summary="Create the music request channel", responses=REFUSED)
async def create_request_channel(client: Client, guild: discord.Guild, member: discord.Member) -> MusicSettings:
    """Creates a channel where anything typed is queued, with the player pinned."""
    if channel := _channel(guild, request.channel_id(guild.id)):
        raise SettingError(f"{channel.mention} is already the music request channel.")
    if not guild.me.guild_permissions.manage_channels:
        raise SettingError("I need the `Manage Channels` permission to create the channel.")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            add_reactions=False,
            attach_files=False,
            embed_links=False,
            create_public_threads=False,
            create_private_threads=False,
            send_messages_in_threads=False,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
        ),
    }
    try:
        channel = await guild.create_text_channel(
            "music-requests", overwrites=overwrites, topic="Send a track name or a link here to queue it."
        )
    except discord.HTTPException as exc:
        raise SettingError(f"I couldn't create the music channel: {exc.text or exc}") from exc
    await request.bind(guild.id, channel.id)
    request.prime(client, guild.id)
    await render_player(client, guild.id, wait=True)
    _audit(member, "created the music request channel")
    return _music(guild)


@delete("/music/request-channel", summary="Delete the music request channel", status_code=200)
async def remove_request_channel(client: Client, guild: discord.Guild, member: discord.Member) -> Notes:
    note = await _remove_request_channel(client, guild, member)
    _audit(member, "removed the music request channel")
    return _notes(guild, note)


def _ticket_category(guild: discord.Guild) -> discord.abc.GuildChannel | None:
    return _channel(guild, cache.get(guild.id).ticket_category_id)


def _ticket_panel_channel(guild: discord.Guild) -> discord.abc.GuildChannel | None:
    return _channel(guild, cache.get(guild.id).ticket_panel_channel_id)


def _tickets(guild: discord.Guild) -> TicketSettings:
    settings = cache.get(guild.id)
    return TicketSettings(
        category_id=id_of(_ticket_category(guild)),
        support_role_ids=[str(role.id) for role in cards.support_roles(guild)],
        max_open=settings.ticket_max_open,
        confirm_close=settings.ticket_confirm_close,
        panel_channel_id=id_of(_ticket_panel_channel(guild)),
    )


async def _remove_ticket_panel(guild: discord.Guild, actor: discord.abc.User) -> str | None:
    channel, message_id = _ticket_panel_channel(guild), cache.get(guild.id).ticket_panel_message_id
    # Unbind first, so the deletes below don't look like someone removing the panel
    await unbind_panel(guild.id)
    if not isinstance(channel, discord.TextChannel):
        return None
    try:
        only_panel = [message.id async for message in channel.history(limit=2)] in ([message_id], [])
    except discord.HTTPException:
        only_panel = False
    if only_panel:
        try:
            await channel.delete(reason=f"Ticket panel removed by {actor}")
            return None
        except discord.HTTPException:
            return f"I couldn't delete {channel.mention}, so it's yours to remove."
    if message_id:
        await delete_quietly(channel.get_partial_message(message_id))
    return f"I removed the panel but kept {channel.mention}, since it has other messages."


async def _reset_tickets(guild: discord.Guild, actor: discord.abc.User) -> str | None:
    note = await _remove_ticket_panel(guild, actor)
    await tickets_db.reset_ticket_settings(guild.id)
    return note


@get("/tickets", summary="Ticket setup and panel")
async def get_ticket_settings(guild: discord.Guild) -> TicketSettings:
    return _tickets(guild)


@patch("/tickets", summary="Change ticket settings", responses=REFUSED)
async def update_ticket_settings(guild: discord.Guild, member: discord.Member, data: TicketPatch) -> TicketSettings:
    settings = cache.get(guild.id)
    if any(
        value is not UNSET for value in (data.category_id, data.support_role_ids, data.max_open, data.confirm_close)
    ):
        current = _ticket_category(guild)
        category = (
            resolve.category(guild, data.category_id)
            if data.category_id is not UNSET
            else current
            if isinstance(current, discord.CategoryChannel)
            else None
        )
        support_roles = (
            resolve.roles(guild, data.support_role_ids)
            if data.support_role_ids is not UNSET
            else cards.support_roles(guild)
        )
        await tickets_db.set_ticket_setup(
            guild.id,
            category_id=category.id if category else None,
            support_role_ids=[role.id for role in support_roles],
            max_open=data.max_open if data.max_open is not UNSET else settings.ticket_max_open,
            confirm_close=data.confirm_close if data.confirm_close is not UNSET else settings.ticket_confirm_close,
        )
    _audit(member, "updated ticket settings")
    return _tickets(guild)


@delete("/tickets", summary="Reset ticket settings, removing the panel", status_code=200)
async def reset_ticket_settings(guild: discord.Guild, member: discord.Member) -> Notes:
    note = await _reset_tickets(guild, member)
    _audit(member, "reset ticket settings")
    return _notes(guild, note)


@post("/tickets/panel", summary="Create the ticket panel channel", responses=REFUSED)
async def create_ticket_panel(guild: discord.Guild, member: discord.Member) -> TicketSettings:
    """Creates a read-only channel holding the "Open a ticket" panel, kept up to date like the music card."""
    if channel := _ticket_panel_channel(guild):
        raise SettingError(f"{channel.mention} already holds the ticket panel.")
    if not guild.me.guild_permissions.manage_channels:
        raise SettingError("I need the `Manage Channels` permission to create the channel.")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=False,
            add_reactions=False,
            create_public_threads=False,
            create_private_threads=False,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            manage_messages=True,
            embed_links=True,
        ),
    }
    try:
        channel = await guild.create_text_channel(
            "tickets", overwrites=overwrites, topic="Press the button to open a private ticket with staff."
        )
        await post_panel(channel)
    except discord.HTTPException as exc:
        raise SettingError(f"I couldn't create the ticket channel: {exc.text or exc}") from exc
    _audit(member, "created the ticket panel")
    return _tickets(guild)


@delete("/tickets/panel", summary="Remove the ticket panel", status_code=200)
async def remove_ticket_panel(guild: discord.Guild, member: discord.Member) -> Notes:
    note = await _remove_ticket_panel(guild, member)
    _audit(member, "removed the ticket panel")
    return _notes(guild, note)


def _modules(guild: discord.Guild) -> ModuleSettings:
    return ModuleSettings(**{module.value: cache.enabled(guild.id, module) for module in Module})


@get("/modules", summary="Which modules are turned on")
async def get_module_settings(guild: discord.Guild) -> ModuleSettings:
    return _modules(guild)


@patch("/modules", summary="Turn modules on or off")
async def update_module_settings(guild: discord.Guild, member: discord.Member, data: ModulePatch) -> ModuleSettings:
    for module in Module:
        if (on := getattr(data, module.value)) is not UNSET:
            await guild_db.set_module(guild.id, module, on)
    await refresh_invites(guild)
    _audit(member, "updated modules")
    return _modules(guild)


@delete("/", summary="Reset every setting", status_code=200)
async def reset_all_settings(client: Client, guild: discord.Guild, member: discord.Member) -> Notes:
    """Resets every setting and drops the server's row."""
    await _reset_general(guild)
    await _reset_logs(client, guild)
    notes = [await _reset_music(client, guild, member), await _reset_tickets(guild, member)]
    await _reset_invites(guild)
    await remove_guild(guild.id)
    await refresh_invites(guild)
    request.forget(guild.id)
    stay.forget(guild.id)
    client.dispatch("log_channels_update", guild.id)
    _audit(member, "reset every setting")
    return _notes(guild, *notes)


def refused(request: Request, exc: SettingError) -> Response[Problem]:
    client: Client | None = request.app.state.client
    guild = client.get_guild(int(request.path_params["guild_id"])) if client else None
    return Response(Problem(detail=resolve.plain(guild, str(exc)) if guild else str(exc)), status_code=422)


router = Router(
    "/guilds/{guild_id:str}/settings",
    tags=["Settings"],
    exception_handlers={SettingError: refused},
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
        get_module_settings,
        update_module_settings,
        reset_all_settings,
    ],
)
