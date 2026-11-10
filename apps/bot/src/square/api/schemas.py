import discord
import msgspec
from square.db.cache import GuildSettings
from typing import Annotated

# Discord IDs go past JavaScript's safe integer range, so the API sends them as strings
Snowflake = Annotated[str, msgspec.Meta(pattern=r"^\d{17,20}$", description="A Discord ID")]


class Schema(msgspec.Struct, rename="camel", kw_only=True):
    pass


class Health(Schema):
    ready: bool
    guilds: int
    latency_ms: int | None


class Guild(Schema):
    id: Snowflake
    name: str
    icon_url: str | None
    member_count: int


class Settings(Schema):
    ticket_cmds: bool
    media_only_channel_id: Snowflake | None
    autorole: Snowflake | None
    dj_mode: bool
    dj_roles: list[Snowflake]
    music_channel_id: Snowflake | None
    music_message_id: Snowflake | None
    music_stay_channel_id: Snowflake | None
    invite_tracker: bool
    invite_fake_days: int
    ticket_category_id: Snowflake | None
    ticket_support_role_ids: list[Snowflake]
    ticket_panel_channel_id: Snowflake | None
    ticket_panel_message_id: Snowflake | None
    ticket_max_open: int
    ticket_confirm_close: bool
    log_channels: dict[str, Snowflake]


def _id(value: int | None) -> str | None:
    return None if value is None else str(value)


def guild_out(guild: discord.Guild) -> Guild:
    return Guild(
        id=str(guild.id),
        name=guild.name,
        icon_url=guild.icon.url if guild.icon else None,
        member_count=guild.member_count or 0,
    )


def settings_out(settings: GuildSettings) -> Settings:
    return Settings(
        ticket_cmds=settings.ticket_cmds,
        media_only_channel_id=_id(settings.media_only_channel_id),
        autorole=_id(settings.autorole),
        dj_mode=settings.dj_mode,
        dj_roles=[str(role_id) for role_id in settings.dj_roles],
        music_channel_id=_id(settings.music_channel_id),
        music_message_id=_id(settings.music_message_id),
        music_stay_channel_id=_id(settings.music_stay_channel_id),
        invite_tracker=settings.invite_tracker,
        invite_fake_days=settings.invite_fake_days,
        ticket_category_id=_id(settings.ticket_category_id),
        ticket_support_role_ids=[str(role_id) for role_id in settings.ticket_support_role_ids],
        ticket_panel_channel_id=_id(settings.ticket_panel_channel_id),
        ticket_panel_message_id=_id(settings.ticket_panel_message_id),
        ticket_max_open=settings.ticket_max_open,
        ticket_confirm_close=settings.ticket_confirm_close,
        log_channels={log_type: str(channel_id) for log_type, channel_id in settings.log_channels.items()},
    )
