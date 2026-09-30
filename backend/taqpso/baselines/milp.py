"""MTZ CVRP formulation solved with HiGHS (via scipy.optimize.milp). For n <= ~15."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from taqpso.core.instance import Instance
from taqpso.core.solution import Solution


@dataclass
class MilpResult:
    solution: Solution | None
    objective: float | None
    bound: float | None
    gap: float | None
    optimal: bool


def solve_milp(inst: Instance, time_limit_s: float = 60.0) -> MilpResult:
    n = inst.n
    N = n + 1
    c = inst.tables.tau[:, :, 0].astype(np.float64)
    d = inst.demand.astype(np.float64)
    Q = float(inst.Q)
    arcs = [(i, j) for i in range(N) for j in range(N) if i != j]
    ai = {a: k for k, a in enumerate(arcs)}
    nx = len(arcs)
    nv = nx + n  # u_1..u_n
    cost = np.zeros(nv)
    for (i, j), k in ai.items():
        cost[k] = c[i, j]
    lo: list[float] = []
    hi: list[float] = []
    A = lil_matrix((2 * n + n * n + 2, nv))
    r = 0
    for i in range(1, N):
        for j in range(N):
            if j != i:
                A[r, ai[(i, j)]] = 1
        lo.append(1)
        hi.append(1)
        r += 1
        for j in range(N):
            if j != i:
                A[r, ai[(j, i)]] = 1
        lo.append(1)
        hi.append(1)
        r += 1
    for i in range(1, N):
        for j in range(1, N):
            if i == j:
                continue
            A[r, nx + i - 1] = 1
            A[r, nx + j - 1] = -1
            A[r, ai[(i, j)]] = Q
            lo.append(-np.inf)
            hi.append(Q - d[j])
            r += 1
    if inst.K is not None:
        for j in range(1, N):
            A[r, ai[(0, j)]] = 1
        lo.append(0)
        hi.append(inst.K)
        r += 1
    cons = LinearConstraint(A[:r].tocsr(), np.asarray(lo), np.asarray(hi))
    lb = np.zeros(nv)
    ub = np.ones(nv)
    lb[nx:] = d[1:]
    ub[nx:] = Q
    integrality = np.r_[np.ones(nx), np.zeros(n)]
    res = milp(
        cost,
        constraints=cons,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        options={"time_limit": time_limit_s, "disp": False},
    )
    if res.x is None:
        return MilpResult(None, None, None, None, False)
    x = np.rint(res.x[:nx]).astype(int)
    succ: dict[int, list[int]] = {}
    for (i, j), k in ai.items():
        if x[k]:
            succ.setdefault(i, []).append(j)
    routes = []
    for start in succ.get(0, []):
        route = []
        cur = start
        while cur != 0:
            route.append(cur)
            cur = succ[cur][0]
        routes.append(route)
    obj = float(res.fun)
    bound = float(getattr(res, "mip_dual_bound", obj))
    gap = (obj - bound) / max(obj, 1e-9)
    return MilpResult(Solution(routes), obj, bound, gap, bool(res.status == 0))
