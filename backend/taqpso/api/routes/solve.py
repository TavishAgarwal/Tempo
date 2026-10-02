from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from taqpso.api import state
from taqpso.api.jobs import Job
from taqpso.api.schemas import JobStatus, MetricsOut, RescoreOut, SolutionOut, SolveRequest
from taqpso.config import load_config
from taqpso.core.objective import Objective
from taqpso.core.solution import Solution
from taqpso.sim.simulator import simulate

router = APIRouter()


def _status(job: Job) -> JobStatus:
    import time

    best = job.best()
    fin = job.final()
    sol = None
    if best is not None and "metrics" in best:
        spec = job.spec
        sol = SolutionOut(
            routes=best["routes"],
            depart=float(best.get("depart", spec.get("depart_s") or 0.0)),
            metrics=MetricsOut(**best["metrics"]),
            solver=spec.get("solver", "qpso_warm"),
            seed=spec.get("seed", 0),
            budget=spec.get("budget_s", 0.0),
            geometry=best.get("geometry", []),
        )
    msg = fin.get("message") if fin and fin["type"] == "error" else None
    elapsed = (job.ended if job.finished else time.time()) - job.started
    return JobStatus(
        job_id=job.id,
        kind=job.kind,  # type: ignore[arg-type]
        state=job.state,  # type: ignore[arg-type]
        elapsed_s=elapsed,
        message=msg,
        solution=sol,
        run_id=fin.get("run_id") if fin else None,
    )


@router.post("/solve", response_model=JobStatus)
def solve(req: SolveRequest) -> JobStatus:
    try:
        sc = state.scenario(req.instance_id)
    except KeyError:
        raise HTTPException(404, f"Unknown instance {req.instance_id}") from None
    job = state.jobs().submit("solve", req.model_dump())
    del sc
    return _status(job)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    job = state.jobs().get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job")
    return _status(job)


@router.post("/jobs/{job_id}/stop")
def stop_job(job_id: str) -> dict[str, bool]:
    return {"stopping": state.jobs().stop(job_id)}


@router.post("/jobs/{job_id}/rescore", response_model=RescoreOut)
def rescore(job_id: str, depart: float) -> RescoreOut:
    """Re-simulate the job's current plan at another departure time (time-of-day slider)."""
    job = state.jobs().get(job_id)
    best = job.best() if job else None
    if job is None or best is None:
        raise HTTPException(404, "No plan available for this job")
    sc = state.scenario(job.spec["instance_id"])
    cfg = load_config({"objective": {"preset": job.spec.get("preset", "fastest")}})
    obj = Objective.from_instance(sc.inst, cfg)
    m = simulate(sc.inst, sc.net, Solution(best["routes"]), obj, depart)
    return RescoreOut(depart_s=depart, metrics=MetricsOut(**m.as_dict()))  # type: ignore[arg-type]


@router.websocket("/jobs/{job_id}/stream")
async def stream(ws: WebSocket, job_id: str) -> None:
    await ws.accept()
    job = state.jobs().get(job_id)
    if job is None:
        await ws.send_json({"type": "error", "message": "Unknown job"})
        await ws.close()
        return
    i = 0
    try:
        while True:
            while i < len(job.messages):
                await ws.send_json(job.messages[i])
                i += 1
            if job.finished and i >= len(job.messages):
                break
            await asyncio.sleep(0.05)
        await ws.close()
    except WebSocketDisconnect:
        return
