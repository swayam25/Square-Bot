import re
from datetime import UTC, datetime

_CUSTOM_EMOJI = re.compile(r"<a?:(\w+):\d+>")
_TIMESTAMP = re.compile(r"<t:(-?\d+)(?::[tTdDfFR])?>")
# Paired markers only: py-cord's `remove_markdown` also eats lone underscores, like the ones in snake_case
_PAIRS = re.compile(
    r"```(?:[\w+-]*\n)?(.+?)```|\*\*(?!\s)(.+?)\*\*|__(.+?)__|~~(.+?)~~|\|\|(.+?)\|\||`([^`\n]+)`|\*(?!\s)([^*\n]+?)\*",
    re.S,
)
_LINE_MARKS = re.compile(r"^(?:#{1,3} |-# |>>> |> )", re.M)


def _date(match: re.Match[str]) -> str:
    try:
        return datetime.fromtimestamp(int(match[1]), UTC).strftime("%b %d, %Y")
    except OverflowError, ValueError, OSError:
        return match[0]


def plain(text: str) -> str:
    """Turns Discord markup into the text people read: emojis become names, timestamps dates, markers go."""
    text = _CUSTOM_EMOJI.sub(r":\1:", text)
    text = _TIMESTAMP.sub(_date, text)
    # Twice, for nested markers like ***bold italic***
    for _ in range(2):
        text = _PAIRS.sub(lambda match: next(group for group in match.groups() if group is not None), text)
    text = _LINE_MARKS.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
