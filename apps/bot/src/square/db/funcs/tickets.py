import discord
from square.db import cache
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import GuildTable, TicketMemberTable, TicketTable
from tortoise.transactions import in_transaction


async def set_ticket_setup(
    guild_id: int, *, category_id: int | None, support_role_ids: list[int], max_open: int, confirm_close: bool
) -> None:
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
    guild = await fetch_guild_settings(guild_id)
    guild.ticket_category_id = category_id
    await guild.save(update_fields=["ticket_category_id"])
    cache.entry(guild_id).ticket_category_id = category_id


async def set_ticket_panel(guild_id: int, channel_id: int | None, message_id: int | None) -> None:
    guild = await fetch_guild_settings(guild_id)
    guild.ticket_panel_channel_id, guild.ticket_panel_message_id = channel_id, message_id
    await guild.save(update_fields=["ticket_panel_channel_id", "ticket_panel_message_id"])
    settings = cache.entry(guild_id)
    settings.ticket_panel_channel_id, settings.ticket_panel_message_id = channel_id, message_id


async def reset_ticket_settings(guild_id: int) -> None:
    await set_ticket_setup(guild_id, category_id=None, support_role_ids=[], max_open=1, confirm_close=True)
    await set_ticket_panel(guild_id, None, None)


async def create_ticket(guild_id: int, channel_id: int, opener_id: int, reason: str, number: int) -> TicketTable:
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
    await fetch_guild_settings(guild_id)
    async with in_transaction() as conn:
        guild = await GuildTable.filter(guild_id=guild_id).select_for_update().using_db(conn).get()
        number = guild.ticket_next_number
        guild.ticket_next_number = number + 1
        await guild.save(using_db=conn, update_fields=["ticket_next_number"])
    return number


async def fetch_ticket(channel_id: int) -> TicketTable | None:
    return await TicketTable.filter(channel_id=channel_id).first()


async def count_open_tickets(guild_id: int, opener_id: int) -> list[int]:
    rows = await TicketTable.filter(guild__guild_id=guild_id, opener_id=opener_id, status="open").values("channel_id")
    return [row["channel_id"] for row in rows]


async def fetch_ticket_members(ticket: TicketTable) -> list[int]:
    return [row["user_id"] for row in await TicketMemberTable.filter(ticket=ticket).values("user_id")]


async def add_ticket_member(ticket: TicketTable, user_id: int, added_by: int) -> None:
    await TicketMemberTable.get_or_create(ticket=ticket, user_id=user_id, defaults={"added_by": added_by})


async def remove_ticket_member(ticket: TicketTable, user_id: int) -> None:
    await TicketMemberTable.filter(ticket=ticket, user_id=user_id).delete()


async def save_ticket(ticket: TicketTable, **changes) -> None:
    if changes.get("status") == "closed":
        changes.setdefault("closed_at", discord.utils.utcnow())
    for name, value in changes.items():
        setattr(ticket, name, value)
    await ticket.save(update_fields=list(changes))
