"""E1 Correctness (static part): feasibility, gap to MILP optimum (n<=15) and CVRPLIB BKS."""

from __future__ import annotations

import logging
import os
import sys

for _v in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from taqpso.baselines.milp import solve_milp  # noqa: E402
from taqpso.bench import cvrplib  # noqa: E402
from taqpso.config import load_config  # noqa: E402
from taqpso.core.objective import Objective  # noqa: E402
from taqpso.solver.runner import solve  # noqa: E402
from taqpso.store.results import RunRecord, save_run  # noqa: E402
from tests.conftest import make_instance  # noqa: E402

log = logging.getLogger("e1")
CVRPLIB = ["A-n32-k5", "B-n31-k5", "E-n13-k4", "P-n16-k8", "F-n72-k4", "X-n101-k25"]


def main(budget_s: float = 10.0) -> None:
    logging.basicConfig(level=logging.INFO)
    rows: list[dict[str, object]] = []
    cfg = load_config()
    for seed in range(3):
        inst = make_instance(10, 100 + seed, Q=20)
        opt = solve_milp(inst, 60).objective
        r = solve(inst, cfg, "qpso", seed, budget_s=3)
        gap = (r.metrics.T - opt) / opt if opt else None
        save_run(
            RunRecord(
                experiment="e1",
                instance_id=inst.name,
                instance_hash=inst.hash(),
                config=cfg.to_dict(),
                config_hash=cfg.hash(),
                solver="qpso",
                seed=seed,
                budget_s=3,
                metrics={"T": r.metrics.T, "opt": opt, "gap_to_opt": gap, "feasible": r.feasible},
                trace=r.trace,
            )
        )
        log.info("%s gap to optimum %s", inst.name, gap)
        rows.append(
            {
                "instance": inst.name,
                "n": inst.n,
                "reference": "MILP optimum",
                "T": r.metrics.T,
                "ref_value": opt,
                "gap_pct": 100 * gap if gap is not None else None,
                "feasible": r.feasible,
            }
        )
    for name in CVRPLIB:
        try:
            inst, bks = cvrplib.load(name)
        except Exception as e:  # noqa: BLE001
            log.warning("skip %s: %s", name, e)
            continue
        obj = Objective.from_instance(inst, cfg)
        r = solve(inst, cfg, "qpso", 0, budget_s=budget_s, objective=obj)
        gap = (r.metrics.T - bks) / bks if bks else None
        save_run(
            RunRecord(
                experiment="e1",
                instance_id=name,
                instance_hash=inst.hash(),
                config=cfg.to_dict(),
                config_hash=cfg.hash(),
                solver="qpso",
                seed=0,
                budget_s=budget_s,
                metrics={
                    "T": r.metrics.T,
                    "bks": bks,
                    "gap_to_bks": gap,
                    "feasible": r.feasible,
                    "K": r.metrics.K,
                },
                trace=r.trace,
            )
        )
        log.info("%s T=%s bks=%s gap=%s feasible=%s", name, r.metrics.T, bks, gap, r.feasible)
        rows.append(
            {
                "instance": name,
                "n": inst.n,
                "reference": "CVRPLIB BKS",
                "T": r.metrics.T,
                "ref_value": bks,
                "gap_pct": 100 * gap if gap is not None else None,
                "feasible": r.feasible,
            }
        )
    import pandas as pd

    from taqpso.config import REPO_ROOT

    out = REPO_ROOT / "results" / "e1"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "table.csv", index=False)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 10.0)
