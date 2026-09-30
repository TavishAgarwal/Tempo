"""Fixed-fleet Split: at most K routes, O(K n B). Falls back to fewest routes when infeasible."""

from __future__ import annotations

import numpy as np
from numba import njit
from numpy.typing import NDArray

from taqpso.core.evaluate import lookup, tw_arrival
from taqpso.core.fleet import Fleet
from taqpso.core.instance import Instance
from taqpso.solver.split import INF, max_route_len, route_cost_table


@njit(cache=True)
def split_fixed_k(cost, n, B, K):  # type: ignore[no-untyped-def]
    """V[k, j]: best cost covering first j customers with exactly k routes (1..K)."""
    V = np.full((K + 1, n + 1), INF)
    pred = np.zeros((K + 1, n + 1), dtype=np.int32)
    V[0, 0] = 0.0
    for k in range(1, K + 1):
        for i in range(n):
            if V[k - 1, i] >= INF:
                continue
            for l in range(1, B + 1):
                if i + l > n:
                    break
                c = cost[i, l]
                if c >= INF:
                    break
                v = V[k - 1, i] + c
                if v < V[k, i + l]:
                    V[k, i + l] = v
                    pred[k, i + l] = i
    best = INF
    bk = -1
    for k in range(1, K + 1):
        if V[k, n] < best:
            best = V[k, n]
            bk = k
    if bk < 0:
        return np.empty(0, dtype=np.int32), INF
    cuts = np.empty(bk, dtype=np.int32)
    j = n
    for k in range(bk, 0, -1):
        cuts[k - 1] = pred[k, j]
        j = pred[k, j]
    return cuts, best


@njit(cache=True)
def min_routes(cost, n, B):  # type: ignore[no-untyped-def]
    """Fewest-routes partition (cost as tie-break): used when K is too small for the tour."""
    R = np.full(n + 1, 1 << 30, dtype=np.int64)
    V = np.full(n + 1, INF)
    pred = np.zeros(n + 1, dtype=np.int32)
    R[0] = 0
    V[0] = 0.0
    for i in range(n):
        if R[i] >= (1 << 30):
            continue
        for l in range(1, B + 1):
            if i + l > n:
                break
            c = cost[i, l]
            if c >= INF:
                break
            r = R[i] + 1
            v = V[i] + c
            if r < R[i + l] or (r == R[i + l] and v < V[i + l]):
                R[i + l] = r
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


def split_fleet(
    g: NDArray[np.int32], inst: Instance, cw: NDArray[np.float64], K: int, B: int | None = None
) -> tuple[NDArray[np.int32], float, int]:
    """Return (cuts, cost, excess_vehicles). excess > 0 means K was infeasible for this tour."""
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
    cuts, c = split_fixed_k(cost, n, B, K)
    if len(cuts) > 0:
        return cuts, float(c), 0
    cuts, c = min_routes(cost, n, B)
    return cuts, float(c), max(0, len(cuts) - K)


@njit(cache=True)
def _vehicle_costs(g, n, demand, cap, tau, dist, cong, svc, snode, stime, slot_s, cw, B):  # type: ignore[no-untyped-def]
    """cost[k, i, l]: vehicle k serves g[i : i+l] starting from its own (node, time) state."""
    R = snode.shape[0]
    cost = np.full((R, n + 1, B + 1), INF)
    for k in range(R):
        t0 = stime[k]
        s0 = snode[k]
        rt = lookup(tau, s0, 0, t0, slot_s)
        empty = cw[0] * rt + cw[1] * dist[s0, 0] + cw[2] * lookup(cong, s0, 0, t0, slot_s)
        for i in range(n + 1):
            cost[k, i, 0] = empty
        for i in range(n):
            load = 0
            t = t0
            prev = s0
            acc = 0.0
            for l in range(1, B + 1):
                j = i + l - 1
                if j >= n:
                    break
                c = g[j]
                load += demand[c]
                if load > cap[k]:
                    break
                tt = lookup(tau, prev, c, t, slot_s)
                acc += cw[0] * tt + cw[1] * dist[prev, c] + cw[2] * lookup(cong, prev, c, t, slot_s)
                arr, w, ok = tw_arrival(t + tt, c, svc)  # no departure shift for in-field vehicles
                if not ok:
                    break
                acc += cw[0] * w
                t = arr + svc[c, 0]
                prev = c
                rt = lookup(tau, prev, 0, t, slot_s)
                ret = cw[0] * rt + cw[1] * dist[prev, 0] + cw[2] * lookup(cong, prev, 0, t, slot_s)
                cost[k, i, l] = acc + ret
    return cost


@njit(cache=True)
def _split_vehicles(cost, n, B):  # type: ignore[no-untyped-def]
    R = cost.shape[0]
    V = np.full((R + 1, n + 1), INF)
    pred = np.zeros((R + 1, n + 1), dtype=np.int32)
    V[0, 0] = 0.0
    for k in range(1, R + 1):
        for i in range(n + 1):
            if V[k - 1, i] >= INF:
                continue
            for l in range(0, B + 1):
                if i + l > n:
                    break
                c = cost[k - 1, i, l]
                if c >= INF:
                    break
                v = V[k - 1, i] + c
                if v < V[k, i + l]:
                    V[k, i + l] = v
                    pred[k, i + l] = i
    bounds = np.zeros(R + 1, dtype=np.int32)
    if V[R, n] >= INF:
        return bounds, INF
    j = n
    bounds[R] = n
    for k in range(R, 0, -1):
        j = pred[k, j]
        bounds[k - 1] = j
    return bounds, V[R, n]


def split_vehicles(
    g: NDArray[np.int32],
    inst: Instance,
    cw: NDArray[np.float64],
    fleet: Fleet,
    B: int | None = None,
) -> tuple[NDArray[np.int32], float]:
    """Vehicles-in-field Split: vehicle k gets g[bounds[k]:bounds[k+1]] (possibly empty).

    Returns (bounds, cost); cost = inf when this tour cannot be partitioned feasibly.
    """
    B = B or max_route_len(inst)
    tb = inst.tables
    cost = _vehicle_costs(
        g,
        inst.n,
        inst.demand,
        fleet.cap,
        tb.tau,
        tb.dist,
        tb.cong,
        inst.sv,
        fleet.snode,
        fleet.stime,
        tb.slot_s,
        cw,
        B,
    )
    return _split_vehicles(cost, inst.n, B)  # type: ignore[no-any-return]
