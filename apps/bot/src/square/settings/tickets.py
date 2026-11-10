import discord
from square.cogs.tickets.panel import post as post_panel
from square.cogs.tickets.panel import unbind as unbind_panel
from square.db import cache
from square.db.funcs import guild as guild_db
from square.db.funcs import tickets as db
from square.music.utils import delete_quietly
from square.settings.errors import SettingError
from typing import Literal, get_args

MaxOpen = Literal[1, 2, 3, 5]
OPEN_LIMITS: tuple[int, ...] = get_args(MaxOpen)
MAX_SUPPORT_ROLES = 10


def category(guild: discord.Guild) -> discord.abc.GuildChannel | None:
    category_id = cache.get(guild.id).ticket_category_id
    return guild.get_channel(category_id) if category_id else None


def panel_channel(guild: discord.Guild) -> discord.abc.GuildChannel | None:
    channel_id = cache.get(guild.id).ticket_panel_channel_id
    return guild.get_channel(channel_id) if channel_id else None


async def set_enabled(guild: discord.Guild, enabled: bool) -> None:
    """Turns the ticket commands on or off."""
    await guild_db.set_ticket_cmds(guild.id, enabled)


async def set_setup(
    guild: discord.Guild,
    *,
    category: discord.CategoryChannel | None,
    support_roles: list[discord.Role],
    max_open: int,
    confirm_close: bool,
) -> None:
    """Saves where tickets go, who handles them, how many a member may open and whether closing asks first."""
    if len(support_roles) > MAX_SUPPORT_ROLES:
        raise SettingError(f"Pick up to {MAX_SUPPORT_ROLES} support roles.")
    if max_open not in OPEN_LIMITS:
        raise SettingError(f"Open tickets per member must be one of {', '.join(map(str, OPEN_LIMITS))}.")
    await db.set_ticket_setup(
        guild.id,
        category_id=category.id if category else None,
        support_role_ids=[role.id for role in support_roles],
        max_open=max_open,
        confirm_close=confirm_close,
    )


async def create_panel(guild: discord.Guild) -> discord.TextChannel:
    """Creates a read-only channel holding the "Open a ticket" panel, kept up to date like the music card."""
    if channel := panel_channel(guild):
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
    return channel


async def remove_panel(guild: discord.Guild, actor: discord.abc.User) -> str | None:
    """
    Unbinds the panel and deletes its channel. Returns a note when the channel had to be left behind.

    Panels posted before the bot made its own channel sit in channels people chat in, so a channel is only deleted
    when the panel is all it holds. Otherwise just the panel goes.
    """
    channel, message_id = panel_channel(guild), cache.get(guild.id).ticket_panel_message_id
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


async def reset(guild: discord.Guild, actor: discord.abc.User) -> str | None:
    """Clears the page. Returns a note when the panel's channel had to be left behind."""
    note = await remove_panel(guild, actor)
    await guild_db.set_ticket_cmds(guild.id, False)
    await db.reset_ticket_settings(guild.id)
    return note
