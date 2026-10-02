"""Run records (JSON) and CSV export. All numbers shown anywhere come from here."""

from __future__ import annotations

import logging
import platform
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from taqpso.config import REPO_ROOT, RESULTS_DIR

log = logging.getLogger(__name__)


def git_info() -> dict[str, Any]:
    try:
        h = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True
            ).stdout.strip()
        )
        return {"commit": h, "dirty": dirty}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"commit": "unknown", "dirty": True}


def machine_info() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "processor": platform.processor(),
    }


class RunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    kind: str = "solve"  # solve | experiment | incident | path
    experiment: str | None = None
    instance_id: str
    instance_hash: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    config_hash: str = ""
    solver: str
    seed: int
    budget_s: float
    commit: dict[str, Any] = Field(default_factory=git_info)
    machine: dict[str, Any] = Field(default_factory=machine_info)
    created_at: float = Field(default_factory=time.time)
    metrics: dict[str, Any] = Field(default_factory=dict)
    solution: dict[str, Any] | None = None
    trace: list[list[float]] = Field(default_factory=list)  # [t, best J, best T]
    extra: dict[str, Any] = Field(default_factory=dict)


def save_run(rec: RunRecord, root: Path | None = None) -> Path:
    base = (root or RESULTS_DIR) / "runs"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{rec.run_id}.json"
    path.write_text(rec.model_dump_json(indent=1))
    return path


def load_runs(root: Path | None = None, experiment: str | None = None) -> list[RunRecord]:
    base = (root or RESULTS_DIR) / "runs"
    out: list[RunRecord] = []
    if not base.exists():
        return out
    for p in sorted(base.glob("*.json")):
        try:
            rec = RunRecord.model_validate_json(p.read_text())
        except ValueError:
            log.warning("skipping unreadable run record %s", p)
            continue
        if experiment is None or rec.experiment == experiment:
            out.append(rec)
    return out


def export_csv(records: list[RunRecord], path: Path) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in records:
        row = {
            "run_id": r.run_id,
            "experiment": r.experiment,
            "instance": r.instance_id,
            "solver": r.solver,
            "seed": r.seed,
            "budget_s": r.budget_s,
            "commit": r.commit.get("commit"),
        }
        row.update({f"m_{k}": v for k, v in r.metrics.items() if not isinstance(v, (list, dict))})
        rows.append(row)
    keys = sorted({k for row in rows for k in row})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
