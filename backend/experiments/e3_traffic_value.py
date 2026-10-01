"""E3: realised travel-time reduction of TD planning vs static (free-flow) planning."""

from __future__ import annotations

import logging

import pandas as pd

from experiments import plots, stats
from experiments.driver import load_experiment, run_jobs
from taqpso.config import REPO_ROOT, load_config
from taqpso.store.results import export_csv, load_runs

log = logging.getLogger("e3")
OUT = REPO_ROOT / "results" / "e3"
N_OF = {"delhi_n30": 30, "delhi_n50": 50, "delhi_demo": 100}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    spec = load_experiment("e3")
    cfg = load_config()
    jobs = []
    for inst in spec["instances"]:
        ns = cfg.seeds.small_n if N_OF[inst] <= cfg.seeds.small_n_threshold else cfg.seeds.default_n
        for dep in spec["departures_h"]:
            for plan in ("static", "td"):
                for seed in range(ns):
                    jobs.append(
                        {
                            "exp": "e3",
                            "instance": inst,
                            "solver": spec["solver"],
                            "seed": seed,
                            "budget_s": spec["budget_s"],
                            "plan": plan,
                            "depart_h": dep,
                        }
                    )
    run_jobs(jobs)
    recs = load_runs(experiment="e3")
    OUT.mkdir(parents=True, exist_ok=True)
    export_csv(recs, OUT / "runs.csv")
    df = pd.DataFrame(
        [
            {
                "instance": r.instance_id,
                "depart_h": r.extra["depart_h"],
                "plan": r.extra["plan"],
                "seed": r.seed,
                "T_min": r.metrics["T"] / 60,
                "C_min": r.metrics["C"] / 60,
                "J": r.metrics["J"],
            }
            for r in recs
        ]
    )
    rows = []
    for (inst, dep), g in df.groupby(["instance", "depart_h"]):
        p = g.pivot(index="seed", columns="plan", values="T_min").dropna()
        red = 100 * (p["static"] - p["td"]) / p["static"]
        rows.append(
            {
                "instance": inst,
                "depart_h": dep,
                "n_seeds": len(p),
                "static_median_T_min": p["static"].median(),
                "td_median_T_min": p["td"].median(),
                "median_reduction_pct": red.median(),
                "wilcoxon_p": stats.wilcoxon_p(p["td"].to_numpy(), p["static"].to_numpy()),
                "A12_td_better": stats.a12(p["td"].to_numpy(), p["static"].to_numpy()),
            }
        )
        plots.boxplot(
            {"static plan": p["static"].tolist(), "TD plan": p["td"].tolist()},
            OUT,
            f"box_{inst}_{dep}",
            f"{inst} depart {dep:g}h: realised travel time",
            "minutes (simulator)",
        )
    t = pd.DataFrame(rows)
    t["holm_p"] = stats.holm(t["wilcoxon_p"].tolist())
    t.to_csv(OUT / "table.csv", index=False)
    log.info("\n%s", t.to_string())


if __name__ == "__main__":
    main()
