"""Write the OpenAPI schema (frontend types are generated from it)."""

from __future__ import annotations

import json
import sys

from taqpso.api.main import app

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    with open(out, "w") as f:
        json.dump(app.openapi(), f, indent=1)
