import discord
from litestar import Router, delete, get, patch, post
from litestar.di import Provide
from litestar.params import Parameter
from msgspec import UNSET, structs
from square.api import resolve
from square.api.auth import provide_guild
from square.api.refusals import REFUSED, refused
from square.api.resolve import SettingError
from square.api.schemas import (
    MAX_NATIVE_ALLOW,
    NATIVE_LIMITS,
    AutomodHit,
    AutomodPatch,
    AutomodSettings,
    AutomodTest,
    AutomodTestResult,
    NativeRule,
    NativeRuleCreate,
    NativeRulePatch,
    Punishment,
    SquareRule,
)
from square.cogs.automod import rules
from square.cogs.automod.rules import DEFAULTS, KINDS, LABELS
from square.core import Client
from square.db.funcs import automod as automod_db
from square.db.schema import AutomodRuleTable
from square.utils.helpers import fmt_count, plural
from typing import Annotated, Any

RuleId = Annotated[str, Parameter(pattern=r"^\d{17,20}$", description="A Discord AutoMod rule ID")]

# (lowest, highest) for each kind's amount and seconds
_RANGES: dict[str, tuple[tuple[int, int] | None, tuple[int, int] | None]] = {
    "media": (None, None),
    "invites": (None, None),
    "masked_links": (None, None),
    "new_members": ((1, 1440), None),
    "flood": ((2, 50), (2, 60)),
    "duplicates": ((1, 20), (5, 600)),
    "mention_flood": ((2, 100), (5, 300)),
    "file_flood": ((2, 50), (2, 60)),
    "ghost_pings": (None, (5, 600)),
    "caps": ((50, 95), None),
    "emojis": ((1, 100), None),
    "zalgo": ((2, 20), None),
    "fonts": ((0, 90), None),
    "repeated_chars": ((3, 50), None),
    "lines": ((3, 100), None),
    "invisible": (None, None),
}
_UNITS = {
    "new_members": "minutes",
    "flood": "messages",
    "duplicates": "repeats",
    "mention_flood": "mentions",
    "file_flood": "files",
    "caps": "percent",
    "emojis": "emojis",
    "zalgo": "marks",
    "fonts": "percent",
    "repeated_chars": "characters",
    "lines": "lines",
}

_TRIGGERS = {1: "keyword", 3: "spam", 4: "preset", 5: "mention_spam", 6: "member_profile"}
_TRIGGER_IDS = {name: value for value, name in _TRIGGERS.items()}
_PRESETS = {1: "profanity", 2: "sexual_content", 3: "slurs"}
_PRESET_IDS = {name: value for value, name in _PRESETS.items()}
_WORD_TRIGGERS = ("keyword", "member_profile")
_TIMEOUT_TRIGGERS = ("keyword", "mention_spam")
_MENTION_LIMIT = 20
_BLOCK, _ALERT, _TIMEOUT, _BLOCK_INTERACTION = 1, 2, 3, 4


def _ids(values: list[int]) -> list[str]:
    return [str(value) for value in values]


def _square_rule(kind: str, rule: AutomodRuleTable | None) -> SquareRule:
    if rule is None:
        amount, seconds = DEFAULTS[kind]
        return SquareRule(
            kind=kind,  # type: ignore[arg-type]
            enabled=False,
            amount=amount,
            seconds=seconds,
            channel_ids=[],
            delete=kind != "ghost_pings",
            warn=False,
            notify=True,
            exempt_role_ids=[],
            exempt_channel_ids=[],
        )
    return SquareRule(
        kind=kind,  # type: ignore[arg-type]
        enabled=rule.enabled,
        amount=rule.amount,
        seconds=rule.seconds,
        channel_ids=_ids(rule.channel_ids),
        delete=rule.delete_message,
        warn=rule.warn,
        notify=rule.notify,
        exempt_role_ids=_ids(rule.exempt_role_ids),
        exempt_channel_ids=_ids(rule.exempt_channel_ids),
    )


