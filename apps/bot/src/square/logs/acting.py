import discord
import time

# Long enough for a ban that waits on a DM first, short enough that a stale entry can't name the wrong moderator
FRESH_SECONDS = 60

_acting: dict[tuple[int, discord.AuditLogAction, int], tuple[str, float]] = {}


def acting(guild_id: int, action: discord.AuditLogAction, target_id: int, moderator: discord.abc.User | str) -> None:
    """
    Remembers who asked Square to do something, so its audit log entry names them instead of Square.

    `moderator` is a user, or a label such as "AutoMod" when Square acts on its own.
    """
    now = time.monotonic()
    label = moderator if isinstance(moderator, str) else f"{moderator.mention} (`{moderator.name}`)"
    _acting[(guild_id, action, target_id)] = (label, now)
    if len(_acting) > 500:
        for key in [key for key, (_, at) in _acting.items() if now - at > FRESH_SECONDS]:
            del _acting[key]


def acted_for(guild_id: int, action: discord.AuditLogAction, target_id: int) -> str | None:
    """Kept until it goes stale, since one purge or mass action writes several audit log entries."""
    found = _acting.get((guild_id, action, target_id))
    if found and time.monotonic() - found[1] <= FRESH_SECONDS:
        return found[0]
    return None
