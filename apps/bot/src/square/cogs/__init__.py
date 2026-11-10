from pathlib import Path


def extensions() -> list[str]:
    """Every cog package in this folder as an extension name, e.g. `square.cogs.voice`."""
    return sorted(f"{__name__}.{path.parent.name}" for path in Path(__file__).parent.glob("*/__init__.py"))
