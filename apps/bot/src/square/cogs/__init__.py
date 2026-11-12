from pathlib import Path


def extensions() -> list[str]:
    return sorted(f"{__name__}.{path.parent.name}" for path in Path(__file__).parent.glob("*/__init__.py"))
