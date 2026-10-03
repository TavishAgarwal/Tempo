"""FastAPI application."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from taqpso.api import state
from taqpso.api.routes import incidents, instances, live, paths, results, solve


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from taqpso.api.worker import warmup

    warmup()  # JIT/load kernels so the demo has no first-call lag
    state.jobs()
    yield
    state.shutdown_jobs()


app = FastAPI(title="Tempo API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in (
    instances.router,
    solve.router,
    incidents.router,
    paths.router,
    results.router,
    live.router,
):
    app.include_router(r)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