def _settings(guild: discord.Guild) -> AutomodSettings:
    saved = automod_db.rules(guild.id)
    return AutomodSettings(
        rules=[_square_rule(kind, saved.get(kind)) for kind in KINDS],
        punishments=[
            Punishment(warnings=step.warnings, action=step.action, seconds=step.seconds)  # type: ignore[arg-type]
            for step in automod_db.punishments(guild.id)
        ],
    )


def _in_range(value: int | None, bounds: tuple[int, int] | None, what: str) -> int | None:
    if bounds is None:
        return None
    low, high = bounds
    if value is None or not low <= value <= high:
        raise SettingError(f"{what} must be between {low} and {high}.")
    return value


def _channels(guild: discord.Guild, channel_ids: list[str]) -> list[int]:
    found = [guild.get_channel(int(channel_id)) for channel_id in dict.fromkeys(channel_ids)]
    if any(channel is None for channel in found):
        raise SettingError("One of those channels isn't in this server.")
    return [channel.id for channel in found if channel]


def _rule_values(guild: discord.Guild, rule: SquareRule) -> dict[str, Any]:
    label = LABELS[rule.kind]
    amount_range, seconds_range = _RANGES[rule.kind]
    ghost = rule.kind == "ghost_pings"
    if rule.enabled and ghost and not (rule.notify or rule.warn):
        raise SettingError(f"{label} needs to post who was pinged, warn, or both.")
    if rule.enabled and not ghost and not (rule.delete or rule.warn):
        raise SettingError(f"{label} needs to delete the message, warn, or both.")
    media = [channel.id for value in dict.fromkeys(rule.channel_ids) if (channel := resolve.text_channel(guild, value))]
    if rule.kind == "media":
        if rule.enabled and not media:
            raise SettingError("Pick at least one media-only channel.")
        for channel_id in media:
            channel = guild.get_channel(channel_id)
            if channel and not channel.permissions_for(guild.me).manage_messages:
                raise SettingError(f"Square needs `Manage Messages` in {channel.mention}.")
    return {
        "enabled": rule.enabled,
        "amount": _in_range(rule.amount, amount_range, f"{label} {_UNITS.get(rule.kind, '')}".strip()),
        "seconds": _in_range(rule.seconds, seconds_range, f"{label} seconds"),
        "channel_ids": media if rule.kind == "media" else [],
        "delete_message": rule.delete and not ghost,
        "warn": rule.warn,
        "notify": rule.notify,
        "exempt_role_ids": [role.id for role in resolve.roles(guild, rule.exempt_role_ids)],
        "exempt_channel_ids": _channels(guild, rule.exempt_channel_ids),
    }


def _punishments(data: list[Punishment]) -> list[tuple[int, str, int | None]]:
    if len({step.warnings for step in data}) != len(data):
        raise SettingError("Each warning count can only have one punishment.")
    steps = []
    for step in data:
        if step.action == "timeout" and step.seconds is None:
            raise SettingError("Pick how long the timeout lasts.")
        steps.append((step.warnings, step.action, step.seconds if step.action == "timeout" else None))
    return steps


@get("/", summary="Square's own AutoMod rules and warning punishments")
async def get_automod(guild: discord.Guild) -> AutomodSettings:
    return _settings(guild)


@patch("/", summary="Change Square's AutoMod rules or warning punishments", responses=REFUSED)
async def update_automod(guild: discord.Guild, data: AutomodPatch) -> AutomodSettings:
    changed = None
    if data.rules is not UNSET:
        if len({rule.kind for rule in data.rules}) != len(data.rules):
            raise SettingError("Each rule can only be sent once.")
        changed = {rule.kind: _rule_values(guild, rule) for rule in data.rules}
    steps = _punishments(data.punishments) if data.punishments is not UNSET else None
    if steps and any(action == "timeout" for _, action, _ in steps) and not guild.me.guild_permissions.moderate_members:
        raise SettingError("Square needs the `Timeout Members` permission to time people out.")
    if steps and any(action == "kick" for _, action, _ in steps) and not guild.me.guild_permissions.kick_members:
        raise SettingError("Square needs the `Kick Members` permission to kick people.")
    if steps and any(action == "ban" for _, action, _ in steps) and not guild.me.guild_permissions.ban_members:
        raise SettingError("Square needs the `Ban Members` permission to ban people.")

    if changed:
        await automod_db.save_rules(guild.id, changed)
    if steps is not None:
        await automod_db.set_punishments(guild.id, steps)
    return _settings(guild)


