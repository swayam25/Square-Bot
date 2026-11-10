import datetime
import discord
import math
import re
from babel.numbers import format_compact_decimal
from babel.units import format_unit


def parse_duration(duration: str, max_duration: str | None = None, *, signed: bool = False) -> datetime.timedelta:
    """
    Parse a duration string into a timedelta object.

    Args:
        duration (str): A string representing the duration, e.g., "2w3d4h5m6s".
        max_duration (str | None): An optional maximum duration string, e.g., "2w3d".
        signed (bool): Accept a leading ``+``/``-`` applying to the whole duration, e.g. ``"-1m20s"`` is 80 seconds back.
    """
    duration = duration.strip()
    sign = 1
    if signed and duration[:1] in ("+", "-"):
        sign = -1 if duration[0] == "-" else 1
        duration = duration[1:]
    pattern = re.compile(r"(?P<value>\d+)(?P<unit>[wdhms])")
    matches = pattern.findall(duration)

    if not matches:
        raise ValueError(
            "Invalid duration format.\n-# Use `w` for weeks, `d` for days, `h` for hours, `m` for minutes, and `s` for seconds."
        )

    total_duration = datetime.timedelta()
    funcs = {
        "w": lambda x: datetime.timedelta(weeks=x),
        "d": lambda x: datetime.timedelta(days=x),
        "h": lambda x: datetime.timedelta(hours=x),
        "m": lambda x: datetime.timedelta(minutes=x),
        "s": lambda x: datetime.timedelta(seconds=x),
    }

    for value, unit in matches:
        value = int(value)
        if value <= 0:
            raise ValueError("Duration values must be positive.")
        total_duration += funcs[unit](value)

    if total_duration.total_seconds() <= 0:
        raise ValueError("Total duration must be positive.")

    # Check against max_duration if provided
    if max_duration is not None:
        max_td = parse_duration(max_duration)
        if total_duration > max_td:
            raise ValueError(f"Total duration must not exceed `{max_duration}`.")

    elif total_duration.days > 28:
        raise ValueError("Total duration must be less than `28 days`.")

    return sign * total_duration


def fmt_perms(perms: list[str]) -> str:
    """
    Format a list of permissions into a human-readable string.

    Args:
        perms (list[str]): A list of permission names.

    Returns:
        str: A formatted string of permissions.
    """
    perms = [perm.replace("_", " ").replace("guild", "server").title() for perm in perms]
    if not perms:
        return "No permissions"
    if len(perms) == 1:
        return perms[0]
    return ", ".join(perms[:-1]) + " and " + perms[-1]


def fmt_memory(bytes_value):
    gb = round(bytes_value / 1024 / 1024 / 1024, 2)
    mb = round(bytes_value / 1024 / 1024, 2)
    if gb >= 1:
        return format_unit(gb, "digital-gigabyte", "short", locale="en")
    else:
        return format_unit(mb, "digital-megabyte", "short", locale="en")


def fmt_number(value: int | float) -> str:
    """
    Formats a number in CLDR short compact form: 999, 1K, 1.3K, 12.3K, 1.5M, 2.3B.

    Args:
        value (int | float): The number to format.
    """
    unit = 1000 ** max(int(math.log(abs(value), 1000)), 0) if value else 1
    # Rounded to the shown precision first, otherwise Babel turns 999,950 into "1000K" instead of "1M"
    return format_compact_decimal(round(value / unit, 1) * unit, locale="en", fraction_digits=1)


def fmt_count(value: int) -> str:
    """
    Formats a count in full up to 9,999 and compactly after, like `fmt_number`: 1,284, 12.3K, 2.4M.

    For counts on cards and the website, where four digits still fit but longer ones would crowd the layout.
    """
    return f"{value:,}" if abs(value) < 10_000 else fmt_number(value)


def member_counts(guild: discord.Guild) -> tuple[int, int, int]:
    """
    Counts a guild's members in one pass over the member cache.

    Returns:
        tuple[int, int, int]: Total members, humans and bots.
    """
    bots = sum(1 for member in guild.members if member.bot)
    return guild.member_count or len(guild.members), len(guild.members) - bots, bots
