"""Ground-truth simulator: walk every route edge by edge with IGP on the road graph.

All solvers (TA-QPSO, PSO, GA, random, PyVRP, MILP, ...) are scored only by this function.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numba import njit
from numpy.typing import NDArray

from taqpso.config import load_emission_params
from taqpso.core.instance import Instance
from taqpso.core.objective import Metrics, Objective
from taqpso.core.solution import Solution
from taqpso.graph.model import Graph
from taqpso.traffic.emissions import path_emissions
from taqpso.traffic.igp import path_time
from taqpso.traffic.pair_tables import PairData


@dataclass
class Network:
    """Everything the simulator needs: graph, stored leg paths and effective speed factors."""

    graph: Graph
    pairs: PairData
    fac: NDArray[np.float64]  # (n_classes, S) or (E, S) when per_edge
    slot_s: float
    thr: float
    per_edge: bool = False

    @property
    def road_class(self) -> NDArray[np.int8]:
        return np.empty(0, dtype=np.int8) if self.per_edge else self.graph.road_class


@njit(cache=True)
def _sim_route(route, N, ptr, edges, length, v0, fac, rc, depart, slot_s, thr, svc):  # type: ignore[no-untyped-def]
    t = depart
    T = 0.0
    D = 0.0
    C = 0.0
    prev = 0
    for k in range(route.shape[0] + 1):
        c = route[k] if k < route.shape[0] else 0
        p = prev * N + c
        tt, d, cg = path_time(edges[ptr[p] : ptr[p + 1]], length, v0, fac, rc, t, slot_s, thr)
        T += tt
        D += d
        C += cg
        t += tt + svc[c]
        prev = c
    return T, D, C, t


def simulate(
    inst: Instance, net: Network, sol: Solution, obj: Objective, depart: float | None = None
) -> Metrics:
    dep = inst.depart_s if depart is None else depart
    g, pd = net.graph, net.pairs
    T = D = C = 0.0
    rT: list[float] = []
    loads: list[int] = []
    for r in sol.routes:
        if not r:
            continue
        arr = np.asarray(r, dtype=np.int32)
        t, d, c, _ = _sim_route(
            arr,
            pd.N,
            pd.path_ptr,
            pd.path_edges,
            g.length_m,
            g.freeflow_mps,
            net.fac,
            net.road_class,
            dep,
            net.slot_s,
            net.thr,
            inst.service,
        )
        T += t
        D += d
        C += c
        rT.append(t)
        loads.append(int(inst.demand[arr].sum()))
    return Metrics(T, D, C, obj.J(T, D, C), len(rT), tuple(rT), tuple(loads))


@njit(cache=True)
def _emis_route(route, N, ptr, edges, length, v0, fac, rc, depart, slot_s, thr, svc, p):  # type: ignore[no-untyped-def]
    t = depart
    g = 0.0
    prev = 0
    for k in range(route.shape[0] + 1):
        c = route[k] if k < route.shape[0] else 0
        q = prev * N + c
        e = edges[ptr[q] : ptr[q + 1]]
        tt, _, _ = path_time(e, length, v0, fac, rc, t, slot_s, thr)
        g += path_emissions(e, length, v0, fac, rc, t, slot_s, p)
        t += tt + svc[c]
        prev = c
    return g


def simulate_emissions(
    inst: Instance, net: Network, sol: Solution, depart: float | None = None
) -> float:
    """Estimated emissions (kg) of a plan, walking the same edge-by-edge model as `simulate`."""
    p = load_emission_params()
    dep = inst.depart_s if depart is None else depart
    g, pd = net.graph, net.pairs
    tot = 0.0
    for r in sol.routes:
        if r:
            tot += _emis_route(
                np.asarray(r, dtype=np.int32),
                pd.N,
                pd.path_ptr,
                pd.path_edges,
                g.length_m,
                g.freeflow_mps,
                net.fac,
                net.road_class,
                dep,
                net.slot_s,
                net.thr,
                inst.service,
                p,
            )
    return tot / 1000.0
