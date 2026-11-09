from collections.abc import Callable
from square.imaging import Template

# Fake data for `python -m square.imaging`: one `sample_<template>` per template, registered in `PREVIEWS`. Cover the
# edge cases (long or styled names, big numbers, missing avatars) so layout bugs show up here first.


PREVIEWS: dict[str, tuple[Template, Callable[[], object]]] = {}
