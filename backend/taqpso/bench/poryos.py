"""Poryos2026 TDVRP loader + official checker hook (via mamut-routing-lib, bench extra).

Arrival-time functions (ATFs) are sampled into the solver's slot tables: tau(t) = f(t) - t at
slot starts over the instance horizon. NOTE: written against mamut-routing-lib 0.12 and not yet
exercised on real Poryos2026 files (the instance collection is not bundled / downloaded here).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from taqpso.core.instance import Instance, TravelTables
from taqpso.core.solution import Solution


def _xy(c: Any) -> tuple[float, float]:
    if hasattr(c, "x"):
        return float(c.x), float(c.y)
    return float(c[0]), float(c[1])


def load_poryos(path: str | Path, n_slots: int = 96) -> tuple[Instance, Any]:
    """Return (Instance with sampled tables, LoadedTDInstance for the official checker)."""
    from mamut_routing_lib.td import load_td_instance

    loaded = load_td_instance(path, verify_sha256=False)
    ins, atfs = loaded.instance, loaded.atfs
    N = ins.num_customers + 1
    lo, hi = atfs.horizon
    slot_s = (hi - lo) / n_slots
    tau = np.zeros((N, N, n_slots), dtype=np.float32)
    for (i, j), f in atfs.arcs.items():
        for k in range(n_slots):
            t = lo + k * slot_s
            tau[i, j, k] = f.evaluate(t) - t
    dist = tau[:, :, 0].copy()
    tb = TravelTables(tau, dist, np.zeros_like(tau), slot_s)
    svc = np.asarray(getattr(ins, "service_times", [0] * N), dtype=np.float32)
    twl = getattr(ins, "time_windows", None)
    tw = None if twl is None else np.asarray(twl, dtype=np.float64)
    inst = Instance(
        ins.instance_name,
        np.asarray([_xy(c) for c in ins.coordinates]),
        np.asarray(ins.demands, dtype=np.int32),
        int(ins.vehicle_capacity),
        tb,
        svc,
        depart_s=float(lo),
        meta={"source": "poryos2026", "problem": "TDVRPTW" if tw is not None else "TDVRP"},
        tw=tw,
    )
    return inst, loaded


def official_cost(loaded: Any, sol: Solution) -> float:
    """Score a solution with the official TD checker (duration objective)."""
    from mamut_routing_lib import BenchmarkSolution
    from mamut_routing_lib.td import check_td_solution

    res = check_td_solution(
        loaded,
        BenchmarkSolution(
            instance_name=loaded.instance.instance_name, routes=[list(r) for r in sol.routes]
        ),
    )
    if not res.is_valid() or res.routing_cost is None:
        raise ValueError(f"official checker rejected the solution: {res.error_message}")
    return float(res.routing_cost)
