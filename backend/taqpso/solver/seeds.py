"""Constructive seeds: nearest neighbour and sweep (also the NN reference for normalisation)."""

from __future__ import annotations

import numpy as np
from numba import njit
from numpy.typing import NDArray

from taqpso.core.evaluate import lookup, tw_arrival
from taqpso.core.instance import Instance
from taqpso.core.solution import Solution


@njit(cache=True)
def _nn_giant(demand, Q, tau, svc, depart, slot_s, n):  # type: ignore[no-untyped-def]
    visited = np.zeros(n + 1, dtype=np.bool_)
    tour = np.empty(n, dtype=np.int32)
    cuts = np.empty(n, dtype=np.int32)
    nr = 0
    k = 0
    while k < n:
        load = 0
        t = depart
        prev = 0
        cuts[nr] = k
        nr += 1
        while True:
            best = -1
            bt = 1e30
            for c in range(1, n + 1):
                if visited[c] or load + demand[c] > Q:
                    continue
                tt = lookup(tau, prev, c, t, slot_s)
                arr, w, ok = tw_arrival(t + tt, c, svc)
                if ok and arr - t < bt:
                    bt = arr - t
                    best = c
            if best < 0:
                if prev != 0:
                    break
                for c in range(1, n + 1):  # lone customer past its due time: serve it anyway
                    if not visited[c]:
                        best = c
                        bt = lookup(tau, 0, c, t, slot_s)
                        break
            visited[best] = True
            tour[k] = best
            k += 1
            load += demand[best]
            t += bt + svc[best, 0]
            prev = best
    return tour, cuts[:nr]


def nearest_neighbour(inst: Instance) -> Solution:
    tb = inst.tables
    tour, cuts = _nn_giant(inst.demand, inst.Q, tb.tau, inst.sv, inst.depart_s, tb.slot_s, inst.n)
    return Solution.from_giant_tour(tour, [int(c) for c in cuts])


def sweep_tour(inst: Instance) -> NDArray[np.int32]:
    """Customers sorted by polar angle around the depot (giant tour; Split cuts routes)."""
    d = inst.coords[1 : inst.n + 1] - inst.coords[0]
    ang = np.arctan2(d[:, 1], d[:, 0])
    return (np.argsort(ang, kind="stable") + 1).astype(np.int32)


def tour_to_keys(tour: NDArray[np.int32]) -> NDArray[np.float64]:
    """Keys whose stable argsort decodes to `tour`."""
    n = len(tour)
    keys = np.empty(n, dtype=np.float64)
    keys[tour - 1] = (np.arange(n) + 0.5) / n
    return keys
