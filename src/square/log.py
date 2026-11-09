import atexit
import logging
import os
import queue
import sys
import warnings
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.text import Text

# Third-party loggers are noisy below these levels. Lower one here to debug it, e.g. "tortoise" to DEBUG prints SQL.
LIBRARY_LEVELS = {
    "aerich": logging.WARNING,
    "asyncio": logging.WARNING,
    "discord": logging.WARNING,
    "fontTools": logging.WARNING,
    "PIL": logging.WARNING,
    "sonolink": logging.INFO,
    "tortoise": logging.WARNING,
}
LOG_FILE = Path(".cache/logs/square.log")
PLAIN_FORMAT = logging.Formatter("%(asctime)s %(levelname)-8s %(name)-14s %(message)s", "%Y-%m-%d %H:%M:%S")


class _ConsoleHandler(RichHandler):
    """Rich console output, with optional per-record styling (`extra={"style": ..., "accent": ...}`) for the banner."""

    def render_message(self, record: logging.LogRecord, message: str) -> ConsoleRenderable:
        text = super().render_message(record, message)
        if not isinstance(text, Text):
            return text
        if style := getattr(record, "style", None):
            text.stylize(style)
        if accent := getattr(record, "accent", None):
            text.highlight_words([accent], "bold yellow")
        if getattr(record, "no_wrap", False):
            # Banner art in a narrow terminal: cut lines off rather than break the picture across rows
            text.no_wrap = True
            text.overflow = "crop"
        return text


class _LocalQueueHandler(QueueHandler):
    # The stock handler pre-formats records and drops `exc_info`, which would cost Rich its tracebacks.
    # Records never leave this process, so they can be handed over untouched.
    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        return record


def setup_logging(level: str = "INFO", file: bool = False) -> None:
    """
    Routes every logger (Square's and the libraries') through one queue, written by a background thread.

    Args:
        level (str): The root level. The `SQUARE_LOG_LEVEL` env var overrides it, e.g. `DEBUG` for `just dev`.
        file (bool): Also write plain-text logs to `.cache/logs/square.log`, rotated at 5 × 5 MB.
    """
    # Rich only for a real terminal. Docker and pipes get plain lines: Rich would pad or wrap them to a fixed width.
    console: logging.Handler
    if Console().is_terminal:
        console = _ConsoleHandler(
            rich_tracebacks=True,
            show_path=False,
            omit_repeated_times=False,
            log_time_format="[%Y-%m-%d %H:%M:%S]",
            markup=False,
        )
        console.setFormatter(logging.Formatter("%(name)-14s %(message)s"))
    else:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(PLAIN_FORMAT)
    handlers: list[logging.Handler] = [console]
    if file:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(PLAIN_FORMAT)
        handlers.append(file_handler)

    log_queue: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
    root = logging.getLogger()
    root.handlers[:] = [_LocalQueueHandler(log_queue)]
    root.setLevel(os.getenv("SQUARE_LOG_LEVEL", level).upper())
    logging.captureWarnings(True)
    # py-cord & sonolink trip Python 3.14's `return` in `finally` check while compiling; nothing we can act on
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    for name, lib_level in LIBRARY_LEVELS.items():
        logging.getLogger(name).setLevel(lib_level)
    listener.start()
    atexit.register(listener.stop)
