import datetime
import discord
import io
import logging
import math
import secrets
import sys
import traceback
from babel.dates import format_timedelta
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from discord import ui
from discord.ext import commands
from square.cogs.error_handler.permissions import Refusal, explain
from square.core import Client
from square.core.cog import Cog
from square.core.view import DesignerView
from square.db.funcs.dev import fetch_dev_ids
from square.modules import ModuleOff
from square.utils import check, config
from square.utils.emoji import emoji
from square.utils.helpers import fmt_perms

log = logging.getLogger(__name__)

TRACEBACK_LIMIT = 3800  # A container's text can't go past 4000 characters
PERMISSION_CODES = {50001, 50013}  # Missing Access and Missing Permissions. Other 403s explain themselves.


@dataclass
class Failure:
    source: str
    user: discord.abc.User | None
    guild: discord.Guild | None
    channel: object | None
    reply: Callable[..., Awaitable[object]] | None = None
    options: str = ""


def _user_fault(error: BaseException) -> str | None:
    match error:
        case check.NotAuthorized():
            return "This command is only for the bot's developers."
        case commands.CommandOnCooldown():
            wait = datetime.timedelta(seconds=math.ceil(error.retry_after))
            return f"You're going too fast. Try again in **{format_timedelta(wait, locale='en')}**."
        case commands.MissingPermissions():
            return f"You need **{fmt_perms(error.missing_permissions)}** to use this."
        case commands.BotMissingPermissions():
            return f"I need **{fmt_perms(error.missing_permissions)}** to do that. Ask a server admin to grant it."
        case commands.NoPrivateMessage():
            return "This only works in a server."
        case commands.PrivateMessageOnly():
            return "This only works in DMs."
        case commands.MaxConcurrencyReached():
            return "This is already running. Try again once it finishes."
        case commands.UserInputError() | ModuleOff():
            return f"{error}"
        case commands.CheckFailure() | discord.CheckFailure():
            return "You can't use this here."
    return None


def _refused(error: discord.Forbidden, refusal: Refusal) -> str:
    if error.code not in PERMISSION_CODES and error.text:
        return f"Discord won't let me do that: {error.text}."
    opening = refusal.action or "I don't have permission to do that."
    if refusal.missing:
        place = f" in {refusal.place}" if refusal.place else ""
        return f"{opening}\nI'm missing **{fmt_perms(refusal.missing)}**{place}. Ask a server admin to grant it."
    if refusal.needed:
        return (
            f"{opening}\nI already have **{fmt_perms(refusal.needed)}**, so my role is probably below the member "
            "or role involved. Move my role higher, then try again."
        )
    return f"{opening}\nCheck my role and this channel's permissions, then try again."


def _bug(error: BaseException, reference: str) -> str:
    match error:
        case discord.NotFound():
            text = "Something I needed no longer exists. It may have just been deleted."
        case discord.DiscordServerError():
            text = "Discord is having trouble right now. Please try again in a moment."
        case TimeoutError():
            text = "That took too long. Please try again."
        case _:
            text = "Something went wrong on my side. It's been logged, so please try again later."
    return f"{text}\n-# Reference: `{reference}`"


def _code_location(error: BaseException) -> str:
    frames = list(traceback.walk_tb(error.__traceback__))
    for frame, line in reversed(frames):
        if frame.f_globals.get("__name__", "").startswith("square"):
            return f"{frame.f_globals['__name__']}:{line} in {frame.f_code.co_name}"
    if frames:
        frame, line = frames[-1]
        return f"{frame.f_globals.get('__name__', '?')}:{line} in {frame.f_code.co_name}"
    return "unknown"


async def _is_dev(user: discord.abc.User | None) -> bool:
    if user is None:
        return False
    if user.id == config.owner_id:
        return True
    try:
        return user.id in await fetch_dev_ids()
    except Exception:  # The database being down may be the error being handled
        return False


def _interaction_reply(interaction: discord.Interaction) -> Callable[..., Awaitable[object]]:
    async def reply(view: DesignerView, file: discord.File | None = None) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(view=view, file=file or discord.utils.MISSING, ephemeral=True)
        else:
            await interaction.response.send_message(view=view, file=file, ephemeral=True)

    return reply


