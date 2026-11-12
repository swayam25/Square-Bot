import json
import sys
from pathlib import Path
from square.api.app import create_app

if len(sys.argv) != 2:
    raise SystemExit("Usage: python -m square.api <path>")

app = create_app(None, secret="", docs=True)
Path(sys.argv[1]).write_text(json.dumps(app.openapi_schema.to_schema(), indent=2) + "\n")
