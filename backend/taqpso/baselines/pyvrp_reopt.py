"""B3: PyVRP snapshot re-solve of the remaining problem (static matrix at t_e)."""

from __future__ import annotations

import numpy as np
from pyvrp import Model
from pyvrp.stop import MaxRuntime

from taqpso.baselines.pyvrp_adapter import slot_matrix
from taqpso.dynamic.reopt import ReoptProblem


def solve_pyvrp_reopt(
    prob: ReoptProblem, budget_s: float, seed: int, t_e: float
) -> list[list[int]]:
    """Return per-vehicle routes in original customer ids."""
    sub, fl = prob.sub, prob.fleet
    D = np.rint(slot_matrix(sub, t_e)).astype(int)
    N = D.shape[0]
    m = sub.n
    model = Model()
    locs = [
        model.add_location(x=float(sub.coords[i, 0]), y=float(sub.coords[i, 1])) for i in range(N)
    ]
    main = model.add_depot(locs[0])
    for i in range(1, m + 1):
        model.add_client(locs[i], delivery=int(sub.demand[i]))
    starts = {}
    for v in range(fl.size):
        sn = int(fl.snode[v])
        if sn > 0 and sn not in starts:
            starts[sn] = model.add_depot(locs[sn])
    for v in range(fl.size):
        sn = int(fl.snode[v])
        model.add_vehicle_type(
            1,
            capacity=int(fl.cap[v]),
            start_depot=starts.get(sn, main),
            end_depot=main,
            tw_early=max(0, int(round(fl.stime[v] - t_e))),
        )
    for i, a in enumerate(locs):
        for j, b in enumerate(locs):
            if i != j:
                model.add_edge(a, b, distance=int(D[i, j]), duration=int(D[i, j]))
    res = model.solve(stop=MaxRuntime(budget_s), seed=seed, display=False)
    out: list[list[int]] = [[] for _ in range(fl.size)]
    for r in res.best.routes():
        out[int(r.vehicle_type())] = [
            prob.remaining[int(a.idx)] for a in r.schedule() if str(a.type).endswith("CLIENT")
        ]
    return out
