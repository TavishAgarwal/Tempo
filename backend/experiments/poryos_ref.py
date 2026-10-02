"""Poryos2026 reference comparison (Phase 8): TA-QPSO vs KAYROS vs stored BKS, TDVRP and TDVRPTW.

Equal wall-clock budget, one thread each, run one after another (no parallel processes) so the
timings are comparable. Every solution is re-scored by the official mamut-routing-lib checker.
Losses are reported as well as wins (rules.md).

    python -m experiments.poryos_ref TDVRPTW 10 3
"""

from __future__ import annotations

import json
import logging
import os
import sys

for _v in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from taqpso.baselines.kayros_adapter import solve_kayros  # noqa: E402
from taqpso.bench.poryos import load_poryos, official_cost  # noqa: E402
from taqpso.config import DATA_DIR, load_config  # noqa: E402
from taqpso.core.solution import Solution  # noqa: E402
from taqpso.solver.runner import solve  # noqa: E402
from taqpso.store.results import RunRecord, save_run  # noqa: E402

log = logging.getLogger("poryos_ref")
CITIES = ["paris", "san_francisco", "tokyo"]
SIZES = [10, 25, 50]
VARIANT = "bpr-heavy"


def main(
    problem: str = "TDVRPTW", budget_s: float = 10.0, seeds: int = 3, sizes: list[int] | None = None
) -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    root = DATA_DIR / "raw" / "Poryos2026" / problem
    rows = []
    for city in CITIES:
        for n in sizes or SIZES:
            for p in sorted(root.glob(f"{city}/n={n}/*/{VARIANT}/*.vrp.json")):
                bks_f = p.with_name(p.name.replace(".vrp.json", ".bks.Duration.json"))
                if not bks_f.exists():
                    continue
                inst, loaded = load_poryos(p)
                bks = float(json.loads(bks_f.read_text())["cost"])
                q_best = k_best = float("inf")
                q_feas = 0
                for seed in range(seeds):
                    r = solve(inst, cfg, "qpso", seed, budget_s=budget_s)
                    try:
                        c = official_cost(loaded, r.solution)
                        q_feas += 1
                    except ValueError as e:
                        log.warning("%s qpso seed %d rejected by checker: %s", inst.name, seed, e)
                        c = float("inf")
                    q_best = min(q_best, c)
                    save_run(
                        RunRecord(
                            experiment=f"poryos_ref_{problem}",
                            instance_id=inst.name,
                            instance_hash=inst.hash(),
                            config=cfg.to_dict(),
                            config_hash=cfg.hash(),
                            solver="qpso",
                            seed=seed,
                            budget_s=budget_s,
                            metrics={"official_cost": c, "bks": bks, "feasible": c < float("inf")},
                            trace=r.trace,
                        )
                    )
                    k = solve_kayros(p, budget_s, seed)
                    kc = official_cost(loaded, Solution(k.routes))
                    k_best = min(k_best, kc)
                    save_run(
                        RunRecord(
                            experiment=f"poryos_ref_{problem}",
                            instance_id=inst.name,
                            instance_hash=inst.hash(),
                            config={"kayros": k.version},
                            config_hash="kayros-" + k.version,
                            solver="kayros",
                            seed=seed,
                            budget_s=budget_s,
                            metrics={
                                "official_cost": kc,
                                "bks": bks,
                                "feasible": True,
                                "note": k.note,
                            },
                            trace=[[t, v, v] for t, v in k.trace],
                        )
                    )
                row = {
                    "instance": inst.name,
                    "n": n,
                    "bks": bks,
                    "qpso_best": q_best,
                    "qpso_feasible_runs": q_feas,
                    "kayros_best": k_best,
                    "qpso_gap_pct": 100 * (q_best - bks) / bks,
                    "kayros_gap_pct": 100 * (k_best - bks) / bks,
                }
                log.info("%s", row)
                rows.append(row)
    out = DATA_DIR.parent / "results" / f"poryos_ref_{problem}.json"
    out.write_text(json.dumps(rows, indent=1))
    log.info("wrote %s", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(
        a[0] if a else "TDVRPTW",
        float(a[1]) if len(a) > 1 else 10.0,
        int(a[2]) if len(a) > 2 else 3,
    )
