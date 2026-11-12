import discord
from square.db import cache
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import GuildTable, TicketMemberTable, TicketTable
from tortoise.transactions import in_transaction


async def set_ticket_setup(
    guild_id: int, *, category_id: int | None, support_role_ids: list[int], max_open: int, confirm_close: bool
) -> None:
    """
    Saves the ticket setup modal: category, support roles, open tickets per member and close confirmation.

    Args:
        guild_id (int): The guild ID to perform action on.
        category_id (int | None): The category new tickets go in, or None to create one on the next ticket.
        support_role_ids (list[int]): Roles that can see, claim and manage every ticket.
        max_open (int): How many open tickets a member may have at once.
        confirm_close (bool): Whether closing asks for a second click.
    """
    guild = await fetch_guild_settings(guild_id)
    guild.ticket_category_id = category_id
    guild.ticket_support_role_ids = support_role_ids
    guild.ticket_max_open = max_open
    guild.ticket_confirm_close = confirm_close
    await guild.save(
        update_fields=["ticket_category_id", "ticket_support_role_ids", "ticket_max_open", "ticket_confirm_close"]
    )
    settings = cache.entry(guild_id)
    settings.ticket_category_id, settings.ticket_support_role_ids = category_id, list(support_role_ids)
    settings.ticket_max_open, settings.ticket_confirm_close = max_open, confirm_close


async def set_ticket_category(guild_id: int, category_id: int | None) -> None:
    """
    Remembers the category the bot created for tickets.

    Args:
        guild_id (int): The guild ID to perform action on.
        category_id (int | None): The category ID.
    """
    guild = await fetch_guild_settings(guild_id)
    guild.ticket_category_id = category_id
    await guild.save(update_fields=["ticket_category_id"])
    cache.entry(guild_id).ticket_category_id = category_id


async def set_ticket_panel(guild_id: int, channel_id: int | None, message_id: int | None) -> None:
    """
    Remembers where the "Open a ticket" panel was posted.

    Args:
        guild_id (int): The guild ID to perform action on.
        channel_id (int | None): The panel's channel.
        message_id (int | None): The panel message.
    """
    guild = await fetch_guild_settings(guild_id)
    guild.ticket_panel_channel_id, guild.ticket_panel_message_id = channel_id, message_id
    await guild.save(update_fields=["ticket_panel_channel_id", "ticket_panel_message_id"])
    settings = cache.entry(guild_id)
    settings.ticket_panel_channel_id, settings.ticket_panel_message_id = channel_id, message_id


async def reset_ticket_settings(guild_id: int) -> None:
    """
    Puts the ticket setup back to its defaults. Ticket numbers keep counting up.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    await set_ticket_setup(guild_id, category_id=None, support_role_ids=[], max_open=1, confirm_close=True)
    await set_ticket_panel(guild_id, None, None)


async def create_ticket(guild_id: int, channel_id: int, opener_id: int, reason: str, number: int) -> TicketTable:
    """
    Stores a new open ticket.

    Args:
        guild_id (int): The guild ID to perform action on.
        channel_id (int): The ticket's channel.
        opener_id (int): Who opened it.
        reason (str): Why.
        number (int): Its number from `reserve_ticket_number`.
    """
    guild = await fetch_guild_settings(guild_id)
    return await TicketTable.create(
        guild=guild, number=number, channel_id=channel_id, opener_id=opener_id, reason=reason
    )


async def reserve_ticket_number(guild_id: int) -> int:
    """
    Hands out the guild's next ticket number. The row lock means two tickets opened at once can't share a number.

    Args:
        guild_id (int): The guild ID to perform action on.
    """
    await fetch_guild_settings(guild_id)  # Makes sure the row exists before locking it
    async with in_transaction() as conn:
        guild = await GuildTable.filter(guild_id=guild_id).select_for_update().using_db(conn).get()
        number = guild.ticket_next_number
        guild.ticket_next_number = number + 1
        await guild.save(using_db=conn, update_fields=["ticket_next_number"])
    return number


async def fetch_ticket(channel_id: int) -> TicketTable | None:
    """
    The ticket living in a channel, if any.

    Args:
        channel_id (int): The channel to look up.
    """
    return await TicketTable.filter(channel_id=channel_id).first()


async def count_open_tickets(guild_id: int, opener_id: int) -> list[int]:
    """
    Channel IDs of a member's open tickets.

    Args:
        guild_id (int): The guild ID to perform action on.
        opener_id (int): The member.
    """
    rows = await TicketTable.filter(guild__guild_id=guild_id, opener_id=opener_id, status="open").values("channel_id")
    return [row["channel_id"] for row in rows]


async def fetch_ticket_members(ticket: TicketTable) -> list[int]:
    """User IDs added to a ticket besides its opener."""
    return [row["user_id"] for row in await TicketMemberTable.filter(ticket=ticket).values("user_id")]


async def add_ticket_member(ticket: TicketTable, user_id: int, added_by: int) -> None:
    await TicketMemberTable.get_or_create(ticket=ticket, user_id=user_id, defaults={"added_by": added_by})


async def remove_ticket_member(ticket: TicketTable, user_id: int) -> None:
    await TicketMemberTable.filter(ticket=ticket, user_id=user_id).delete()


async def save_ticket(ticket: TicketTable, **changes) -> None:
    """
    Updates a ticket's fields, e.g. `status="closed", closed_by=...`.

    Args:
        ticket (:class:`TicketTable`): The ticket to update.
        **changes: Field names and their new values.
    """
    if changes.get("status") == "closed":
        changes.setdefault("closed_at", discord.utils.utcnow())
    for name, value in changes.items():
        setattr(ticket, name, value)
    await ticket.save(update_fields=list(changes))
