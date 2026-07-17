import math


class Term:
    """Terminal-style text rendering helpers for Discord code blocks."""

    @staticmethod
    def kv(rows: list[tuple[str, str]], cols: int = 2) -> list[str]:
        """Lays key/value rows out down `cols` aligned columns."""
        if not rows:
            return []
        per_col = math.ceil(len(rows) / cols)
        columns = [rows[i * per_col : (i + 1) * per_col] for i in range(cols)]
        key_widths = [max((len(k) for k, _ in c), default=0) for c in columns]
        val_widths = [max((len(v) for _, v in c), default=0) for c in columns]
        lines = []
        for i in range(per_col):
            cells = []
            for col, key_width, val_width in zip(columns, key_widths, val_widths, strict=True):
                if i < len(col):
                    key, value = col[i]
                    cells.append(f"{key.ljust(key_width)}  {value.ljust(val_width)}")
                else:
                    cells.append(" " * (key_width + 2 + val_width))
            lines.append(("  " + "   ".join(cells)).rstrip())
        return lines

    @staticmethod
    def grid(headers: list[str], rows: list[list[str]]) -> list[str]:
        """Renders rows as an aligned column grid under a ruled header."""
        widths = [max(len(str(row[i])) for row in [headers, *rows]) for i in range(len(headers))]

        def render(cells) -> str:
            return (
                "  " + "  ".join(str(cell).ljust(width) for cell, width in zip(cells, widths, strict=True))
            ).rstrip()

        return [render(headers), "  " + "─" * (sum(widths) + 2 * (len(widths) - 1)), *[render(r) for r in rows]]

    @staticmethod
    def fence(section: list[str]) -> str:
        """Wraps a section's lines in a code block."""
        return "```\n" + "\n".join(section).rstrip() + "\n```"

    @staticmethod
    def num(value: float) -> str:
        """Formats a single value with just enough precision to stay informative."""
        return f"{value:.0f}" if abs(value) >= 100 or value == int(value) else f"{value:.1f}"
