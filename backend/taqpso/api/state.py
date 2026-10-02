"""Process-wide API state: scenario cache and job manager."""

from __future__ import annotations

from functools import lru_cache

from taqpso.api.jobs import JobManager
from taqpso.bench.make_scenarios import SCEN, Scenario, load_scenario

_jobs: JobManager | None = None


def jobs() -> JobManager:
    global _jobs
    if _jobs is None:
        _jobs = JobManager()
    return _jobs


def shutdown_jobs() -> None:
    global _jobs
    if _jobs is not None:
        _jobs.shutdown()
        _jobs = None


@lru_cache(maxsize=8)
def scenario(name: str) -> Scenario:
    if not (SCEN / f"{name}.json").exists():
        raise KeyError(name)
    return load_scenario(name)


def scenario_names() -> list[str]:
    return sorted(p.stem for p in SCEN.glob("*.json"))
