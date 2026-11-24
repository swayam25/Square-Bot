from collections.abc import Generator, Hashable
from contextlib import contextmanager


class Guard:
    def __init__(self) -> None:
        self._held: set[Hashable] = set()

    @contextmanager
    def hold(self, key: Hashable) -> Generator[bool]:
        """Yields False, holding nothing, while `key` is already held."""
        if key in self._held:
            yield False
            return
        self._held.add(key)
        try:
            yield True
        finally:
            self._held.discard(key)
