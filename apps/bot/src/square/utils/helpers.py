import datetime
import discord
import math
import re
from babel.numbers import format_compact_decimal
from babel.units import format_unit


def parse_duration(duration: str, max_duration: str | None = None, *, signed: bool = False) -> datetime.timedelta:
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

    if max_duration is not None:
        max_td = parse_duration(max_duration)
        if total_duration > max_td:
            raise ValueError(f"Total duration must not exceed `{max_duration}`.")

    elif total_duration.days > 28:
        raise ValueError("Total duration must be less than `28 days`.")

    return sign * total_duration


def fmt_perms(perms: list[str]) -> str:
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
    unit = 1000 ** max(int(math.log(abs(value), 1000)), 0) if value else 1
    # Rounded to the shown precision first, otherwise Babel turns 999,950 into "1000K" instead of "1M"
    return format_compact_decimal(round(value / unit, 1) * unit, locale="en", fraction_digits=1)


def fmt_count(value: int) -> str:
    return f"{value:,}" if abs(value) < 10_000 else fmt_number(value)


def member_counts(guild: discord.Guild) -> tuple[int, int, int]:
    bots = sum(1 for member in guild.members if member.bot)
    return guild.member_count or len(guild.members), len(guild.members) - bots, bots
