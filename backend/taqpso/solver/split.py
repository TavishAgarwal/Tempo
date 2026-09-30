"""Prins/Bellman Split on a giant tour (Numba). Capacity enforced by construction.

Every route departs the depot at the same time, so a route's cost does not depend on other
routes: the DP stays exact under time-dependent travel times.
"""

from __future__ import annotations

import numpy as np
from numba import njit
from numpy.typing import NDArray

from taqpso.core.evaluate import lookup, tw_arrival
from taqpso.core.instance import Instance

INF = 1e300


def max_route_len(inst: Instance) -> int:
    """B = most customers that can ever share a vehicle (cheapest demands first)."""
    d = np.sort(inst.demand[1:])
    cum = np.cumsum(d)
    return int(max(1, int(np.searchsorted(cum, inst.Q, side="right"))))


@njit(cache=True)
def route_cost_table(g, n, demand, Q, tau, dist, cong, svc, depart, slot_s, cw, B):  # type: ignore[no-untyped-def]
    """cost[i, l] = cost of the route serving g[i : i+l] (inf if over capacity)."""
    cost = np.full((n, B + 1), INF)
    for i in range(n):
        load = 0
        t = depart
        prev = 0
        acc = 0.0
        W = 0.0
        F = 1e18
        for l in range(1, B + 1):
            j = i + l - 1
            if j >= n:
                break
            c = g[j]
            load += demand[c]
            if load > Q:
                break
            tt = lookup(tau, prev, c, t, slot_s)
            acc += cw[0] * tt + cw[1] * dist[prev, c] + cw[2] * lookup(cong, prev, c, t, slot_s)
            st, w, ok = tw_arrival(t + tt, c, svc)
            if not ok:
                break  # later customers can only arrive later: no longer feasible
            W += w
            slack = W + svc[c, 2] - st
            if slack < F:
                F = slack
            t = st + svc[c, 0]
            prev = c
            rt = lookup(tau, prev, 0, t, slot_s)
            ret = cw[0] * rt + cw[1] * dist[prev, 0] + cw[2] * lookup(cong, prev, 0, t, slot_s)
            ret += cw[0] * (W - min(W, F))
            cost[i, l] = acc + ret
    return cost


@njit(cache=True)
def split_unlimited(cost, n, B):  # type: ignore[no-untyped-def]
    V = np.full(n + 1, INF)
    pred = np.zeros(n + 1, dtype=np.int32)
    V[0] = 0.0
    for i in range(n):
        if V[i] >= INF:
            continue
        for l in range(1, B + 1):
            if i + l > n:
                break
            c = cost[i, l]
            if c >= INF:
                break
            v = V[i] + c
            if v < V[i + l]:
                V[i + l] = v
                pred[i + l] = i
    cuts = np.empty(n, dtype=np.int32)
    k = 0
    j = n
    while j > 0:
        cuts[k] = pred[j]
        k += 1
        j = pred[j]
    return cuts[:k][::-1].copy(), V[n]


def split(
    g: NDArray[np.int32], inst: Instance, cw: NDArray[np.float64], B: int | None = None
) -> tuple[NDArray[np.int32], float]:
    """Return (route start indices into g, total cost)."""
    n = inst.n
    B = B or max_route_len(inst)
    tb = inst.tables
    cost = route_cost_table(
        g,
        n,
        inst.demand,
        inst.Q,
        tb.tau,
        tb.dist,
        tb.cong,
        inst.sv,
        inst.depart_s,
        tb.slot_s,
        cw,
        B,
    )
    return split_unlimited(cost, n, B)
