import datetime
import re


def parse_duration(duration: str) -> datetime.timedelta:
    """
    Parse a duration string into a timedelta object.

    Parameters:
        duration (str): A string representing the duration, e.g., "2w3d4h5m6s".
    """
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
    elif total_duration.days > 28:
        raise ValueError("Total duration must be less than `28 days`.")

    return total_duration


def fmt_perms(perms: list[str]) -> str:
    """
    Format a list of permissions into a human-readable string.

    Parameters:
        perms (list[str]): A list of permission names.

    Returns:
        str: A formatted string of permissions.
    """
    perms = [perm.replace("_", " ").replace("guild", "server").title() for perm in perms]
    if len(perms) > 2:
        return "{}, and {}".format("**, **".join(perms[:-1]), perms[-1])
    elif len(perms) == 2:
        return "{} and {}".format("**".join(perms[:-1]), perms[-1])
    elif perms:
        return perms[0]
    else:
        return "No permissions"