class ErrorHandler(Cog):
    def __init__(self, client: Client):
        self.client = client
        # These are client methods that only print to stderr, and a listener would run alongside them, not instead.
        # `on_error` is also the only hook for errors raised inside listeners, like the tickets' button router.
        self._defaults = {name: getattr(client, name) for name in ("on_error", "on_view_error", "on_modal_error")}
        client.on_error = self.on_event_error
        client.on_view_error = self.on_view_error
        client.on_modal_error = self.on_modal_error

    def cog_unload(self):
        for name, default in self._defaults.items():
            setattr(self.client, name, default)

    @commands.Cog.listener(name="on_application_command_error")
    @commands.Cog.listener(name="on_command_error")
    async def on_command_failure(self, ctx: discord.ApplicationContext | commands.Context, error: Exception):
        if isinstance(ctx, discord.ApplicationContext):
            options = ", ".join(f"{option['name']}={option.get('value')!r}" for option in ctx.selected_options or [])
            name = ctx.command.qualified_name if ctx.command else "unknown"
            reply = _interaction_reply(ctx.interaction)
            await self._handle(error, Failure(f"/{name}", ctx.author, ctx.guild, ctx.channel, reply, options))
            return
        if isinstance(error, commands.CommandNotFound | check.NotAuthorized):
            return

        async def text_reply(view: DesignerView, file: discord.File | None = None) -> None:
            await ctx.reply(view=view, file=file, delete_after=None if file or await _is_dev(ctx.author) else 5)

        name = ctx.command.qualified_name if ctx.command else "unknown"
        await self._handle(error, Failure(f"{ctx.clean_prefix}{name}", ctx.author, ctx.guild, ctx.channel, text_reply))

    async def on_view_error(self, error: Exception, item: ui.Item, interaction: discord.Interaction):
        name = getattr(item, "label", None) or getattr(item, "placeholder", None) or getattr(item, "custom_id", None)
        source = f'{type(item.view).__name__} {type(item).__name__.lower()} "{name}"'
        await self._from_interaction(error, source, interaction)

    async def on_modal_error(self, error: Exception, interaction: discord.Interaction):
        await self._from_interaction(error, "modal", interaction)

    async def on_event_error(self, event: str, *args, **kwargs) -> None:
        """Called from inside py-cord's `except`, so the error is still current."""
        error = sys.exc_info()[1]
        if error is None:
            return
        interaction = next((arg for arg in args if isinstance(arg, discord.Interaction)), None)
        if interaction:
            await self._from_interaction(error, f"event {event}", interaction)
        else:
            await self._handle(error, Failure(f"event {event}", None, None, None))

    async def _from_interaction(self, error: Exception, source: str, interaction: discord.Interaction) -> None:
        reply = _interaction_reply(interaction)
        await self._handle(error, Failure(source, interaction.user, interaction.guild, interaction.channel, reply))

    async def _handle(self, error: BaseException, failure: Failure) -> None:
        # Commands wrap what they raise, so the real error is one level down
        error = getattr(error, "original", error)
        context = (
            f"user={failure.user.id if failure.user else None} guild={failure.guild.id if failure.guild else None} "
            f"channel={getattr(failure.channel, 'id', None)}"
        )
        if failure.options:
            context += f" options=[{failure.options}]"
        file = None
        if text := _user_fault(error):
            log.debug("%s refused: %s (%s)", failure.source, type(error).__name__, context)
        elif isinstance(error, discord.Forbidden):
            refusal = explain(error, failure.guild, failure.channel)
            text = _refused(error, refusal)
            log.warning(
                "%s got a 403 at %s: %s, needs %s, missing %s (%s)",
                failure.source,
                _code_location(error),
                error.text or error,
                refusal.needed or "unknown",
                refusal.missing or "none",
                context,
            )
        else:
            reference = secrets.token_hex(3)
            text = _bug(error, reference)
            log.error(
                "%s failed at %s [ref %s] (%s)",
                failure.source,
                _code_location(error),
                reference,
                context,
                exc_info=error,
            )
            if await _is_dev(failure.user):
                trace = "".join(traceback.format_exception(error))
                if len(trace) <= TRACEBACK_LIMIT:
                    text += f"\n```py\n{trace}\n```"
                else:
                    file = discord.File(io.BytesIO(trace.encode()), filename="error.txt")
        if failure.reply is None:
            return
        items: list[ui.ViewItem] = [ui.TextDisplay(f"{emoji.error} {text}")]
        if file:
            items.append(ui.File("attachment://error.txt"))
        view = DesignerView(ui.Container(*items, color=config.color.red))
        try:
            await failure.reply(view, file)
        except discord.HTTPException as exc:
            log.debug("Couldn't tell the user about the failure in %s: %s", failure.source, exc)


def setup(client: Client):
    client.add_cog(ErrorHandler(client))
