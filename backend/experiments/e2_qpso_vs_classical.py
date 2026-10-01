"""E2: QPSO vs PSO / GA / random restart (+ PyVRP reference) at equal budget, plus ablation."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from experiments import plots, stats
from experiments.driver import load_experiment, run_jobs
from taqpso.config import REPO_ROOT, load_config
from taqpso.store.results import export_csv, load_runs

log = logging.getLogger("e2")
EID = "e2"
OUT = REPO_ROOT / "results" / EID


def build_jobs(spec: dict) -> list[dict]:  # type: ignore[type-arg]
    cfg = load_config()
    jobs = []
    names = list(dict.fromkeys(spec["solvers"] + spec["ablation"]))
    n_of = {
        "delhi_n30": 30,
        "delhi_n50": 50,
        "delhi_demo": 100,
        "delhi_n200": 200,
        "delhi_n500": 500,
    }
    for inst in spec["instances"]:
        for s in names:
            for seed in range(stats_seeds(n_of[inst], cfg)):
                jobs.append(
                    {
                        "exp": EID,
                        "instance": inst,
                        "solver": s,
                        "seed": seed,
                        "budget_s": spec.get("budgets", {}).get(inst, spec["budget_s"]),
                    }
                )
    return jobs


def stats_seeds(n: int, cfg) -> int:  # type: ignore[no-untyped-def]
    return cfg.seeds.small_n if n <= cfg.seeds.small_n_threshold else cfg.seeds.default_n


def analyse(spec: dict) -> None:  # type: ignore[type-arg]
    recs = load_runs(experiment=EID)
    OUT.mkdir(parents=True, exist_ok=True)
    export_csv(recs, OUT / "runs.csv")
    df = pd.DataFrame(
        [
            {
                "instance": r.instance_id,
                "solver": r.solver,
                "seed": r.seed,
                "J": r.metrics["J"],
                "T": r.metrics["T"],
                "t_last": r.trace[-1][0] if r.trace else r.metrics["elapsed_s"],
                "feasible": r.metrics["feasible"],
                "evaluations": r.metrics.get("evaluations", np.nan),
                "full_vnd": r.metrics.get("full_vnd", np.nan),
            }
            for r in recs
        ]
    )
    rows = []
    for inst, g in df.groupby("instance"):
        target = min(r.trace[-1][1] for r in recs if r.instance_id == inst and r.trace) * 1.01
        piv = g.pivot(index="seed", columns="solver", values="J")
        ps, labels = [], []
        for s in piv.columns:
            if s == "qpso":
                continue
            ok = piv[["qpso", s]].dropna()
            if len(ok) < 5:
                continue
            ps.append(stats.wilcoxon_p(ok["qpso"].to_numpy(), ok[s].to_numpy()))
            labels.append(s)
        adj = dict(zip(labels, stats.holm(ps), strict=True))
        for s, gs in g.groupby("solver"):
            rows.append(
                {
                    "instance": inst,
                    "method": s,
                    "n_runs": len(gs),
                    "median_J": gs["J"].median(),
                    "best_J": gs["J"].min(),
                    "median_T_min": gs["T"].median() / 60,
                    "feasible_rate": gs["feasible"].mean(),
                    "A12_qpso_better": stats.a12(
                        piv["qpso"].dropna().to_numpy(), gs["J"].to_numpy()
                    )
                    if s != "qpso"
                    else np.nan,
                    "holm_p_vs_qpso": adj.get(s, np.nan),
                    "median_evaluations": gs["evaluations"].median(),
                    "full_vnd_share": (gs["full_vnd"] / gs["evaluations"]).median(),
                    "time_to_1pct_of_best_s": float(
                        np.nanmedian(
                            [
                                next((p[0] for p in r.trace if p[1] <= target), np.nan)
                                for r in recs
                                if r.instance_id == inst and r.solver == s and r.trace
                            ]
                            or [np.nan]
                        )
                    ),
                }
            )
        sub = [
            r for r in recs if r.instance_id == inst and r.solver in ("qpso", "pso", "ga", "random")
        ]
        plots.convergence(
            sub,
            spec.get("budgets", {}).get(inst, spec["budget_s"]),
            OUT,
            f"convergence_{inst}",
            f"{inst}: best J vs time",
        )
        plots.boxplot(
            {s: g[g.solver == s]["J"].tolist() for s in sorted(g.solver.unique())},
            OUT,
            f"box_{inst}",
            f"{inst}: final J by method",
            "J (normalised)",
        )
    pd.DataFrame(rows).to_csv(OUT / "table.csv", index=False)
    log.info("wrote %s", OUT / "table.csv")


def main(eid: str = "e2") -> None:
    global EID, OUT
    EID, OUT = eid, REPO_ROOT / "results" / eid
    logging.basicConfig(level=logging.INFO)
    spec = load_experiment(eid)
    run_jobs(build_jobs(spec))
    analyse(spec)


if __name__ == "__main__":
    import sys

    main(sys.argv[1] if len(sys.argv) > 1 else "e2")