@delete("/", summary="Reset Square's AutoMod rules and warning punishments", status_code=200)
async def reset_automod(guild: discord.Guild) -> AutomodSettings:
    """Discord's own AutoMod rules and members' warnings stay."""
    await automod_db.reset(guild.id)
    return _settings(guild)


def _native(raw: dict[str, Any], bot_id: int) -> NativeRule | None:
    trigger = _TRIGGERS.get(raw.get("trigger_type", 0))
    if trigger is None:
        return None
    meta = raw.get("trigger_metadata") or {}
    actions = {action["type"]: action.get("metadata") or {} for action in raw.get("actions", [])}
    return NativeRule(
        id=str(raw["id"]),
        name=raw.get("name", ""),
        trigger=trigger,  # type: ignore[arg-type]
        enabled=bool(raw.get("enabled")),
        by_square=int(raw.get("creator_id", 0)) == bot_id,
        keywords=meta.get("keyword_filter", []),
        patterns=meta.get("regex_patterns", []),
        allow_list=meta.get("allow_list", []),
        presets=[_PRESETS[value] for value in meta.get("presets", []) if value in _PRESETS],  # type: ignore[misc]
        mention_limit=meta.get("mention_total_limit") if trigger == "mention_spam" else None,
        raid_protection=bool(meta.get("mention_raid_protection_enabled")),
        block=_BLOCK in actions,
        block_message=actions.get(_BLOCK, {}).get("custom_message") or None,
        alert_channel_id=str(actions[_ALERT]["channel_id"]) if _ALERT in actions else None,
        timeout_seconds=actions[_TIMEOUT].get("duration_seconds") if _TIMEOUT in actions else None,
        block_interaction=_BLOCK_INTERACTION in actions,
        exempt_role_ids=[str(value) for value in raw.get("exempt_roles", [])],
        exempt_channel_ids=[str(value) for value in raw.get("exempt_channels", [])],
    )


def _payload(guild: discord.Guild, rule: NativeRule) -> dict[str, Any]:
    trigger = rule.trigger
    meta: dict[str, Any] = {}
    if trigger in _WORD_TRIGGERS:
        if len(rule.allow_list) > 100:
            raise SettingError("This kind of rule allows up to 100 allowed words.")
        meta = {"keyword_filter": rule.keywords, "regex_patterns": rule.patterns, "allow_list": rule.allow_list}
    elif trigger == "preset":
        if not rule.presets:
            raise SettingError("Pick at least one word list.")
        meta = {"presets": [_PRESET_IDS[value] for value in rule.presets], "allow_list": rule.allow_list}
    elif trigger == "mention_spam":
        meta = {
            "mention_total_limit": rule.mention_limit or _MENTION_LIMIT,
            "mention_raid_protection_enabled": rule.raid_protection,
        }

    actions: list[dict[str, Any]] = []
    if trigger == "member_profile":
        if rule.block_interaction:
            actions.append({"type": _BLOCK_INTERACTION})
    elif rule.block:
        actions.append(
            {"type": _BLOCK, "metadata": {"custom_message": rule.block_message} if rule.block_message else {}}
        )
    if rule.alert_channel_id:
        channel = resolve.text_channel(guild, rule.alert_channel_id)
        assert channel is not None
        actions.append({"type": _ALERT, "metadata": {"channel_id": str(channel.id)}})
    if rule.timeout_seconds:
        if trigger not in _TIMEOUT_TRIGGERS:
            raise SettingError("Discord only times people out for keyword and mention spam rules.")
        actions.append({"type": _TIMEOUT, "metadata": {"duration_seconds": rule.timeout_seconds}})
    if not actions:
        raise SettingError(f"{rule.name} needs at least one action.")
    return {
        "name": rule.name,
        "event_type": 2 if trigger == "member_profile" else 1,
        "trigger_metadata": meta,
        "actions": actions,
        "enabled": rule.enabled,
        "exempt_roles": [str(role.id) for role in resolve.roles(guild, rule.exempt_role_ids)],
        "exempt_channels": [str(channel_id) for channel_id in _channels(guild, rule.exempt_channel_ids)],
    }


