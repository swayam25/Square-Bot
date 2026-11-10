import argparse
import time
from pathlib import Path
from square.imaging import render_png
from square.imaging.templates import PREVIEWS


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m square.imaging", description="Render a template with fake data.")
    parser.add_argument("template", choices=sorted(PREVIEWS))
    parser.add_argument("--accent", help='An accent color like "#1FCEEC", instead of the one in config.toml.')
    parser.add_argument("--out", type=Path, default=Path(".preview"), help="Folder to write the PNG to.")
    args = parser.parse_args()

    template, sample = PREVIEWS[args.template]
    accent = int(args.accent.lstrip("#"), 16) if args.accent else None
    start = time.perf_counter()
    png = render_png(template, sample(), accent=accent)
    elapsed = (time.perf_counter() - start) * 1000

    args.out.mkdir(parents=True, exist_ok=True)
    suffix = f"-{args.accent.lstrip('#').lower()}" if args.accent else ""
    path = args.out / f"{args.template}{suffix}.png"
    path.write_bytes(png)
    print(f"{path} ({elapsed:.0f} ms)")  # noqa: T201


if __name__ == "__main__":
    main()
