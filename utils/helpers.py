import datetime
import discord
import io
import re
from babel.dates import format_datetime
from babel.units import format_unit


def parse_duration(duration: str, max_duration: str | None = None) -> datetime.timedelta:
    """
    Parse a duration string into a timedelta object.

    Args:
        duration (str): A string representing the duration, e.g., "2w3d4h5m6s".
        max_duration (str | None): An optional maximum duration string, e.g., "2w3d".
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

    # Check against max_duration if provided
    if max_duration is not None:
        max_td = parse_duration(max_duration)
        if total_duration > max_td:
            raise ValueError(f"Total duration must not exceed `{max_duration}`.")

    elif total_duration.days > 28:
        raise ValueError("Total duration must be less than `28 days`.")

    return total_duration


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


def _fmt_bytes(size: float) -> str:
    """Formats a byte count into a short human-readable size."""
    for unit in ("B", "KB", "MB"):
        if size < 1024 or unit == "MB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024


def _table(rows: list[tuple[str, str]]) -> list[str]:
    """
    Renders key/value rows as an aligned two-column table.

    Multi-line values continue in the value column, e.g.:
    ```
      Title       │ Hello
      Description │ line one
                  │ line two
    ```
    """
    if not rows:
        return []
    width = max(len(key) for key, _ in rows)
    lines = []
    for key, value in rows:
        value_lines = str(value).splitlines() or [""]
        lines.append(f"  {key.ljust(width)} │ {value_lines[0]}")
        lines.extend(f"  {' ' * width} │ {value_line}" for value_line in value_lines[1:])
    return lines


def _embed_rows(embed: discord.Embed) -> list[tuple[str, str]]:
    """Extracts the set parts of an embed as table rows."""
    rows = []
    if name := getattr(embed.author, "name", None):
        rows.append(("Author", name))
    if embed.title:
        rows.append(("Title", embed.title))
    if embed.url:
        rows.append(("URL", embed.url))
    if embed.description:
        rows.append(("Description", embed.description))
    for field in embed.fields:
        rows.append((f"Field · {field.name}", field.value))
    if url := getattr(embed.image, "url", None):
        rows.append(("Image", url))
    if url := getattr(embed.thumbnail, "url", None):
        rows.append(("Thumbnail", url))
    if text := getattr(embed.footer, "text", None):
        rows.append(("Footer", text))
    return rows


def _component_rows(components: list) -> list[tuple[str, str]]:
    """Flattens message components (incl. nested rows, sections & containers) into table rows."""
    rows = []
    for comp in components:
        children = getattr(comp, "children", None) or getattr(comp, "components", None)
        if children:
            rows += _component_rows(children)
            continue
        detail = (
            getattr(comp, "label", None)
            or getattr(comp, "content", None)
            or getattr(comp, "placeholder", None)
            or getattr(comp, "url", None)
            or ""
        )
        rows.append((type(comp).__name__, str(detail)))
    return rows


def _fmt_timestamp(dt: datetime.datetime) -> str:
    """Formats a datetime as an explicit UTC timestamp for message logs."""
    return format_datetime(dt, "dd MMM yyyy, HH:mm:ss zzz", tzinfo=datetime.UTC, locale="en")


def create_dc_msgs_file(
    msgs: list[discord.Message],
    uncached_ids: set[int] | None = None,
    *,
    guild_id: int | None = None,
    channel_id: int | None = None,
) -> discord.File:
    """
    Create a Discord file containing the provided messages, oldest first.

    Each message shows its content, followed by a table block per embed &
    for its attachments & components, all inside the `│ … ╰` tree.
    Uncached IDs get a minimal entry (only the ID & sent time are known),
    shown as a jump link when guild_id & channel_id are provided.

    Args:
        msgs (list[:class:`discord.Message`]): A list of Discord messages.
        uncached_ids (set[int] | None): IDs of deleted messages that weren't cached.
        guild_id (int | None): Guild ID used to build jump links for uncached IDs.
        channel_id (int | None): Channel ID used to build jump links for uncached IDs.

    Returns:
        :class:`discord.File`: A Discord file object containing the messages.
    """
    entries: list[tuple[datetime.datetime, str]] = []
    for msg in msgs:
        lines = msg.content.splitlines() if msg.content else []
        for num, embed in enumerate(msg.embeds, start=1):
            if rows := _embed_rows(embed):
                lines += ["", f"Embed {num}" if len(msg.embeds) > 1 else "Embed"] + _table(rows)
        if msg.attachments:
            rows = [(media.filename, f"{_fmt_bytes(media.size)} · {media.url}") for media in msg.attachments]
            lines += ["", f"Attachment{'s' if len(msg.attachments) > 1 else ''}"] + _table(rows)
        if rows := _component_rows(msg.components):
            lines += ["", "Components"] + _table(rows)
        if not lines:
            lines = ["(no content)"]
        body = "".join(f"│ {line}".rstrip() + "\n" for line in lines[:-1]) + f"╰ {lines[-1]}"
        entries.append(
            (msg.created_at, f"[{_fmt_timestamp(msg.created_at)}] {msg.author} ({msg.author.id})\n{body}\n\n")
        )
    for msg_id in uncached_ids or ():
        created_at = discord.utils.snowflake_time(msg_id)
        ref = (
            f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
            if guild_id and channel_id
            else f"Message ID: {msg_id}"
        )
        entries.append((created_at, f"[{_fmt_timestamp(created_at)}] Unknown\n╰ [Unknown Content • {ref}]\n\n"))
    entries.sort(key=lambda entry: entry[0])
    with io.StringIO() as file:
        file.writelines(text for _, text in entries)
        file.seek(0)
        dc_file = discord.File(fp=file, filename="messages.txt")
    return dc_file
