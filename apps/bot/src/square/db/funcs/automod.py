from square.db import cache
from square.db.funcs.guild import fetch_guild_settings
from square.db.schema import AutomodRuleTable, WarningTable, WarnPunishmentTable
from tortoise.transactions import in_transaction
from typing import Any


def rules(guild_id: int) -> dict[str, AutomodRuleTable]:
    return cache.get(guild_id).automod_rules


def punishments(guild_id: int) -> list[WarnPunishmentTable]:
    return cache.get(guild_id).warn_punishments


async def save_rules(guild_id: int, changed: dict[str, dict[str, Any]]) -> None:
    guild = await fetch_guild_settings(guild_id)
    saved: dict[str, AutomodRuleTable] = {}
    async with in_transaction():
        for kind, values in changed.items():
            rule, created = await AutomodRuleTable.get_or_create(guild=guild, kind=kind, defaults=values)
            if not created:
                rule.update_from_dict(values)
                await rule.save(update_fields=list(values))
            saved[kind] = rule
    cache.entry(guild_id).automod_rules.update(saved)


async def set_punishments(guild_id: int, steps: list[tuple[int, str, int | None]]) -> None:
    guild = await fetch_guild_settings(guild_id)
    async with in_transaction():
        await WarnPunishmentTable.filter(guild=guild).delete()
        await WarnPunishmentTable.bulk_create(
            [
                WarnPunishmentTable(guild=guild, warnings=warnings, action=action, seconds=seconds)
                for warnings, action, seconds in sorted(steps)
            ]
        )
    cache.entry(guild_id).warn_punishments = await WarnPunishmentTable.filter(guild=guild).order_by("warnings")


async def reset(guild_id: int) -> None:
    await AutomodRuleTable.filter(guild__guild_id=guild_id).delete()
    await WarnPunishmentTable.filter(guild__guild_id=guild_id).delete()
    settings = cache.entry(guild_id)
    settings.automod_rules, settings.warn_punishments = {}, []


async def add_warning(guild_id: int, user_id: int, moderator_id: int | None, reason: str) -> tuple[WarningTable, int]:
    guild = await fetch_guild_settings(guild_id)
    warning = await WarningTable.create(guild=guild, user_id=user_id, moderator_id=moderator_id, reason=reason)
    return warning, await WarningTable.filter(guild=guild, user_id=user_id).count()


async def fetch_warnings(guild_id: int, user_id: int, limit: int) -> tuple[list[WarningTable], int]:
    query = WarningTable.filter(guild__guild_id=guild_id, user_id=user_id)
    return await query.order_by("-id").limit(limit), await query.count()


async def remove_warning(guild_id: int, warning_id: int) -> WarningTable | None:
    warning = await WarningTable.filter(guild__guild_id=guild_id, id=warning_id).first()
    if warning:
        await warning.delete()
    return warning


async def clear_warnings(guild_id: int, user_id: int) -> int:
    return await WarningTable.filter(guild__guild_id=guild_id, user_id=user_id).delete()
