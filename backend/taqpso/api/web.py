"""Single-process entrypoint for deployment: API under /api, built UI at /."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from taqpso.api.main import app as api_app
from taqpso.api.main import lifespan


class _UI(StaticFiles):
    """Hashed build assets are immutable; index.html must always revalidate."""

    async def get_response(self, path, scope):  # type: ignore[no-untyped-def]
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
        )
        return resp


app = FastAPI(title="Tempo", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.mount("/api", api_app)

_dist = Path(os.environ.get("TEMPO_UI_DIR", "/app/ui"))
if _dist.is_dir():
    app.mount("/", _UI(directory=_dist, html=True), name="ui")
