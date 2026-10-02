"""Experiment tables and plots, served only from files derived from saved run records."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from taqpso.api.schemas import ResultTable
from taqpso.config import RESULTS_DIR

router = APIRouter()
TITLES = {
    "e1": "Correctness",
    "e2": "QPSO vs classical",
    "e3": "Traffic value",
    "e4": "Incident recovery",
    "e5": "Scaling",
}


@router.get("/results", response_model=list[ResultTable])
def results() -> list[ResultTable]:
    out = []
    for eid, title in TITLES.items():
        d = RESULTS_DIR / eid
        t = d / "table.csv"
        if not t.exists():
            continue
        df = pd.read_csv(t).astype(object).where(lambda x: x.notna(), None)
        files = sorted(p.name for p in d.iterdir() if p.is_file())
        out.append(
            ResultTable(
                experiment=eid,
                title=title,
                rows=[{str(k): v for k, v in r.items()} for r in df.to_dict("records")],
                files=files,
            )
        )
    return out


@router.get("/results/{experiment}/{name}")
def result_file(experiment: str, name: str) -> FileResponse:
    p = (RESULTS_DIR / experiment / name).resolve()
    if RESULTS_DIR.resolve() not in p.parents or not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p)