async def _discord(call: Any) -> Any:
    try:
        return await call
    except discord.Forbidden as exc:
        # 50001 is Discord refusing bots outright, whatever their permissions
        if exc.code == 50001:
            raise SettingError("Discord doesn't let Square do that. Change it in Server Settings › AutoMod.") from exc
        raise SettingError(
            "Square needs the `Manage Server` permission to see or change Discord's AutoMod rules."
        ) from exc
    except discord.HTTPException as exc:
        detail = " ".join(exc.text.split()) if exc.text else "Try again."
        raise SettingError(f"Discord refused the change. {detail}") from exc


def _audit(actor: int) -> str:
    return f"Changed from the dashboard by {actor}"


def _need_manage(guild: discord.Guild) -> None:
    if not guild.me.guild_permissions.manage_guild:
        raise SettingError("Square needs the `Manage Server` permission to see or change Discord's AutoMod rules.")


@get("/discord", summary="Discord's own AutoMod rules in this server", responses=REFUSED)
async def list_native_rules(client: Client, guild: discord.Guild) -> list[NativeRule]:
    _need_manage(guild)
    raw = await _discord(client.http.get_auto_moderation_rules(guild.id))
    return [rule for item in raw if (rule := _native(item, client.user.id))]


@post("/discord", summary="Add a Discord AutoMod rule", status_code=200, responses=REFUSED)
async def create_native_rule(client: Client, guild: discord.Guild, actor: int, data: NativeRuleCreate) -> NativeRule:
    """New rules start off, so nothing is blocked before they're set up."""
    _need_manage(guild)
    # Outside Community servers Discord answers 50001 instead of making one
    if data.trigger == "member_profile" and "COMMUNITY" not in guild.features:
        raise SettingError(
            "Member profile rules need a Community server. Turn on Community in Discord's server settings first."
        )
    raw = await _discord(client.http.get_auto_moderation_rules(guild.id))
    taken = sum(_TRIGGERS.get(item.get("trigger_type")) == data.trigger for item in raw)
    if taken >= NATIVE_LIMITS[data.trigger]:
        raise SettingError(f"Discord allows {NATIVE_LIMITS[data.trigger]} of this kind of rule per server.")
    draft = NativeRule(
        id="0" * 17,
        name=data.name,
        trigger=data.trigger,
        enabled=False,
        by_square=True,
        keywords=[],
        patterns=[],
        allow_list=[],
        presets=["profanity", "sexual_content", "slurs"] if data.trigger == "preset" else [],
        mention_limit=_MENTION_LIMIT if data.trigger == "mention_spam" else None,
        raid_protection=data.trigger == "mention_spam",
        block=data.trigger != "member_profile",
        block_message=None,
        alert_channel_id=None,
        timeout_seconds=None,
        block_interaction=data.trigger == "member_profile",
        exempt_role_ids=[],
        exempt_channel_ids=[],
    )
    payload = {**_payload(guild, draft), "trigger_type": _TRIGGER_IDS[data.trigger]}
    created = await _discord(client.http.create_auto_moderation_rule(guild.id, payload, reason=_audit(actor)))
    rule = _native(created, client.user.id)
    assert rule is not None
    return rule


@patch("/discord/{rule_id:str}", summary="Change a Discord AutoMod rule", responses=REFUSED)
async def update_native_rule(
    client: Client, guild: discord.Guild, actor: int, rule_id: RuleId, data: NativeRulePatch
) -> NativeRule:
    _need_manage(guild)
    raw = await _discord(client.http.get_auto_moderation_rule(guild.id, int(rule_id)))
    current = _native(raw, client.user.id)
    if current is None:
        raise SettingError("Square can't edit this kind of rule. Change it in Discord's server settings.")
    sent = {field: value for field, value in structs.asdict(data).items() if value is not UNSET}
    rule = structs.replace(current, **sent)
    if rule.trigger == "preset" and len(rule.allow_list) > MAX_NATIVE_ALLOW:
        raise SettingError(f"Up to {MAX_NATIVE_ALLOW} allowed words.")
    if rule.timeout_seconds and not guild.me.guild_permissions.moderate_members:
        raise SettingError("Square needs the `Timeout Members` permission to set a timeout.")
    payload = _payload(guild, rule)
    edited = await _discord(
        client.http.edit_auto_moderation_rule(guild.id, int(rule_id), payload, reason=_audit(actor))
    )
    result = _native(edited, client.user.id)
    assert result is not None
    return result


