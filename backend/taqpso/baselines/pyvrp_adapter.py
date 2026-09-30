"""PyVRP baseline: static matrix in, routes out. Never called from inside TA-QPSO."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pyvrp import Model
from pyvrp.stop import MaxRuntime

from taqpso.core.instance import Instance
from taqpso.core.solution import Solution


def slot_matrix(inst: Instance, depart_s: float | None = None) -> NDArray[np.float64]:
    """Static travel times: the table slot of the departure time (single slot if static)."""
    tb = inst.tables
    dep = inst.depart_s if depart_s is None else depart_s
    k = int((dep // tb.slot_s) % tb.n_slots) if tb.n_slots > 1 else 0
    return tb.tau[:, :, k].astype(np.float64)


def solve_pyvrp(
    inst: Instance, budget_s: float, seed: int = 0, matrix: NDArray[np.float64] | None = None
) -> Solution:
    m = matrix if matrix is not None else slot_matrix(inst)
    D = np.rint(m).astype(int)
    model = Model()
    model.add_vehicle_type(
        num_available=inst.K if inst.K is not None else inst.n, capacity=int(inst.Q)
    )
    model.add_depot(model.add_location(x=float(inst.coords[0, 0]), y=float(inst.coords[0, 1])))
    for i in range(1, inst.n + 1):
        loc = model.add_location(x=float(inst.coords[i, 0]), y=float(inst.coords[i, 1]))
        model.add_client(loc, delivery=int(inst.demand[i]))
    locs = model.locations
    for i, a in enumerate(locs):
        for j, b in enumerate(locs):
            if i != j:
                model.add_edge(a, b, distance=int(D[i, j]), duration=int(D[i, j]))
    res = model.solve(stop=MaxRuntime(budget_s), seed=seed, display=False)
    routes = [
        [int(a.idx) + 1 for a in r.schedule() if str(a.type).endswith("CLIENT")]
        for r in res.best.routes()
    ]
    return Solution(routes)
