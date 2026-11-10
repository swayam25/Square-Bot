import discord
from square.db.funcs import invites as db
from square.settings.errors import SettingError
from square.utils import invites

MAX_FAKE_DAYS = 365


async def set_tracker(guild: discord.Guild, enabled: bool) -> None:
    await db.set_tracker(guild.id, enabled)
    await invites.refresh(guild)  # Starts or stops caching this server's invite uses


async def set_fake_days(guild: discord.Guild, days: int) -> None:
    """Accounts younger than this many days when they join count as fake."""
    if not 0 <= days <= MAX_FAKE_DAYS:
        raise SettingError(f"Enter a whole number of days from 0 to {MAX_FAKE_DAYS}.")
    await db.set_fake_days(guild.id, days)


async def reset_counts(guild: discord.Guild) -> None:
    await db.reset_invites(guild.id)


async def reset(guild: discord.Guild) -> None:
    await db.set_tracker(guild.id, False)
    await db.set_fake_days(guild.id, 7)
    await invites.refresh(guild)
