from __future__ import annotations

from fastapi import APIRouter, HTTPException

from taqpso.api import state
from taqpso.api.schemas import EmissionsOut, LiveOut
from taqpso.bench import tomtom
from taqpso.config import CONFIG_DIR, load_yaml
from taqpso.core.solution import Solution

router = APIRouter()


@router.get("/live", response_model=LiveOut)
def live(refresh: bool = False) -> LiveOut:
    """Latest TomTom per-road-class speed ratios (cached snapshot; refresh=true re-fetches)."""
    try:
        ratios, stamp = tomtom.live_ratios(max_age_s=0.0 if refresh else 1e12, refresh=refresh)
    except tomtom.TomTomError as e:
        return LiveOut(available=False, label=tomtom.LABEL, message=str(e))
    return LiveOut(
        available=True,
        label=tomtom.LABEL,
        fetched_at=stamp,
        age_s=tomtom.snapshot_age_s(),
        ratios=ratios,
    )


@router.get("/jobs/{job_id}/emissions", response_model=EmissionsOut)
def emissions(job_id: str) -> EmissionsOut:
    """Estimated emissions of the job's current plan (illustrative speed-based curve)."""
    from taqpso.sim.simulator import simulate_emissions

    job = state.jobs().get(job_id)
    best = job.best() if job else None
    if job is None or best is None:
        raise HTTPException(404, "No plan to evaluate for this job")
    sc = state.scenario(job.spec["instance_id"])
    depart = float(best.get("depart", job.spec.get("depart_s") or sc.inst.depart_s))
    kg = simulate_emissions(sc.inst, sc.net, Solution(best["routes"]), depart)
    label = load_yaml(CONFIG_DIR / "emissions.yaml")["label"]
    return EmissionsOut(kg=kg, label=label)
