"""Discord-flavoured markdown to HTML for transcripts. User text is escaped before any markup is added."""

import datetime
import html
import re
from dataclasses import dataclass, field
from markupsafe import Markup


@dataclass
class Lookups:
    users: dict[int, str] = field(default_factory=dict)
    roles: dict[int, tuple[str, str]] = field(default_factory=dict)  # id: (name, hex color)
    channels: dict[int, str] = field(default_factory=dict)


_CODE_BLOCK = re.compile(r"```(?:([\w+-]+)\n)?(.*?)```", re.S)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_TIMESTAMP_FORMATS = {
    "t": "%H:%M",
    "T": "%H:%M:%S",
    "d": "%d/%m/%Y",
    "D": "%d %B %Y",
    "f": "%d %B %Y %H:%M",
    "F": "%A, %d %B %Y %H:%M",
    "R": "%d %B %Y %H:%M",
}
# Inline rules run on already-escaped text, so `<` and `>` appear as `&lt;` and `&gt;`
_INLINE_RULES = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"__(.+?)__"), r"<u>\1</u>"),
    (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\*)"), r"<em>\1</em>"),
    (re.compile(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])"), r"<em>\1</em>"),
    (re.compile(r"~~(.+?)~~"), r"<s>\1</s>"),
    (re.compile(r"\|\|(.+?)\|\|"), r'<span class="spoiler" tabindex="0">\1</span>'),
]
_MASKED_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")
_URL = re.compile(r'(https?://[^\s<\x01]+[^\s<.,:;"\')\]\x01])')
_CUSTOM_EMOJI = re.compile(r"&lt;(a?):(\w+):(\d+)&gt;")
_USER = re.compile(r"&lt;@!?(\d+)&gt;")
_ROLE = re.compile(r"&lt;@&amp;(\d+)&gt;")
_CHANNEL = re.compile(r"&lt;#(\d+)&gt;")
_TIME = re.compile(r"&lt;t:(-?\d+)(?::([tTdDfFR]))?&gt;")


def _inline(text: str, lookups: Lookups) -> str:
    def emoji(m: re.Match[str]) -> str:
        ext = "gif" if m.group(1) else "webp"
        return f'<img class="emoji" alt=":{m.group(2)}:" title=":{m.group(2)}:" src="https://cdn.discordapp.com/emojis/{m.group(3)}.{ext}?size=48">'

    def user(m: re.Match[str]) -> str:
        name = lookups.users.get(int(m.group(1)), "unknown-user")
        return f'<span class="mention">@{html.escape(name)}</span>'

    def role(m: re.Match[str]) -> str:
        name, color = lookups.roles.get(int(m.group(1)), ("unknown-role", "#c9cdfb"))
        return f'<span class="mention role" style="--role: {color}">@{html.escape(name)}</span>'

    def channel(m: re.Match[str]) -> str:
        return f'<span class="mention">#{html.escape(lookups.channels.get(int(m.group(1)), "unknown-channel"))}</span>'

    def timestamp(m: re.Match[str]) -> str:
        moment = datetime.datetime.fromtimestamp(int(m.group(1)), datetime.UTC)
        style = m.group(2) or "f"
        shown = moment.strftime(_TIMESTAMP_FORMATS.get(style, "%d %B %Y %H:%M"))
        return f'<time class="timestamp" datetime="{moment.isoformat()}" data-style="{style}">{shown} UTC</time>'

    # Finished tags go behind placeholders so the formatting rules can't reach into URLs, e.g. `a_b_c`
    tokens: list[str] = []

    def hold(markup: str) -> str:
        tokens.append(markup)
        return f"\x01{len(tokens) - 1}\x01"

    def masked(m: re.Match[str]) -> str:
        return hold(f'<a href="{m.group(2)}" rel="noopener noreferrer">') + m.group(1) + hold("</a>")

    text = _CUSTOM_EMOJI.sub(lambda m: hold(emoji(m)), text)
    text = _ROLE.sub(lambda m: hold(role(m)), text)
    text = _USER.sub(lambda m: hold(user(m)), text)
    text = _CHANNEL.sub(lambda m: hold(channel(m)), text)
    text = _TIME.sub(lambda m: hold(timestamp(m)), text)
    text = _MASKED_LINK.sub(masked, text)
    text = _URL.sub(lambda m: hold(f'<a href="{m.group(1)}" rel="noopener noreferrer">{m.group(1)}</a>'), text)
    for pattern, replacement in _INLINE_RULES:
        text = pattern.sub(replacement, text)
    return re.sub(r"\x01(\d+)\x01", lambda m: tokens[int(m.group(1))], text)


def render(content: str, lookups: Lookups) -> Markup:
    if not content:
        return Markup("")
    # Code is pulled out first so nothing inside it is treated as markdown, then put back at the end
    stash: list[str] = []

    def keep(snippet: str) -> str:
        stash.append(snippet)
        return f"\x00{len(stash) - 1}\x00"

    content = _CODE_BLOCK.sub(
        lambda m: keep(f"<pre><code>{html.escape(m.group(2).strip(chr(10)))}</code></pre>"), content
    )
    content = _INLINE_CODE.sub(lambda m: keep(f"<code>{html.escape(m.group(1))}</code>"), content)

    blocks: list[str] = []
    for line in html.escape(content, quote=True).split("\n"):
        if m := re.match(r"(#{1,3}) (.+)", line):
            blocks.append(f"<h{len(m.group(1))}>{_inline(m.group(2), lookups)}</h{len(m.group(1))}>")
        elif m := re.match(r"-# (.+)", line):
            blocks.append(f'<div class="subtext">{_inline(m.group(1), lookups)}</div>')
        elif m := re.match(r"&gt; ?(.*)", line):
            blocks.append(f"<blockquote>{_inline(m.group(1), lookups)}</blockquote>")
        else:
            blocks.append(f"<p>{_inline(line, lookups)}</p>" if line.strip() else "<p><br></p>")
    out = "".join(blocks)
    out = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], out)
    return Markup(out)  # noqa: S704 - built only from escaped text and fixed tags above


def plain(content: str, limit: int = 90) -> str:
    text = re.sub(r"[*_~|`>#]", "", content).replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
