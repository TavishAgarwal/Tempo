from __future__ import annotations

from fastapi import APIRouter, HTTPException

from taqpso.api import state
from taqpso.api.schemas import IncidentCreated, IncidentRequest
from taqpso.traffic.incidents import edges_in_polygon

router = APIRouter()


@router.post("/incidents", response_model=IncidentCreated)
def create_incident(req: IncidentRequest) -> IncidentCreated:
    base = state.jobs().get(req.job_id)
    best = base.best() if base else None
    if base is None or best is None:
        raise HTTPException(404, "The base job has no plan yet")
    sc = state.scenario(base.spec["instance_id"])
    if req.edges:
        edges = list(req.edges)
    elif req.polygon:
        edges = [int(e) for e in edges_in_polygon(sc.net.graph, req.polygon)]
    else:
        raise HTTPException(422, "Provide edges or a polygon")
    if not edges:
        raise HTTPException(422, "No road segments inside the selected area")
    spec = {
        "instance_id": base.spec["instance_id"],
        "routes": best["routes"],
        "depart": float(best.get("depart", base.spec.get("depart_s") or sc.inst.depart_s)),
        "preset": base.spec.get("preset", "fastest"),
        "edges": edges,
        "factor": req.factor,
        "t_start": req.t_start,
        "t_end": req.t_end,
        "budget_s": req.budget_s,
        "mu": req.mu,
        "seed": req.seed,
    }
    job = state.jobs().submit("incident", spec)
    return IncidentCreated(job_id=job.id, affected_edges=len(edges))
