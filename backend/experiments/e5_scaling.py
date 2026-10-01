"""E5: runtime, memory and quality over time versus n."""

from __future__ import annotations

import logging
import os

import numpy as np
import pandas as pd

from experiments import plots
from experiments.driver import load_experiment, run_jobs
from taqpso.config import REPO_ROOT
from taqpso.store.results import export_csv, load_runs

log = logging.getLogger("e5")
OUT = REPO_ROOT / "results" / "e5"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    spec = load_experiment("e5")
    jobs = [
        {
            "exp": "e5",
            "instance": r["instance"],
            "solver": spec["solver"],
            "seed": s,
            "budget_s": r["budget_s"],
        }
        for r in spec["runs"]
        for s in range(spec["seeds"])
    ]
    if not os.environ.get("E5_ANALYSE_ONLY"):
        run_jobs(jobs, workers=4)  # fewer workers: long budgets, keep CPU contention low
    recs = load_runs(experiment="e5")
    OUT.mkdir(parents=True, exist_ok=True)
    export_csv(recs, OUT / "runs.csv")
    rows = []
    for inst in sorted(
        {r.instance_id for r in recs},
        key=lambda i: next(x.metrics["n"] for x in recs if x.instance_id == i),
    ):
        g = [r for r in recs if r.instance_id == inst]
        final = np.median([r.metrics["J"] for r in g])
        tf = float(np.median([r.trace[-1][1] for r in g if r.trace]))
        t2 = [next((p[0] for p in r.trace if p[1] <= tf * 1.02), np.nan) for r in g]
        rows.append(
            {
                "instance": inst,
                "n": g[0].metrics["n"],
                "budget_s": g[0].budget_s,
                "median_J": final,
                "median_T_min": np.median([r.metrics["T"] for r in g]) / 60,
                "median_time_to_2pct_s": float(np.nanmedian(t2)),
                "feasible_rate": float(np.mean([r.metrics["feasible"] for r in g])),
                "tau_table_mb": g[0].metrics["tau_mb"],
                "tables_total_mb": g[0].metrics["tables_mb"],
                "peak_rss_mb": max(r.metrics["rss_mb"] for r in g),
            }
        )
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "table.csv", index=False)
    plots.line(
        t["n"].tolist(),
        {"median time to within 2% (s)": t["median_time_to_2pct_s"].tolist()},
        OUT,
        "scaling_time",
        "TA-QPSO scaling",
        "customers n",
        "seconds",
    )
    plots.line(
        t["n"].tolist(),
        {"tau table (MB)": t["tau_table_mb"].tolist(), "peak RSS (MB)": t["peak_rss_mb"].tolist()},
        OUT,
        "scaling_memory",
        "Memory vs n",
        "customers n",
        "MB",
    )
    log.info("\n%s", t.to_string())


if __name__ == "__main__":
    main()