@delete("/discord/{rule_id:str}", summary="Delete a Discord AutoMod rule", status_code=204, responses=REFUSED)
async def delete_native_rule(client: Client, guild: discord.Guild, actor: int, rule_id: RuleId) -> None:
    _need_manage(guild)
    await _discord(client.http.delete_auto_moderation_rule(guild.id, int(rule_id), reason=_audit(actor)))


@post("/test", summary="Check a message against every AutoMod rule", status_code=200, responses=REFUSED)
async def test_automod(client: Client, guild: discord.Guild, data: AutomodTest) -> AutomodTestResult:
    """Runs as a member without exempt roles. Discord rules are the bot's best guess at what Discord would do."""
    channel = guild.get_channel(int(data.channel_id)) if data.channel_id else None
    if data.channel_id and channel is None:
        raise SettingError("That channel isn't in this server.")
    places: set[int] = set()
    if channel:
        places = {channel.id, getattr(channel, "category_id", None) or 0}
    content = data.content
    hits: list[AutomodHit] = []
    skipped: list[str] = []

    if guild.me.guild_permissions.manage_guild:
        raw = await _discord(client.http.get_auto_moderation_rules(guild.id))
        for rule in filter(None, (_native(item, client.user.id) for item in raw)):
            if not rule.enabled or places & {int(value) for value in rule.exempt_channel_ids}:
                continue
            if rule.trigger == "keyword":
                if found := rules.keyword_hit(content, rule.keywords, rule.patterns, rule.allow_list):
                    hits.append(AutomodHit(source="discord", rule=rule.name, detail=f'Matched "{found}"'))
            elif rule.trigger == "mention_spam":
                if (count := rules.mention_count(content)) > (rule.mention_limit or _MENTION_LIMIT):
                    hits.append(
                        AutomodHit(
                            source="discord", rule=rule.name, detail=f"{fmt_count(count)} {plural(count, 'mention')}"
                        )
                    )
            elif rule.trigger == "member_profile":
                skipped.append(f"{rule.name} checks member profiles, not messages.")
            else:
                skipped.append(f"{rule.name} uses Discord's own detection, which can't be tested here.")
    else:
        skipped.append("Discord's rules: Square needs the Manage Server permission to read them.")

    for kind, rule in automod_db.rules(guild.id).items():
        if not rule.enabled or places & set(rule.exempt_channel_ids):
            continue
        label = LABELS[kind]
        if kind in rules.WINDOW_KINDS:
            skipped.append(f"{label} needs several messages in a row.")
        elif kind == "ghost_pings":
            skipped.append(f"{label} looks at deleted messages, which can't be tested here.")
        elif kind == "new_members":
            if rules.has_link(content):
                minutes = rule.amount or 0
                detail = f"Has a link, caught for anyone who joined under {minutes} {plural(minutes, 'minute')} ago"
                hits.append(AutomodHit(source="square", rule=label, detail=detail))
        elif kind == "media":
            if channel and channel.id in rule.channel_ids and not rules.has_link(content):
                hits.append(AutomodHit(source="square", rule=label, detail="No link, and files can't be tested here"))
        elif detail := await rules.content_hit(client, guild, rule, content):
            hits.append(AutomodHit(source="square", rule=label, detail=detail))
    return AutomodTestResult(hits=hits, skipped=skipped)


router = Router(
    "/guilds/{guild_id:str}/automod",
    tags=["AutoMod"],
    exception_handlers={SettingError: refused},
    dependencies={"guild": Provide(provide_guild, sync_to_thread=False)},
    route_handlers=[
        get_automod,
        update_automod,
        reset_automod,
        list_native_rules,
        create_native_rule,
        update_native_rule,
        delete_native_rule,
        test_automod,
    ],
)
