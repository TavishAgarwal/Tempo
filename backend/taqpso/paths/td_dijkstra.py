"""Earliest-arrival Dijkstra with IGP edge costs (valid because travel times are FIFO)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numba import njit
from numpy.typing import NDArray

from taqpso.graph.model import Graph
from taqpso.traffic.igp import edge_time_c


@njit(cache=True)
def _td_tree(indptr, edge_to, length, v0, rc, fac, src, dst, t0, slot_s, thr):  # type: ignore[no-untyped-def]
    """Return (arrival time per node, predecessor edge per node). dst < 0: full tree."""
    V = indptr.shape[0] - 1
    arr = np.full(V, np.inf)
    pe = np.full(V, -1, dtype=np.int64)
    done = np.zeros(V, dtype=np.bool_)
    cap = edge_to.shape[0] + V + 2
    hk = np.empty(cap)
    hv = np.empty(cap, dtype=np.int64)
    n = 0
    arr[src] = t0
    hk[0] = t0
    hv[0] = src
    n = 1
    while n > 0:
        # pop min
        t = hk[0]
        u = hv[0]
        n -= 1
        if n > 0:
            hk[0] = hk[n]
            hv[0] = hv[n]
            i = 0
            while True:
                l = 2 * i + 1
                r = l + 1
                m = i
                if l < n and hk[l] < hk[m]:
                    m = l
                if r < n and hk[r] < hk[m]:
                    m = r
                if m == i:
                    break
                hk[i], hk[m] = hk[m], hk[i]
                hv[i], hv[m] = hv[m], hv[i]
                i = m
        if done[u]:
            continue
        done[u] = True
        if u == dst:
            break
        for e in range(indptr[u], indptr[u + 1]):
            v = edge_to[e]
            if done[v]:
                continue
            row = fac[rc[e]] if rc.shape[0] > 0 else fac[e]
            dt, _ = edge_time_c(length[e], v0[e], row, t, slot_s, thr)
            na = t + dt
            if na < arr[v]:
                arr[v] = na
                pe[v] = e
                i = n
                n += 1
                hk[i] = na
                hv[i] = v
                while i > 0:
                    p = (i - 1) // 2
                    if hk[p] <= hk[i]:
                        break
                    hk[p], hk[i] = hk[i], hk[p]
                    hv[p], hv[i] = hv[i], hv[p]
                    i = p
    return arr, pe


@dataclass
class Path:
    edges: NDArray[np.int32]
    nodes: NDArray[np.int32]
    arrival_s: float
    travel_s: float
    distance_m: float


def _extract(g: Graph, pe: NDArray[np.int64], src: int, dst: int) -> list[int]:
    seq: list[int] = []
    cur = dst
    while cur != src:
        e = int(pe[cur])
        if e < 0:
            raise ValueError("destination unreachable")
        seq.append(e)
        cur = int(g.edge_from[e])
    seq.reverse()
    return seq


def td_tree(
    g: Graph,
    fac: NDArray[np.float64],
    src: int,
    t0: float,
    slot_s: float,
    per_edge: bool = False,
    dst: int = -1,
    thr: float = 0.5,
) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    rc = np.empty(0, dtype=np.int8) if per_edge else g.road_class
    expected = g.n_edges if per_edge else int(g.road_class.max()) + 1
    if fac.shape[0] < expected:
        raise ValueError(f"factor table has {fac.shape[0]} rows, need {expected}")
    return _td_tree(
        g.indptr,
        g.edge_to,
        g.length_m,
        g.freeflow_mps,
        rc,
        np.ascontiguousarray(fac),
        src,
        dst,
        t0,
        slot_s,
        thr,
    )  # type: ignore[no-any-return]


def td_shortest_path(
    g: Graph,
    fac: NDArray[np.float64],
    src: int,
    dst: int,
    t0: float,
    slot_s: float = 900.0,
    per_edge: bool = False,
) -> Path:
    arr, pe = td_tree(g, fac, src, t0, slot_s, per_edge, dst)
    if not np.isfinite(arr[dst]):
        raise ValueError("destination unreachable")
    edges = np.asarray(_extract(g, pe, src, dst), dtype=np.int32)
    nodes = np.r_[src, g.edge_to[edges]].astype(np.int32)
    return Path(edges, nodes, float(arr[dst]), float(arr[dst] - t0), float(g.length_m[edges].sum()))
