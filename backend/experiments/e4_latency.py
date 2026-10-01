"""E4b: safe-plan (fallback B0) latency, measured one run at a time in a single process.

The E4 quality experiment runs many worker processes in parallel, which inflates wall-clock
columns; this micro-benchmark isolates the latency gate (< 1 s). Timed region = everything the API
needs before it can stream the safe plan: vehicle states, lean incident world (re-pathing the legs
the old plan drives), remaining-cost metrics. Kernels are warmed first, as the API does at startup.
"""

from __future__ import annotations

import logging
import os
import time

for _v in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from experiments.driver import load_experiment  # noqa: E402
from experiments.e4_incident import OUT, base_plan, pick_edges  # noqa: E402
from taqpso.bench.make_scenarios import load_scenario  # noqa: E402
from taqpso.config import load_config  # noqa: E402
from taqpso.core.objective import Objective  # noqa: E402
from taqpso.core.solution import Solution  # noqa: E402
from taqpso.dynamic.fallback import safe_plan  # noqa: E402
from taqpso.sim.dynamic_sim import simulate_remaining  # noqa: E402
from taqpso.store.results import RunRecord, save_run  # noqa: E402
from taqpso.traffic.incidents import Incident  # noqa: E402

log = logging.getLogger("e4_latency")
REPS = 30


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    spec = load_experiment("e4")
    cfg = load_config()
    sc = load_scenario(spec["instance"])
    inst = sc.inst
    obj = Objective.from_instance(inst, cfg)
    plan = Solution(base_plan(spec["instance"]))
    t_e = spec["t_e_h"] * 3600.0
    rows = []
    for scen, p in spec["scenarios"].items():
        inc = Incident(
            pick_edges(sc, plan.routes, p["k_edges"]),
            p["factor"],
            t_e,
            t_e + spec["duration_h"] * 3600,
        )
        safe_plan(inst, sc.net, plan, [inc], t_e)  # warm-up (untimed)
        ts = []
        for _ in range(REPS):
            t0 = time.perf_counter()
            fb, w = safe_plan(inst, sc.net, plan, [inc], t_e)
            simulate_remaining(inst, w.net, fb.states, fb.routes, obj, t_e)
            ts.append(time.perf_counter() - t0)
        a = np.asarray(ts)
        rows.append(
            {
                "scenario": scen,
                "edges": len(inc.edges),
                "affected_pairs": w.affected_pairs,
                "reps": REPS,
                "median_s": float(np.median(a)),
                "p95_s": float(np.percentile(a, 95)),
                "max_s": float(a.max()),
                "gate_lt_1s": bool(a.max() < 1.0),
            }
        )
        save_run(
            RunRecord(
                experiment="e4_latency",
                instance_id=inst.name,
                instance_hash=inst.hash(),
                config=cfg.to_dict(),
                config_hash=cfg.hash(),
                solver="safe_plan",
                seed=0,
                budget_s=0.0,
                metrics={k: v for k, v in rows[-1].items() if k != "scenario"} | {"samples": ts},
                extra={"scenario": scen},
            )
        )
        log.info("%s", rows[-1])
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "latency.csv", index=False)


if __name__ == "__main__":
    main()
