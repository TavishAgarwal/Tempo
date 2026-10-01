"""Incident model: edge speed factors over a time window, applied as slot-level multipliers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from taqpso.graph.model import Graph
from taqpso.paths.td_dijkstra import td_tree
from taqpso.traffic.pair_tables import PairData


@dataclass(frozen=True)
class Incident:
    edges: tuple[int, ...]
    factor: float  # speed multiplier: 0.1 blocked, 0.4 heavy
    t_start: float  # seconds of day
    t_end: float


def edges_in_polygon(g: Graph, polygon: list[tuple[float, float]]) -> NDArray[np.int32]:
    """Edges whose both endpoints (lon, lat) fall inside the polygon (or its bounding region)."""
    from shapely.geometry import Point, Polygon

    poly = Polygon(polygon)
    inside = np.array([poly.contains(Point(x, y)) for x, y in g.node_xy])
    return np.nonzero(inside[g.edge_from] & inside[g.edge_to])[0].astype(np.int32)


def apply_incidents(
    g: Graph, fac_cls: NDArray[np.float64], incidents: list[Incident], slot_s: float
) -> NDArray[np.float64]:
    """Per-edge factor matrix (E, S): class profile times incident multipliers.

    Each slot is scaled by (1 - overlap_fraction * (1 - factor)), so the speed stays stepwise
    constant per slot and the IGP/FIFO guarantees are untouched.
    """
    S = fac_cls.shape[1]
    fe = fac_cls[g.road_class].copy()
    for inc in incidents:
        for k in range(S):
            a, b = k * slot_s, (k + 1) * slot_s
            ov = max(0.0, min(b, inc.t_end) - max(a, inc.t_start)) / slot_s
            if ov > 0:
                fe[np.asarray(inc.edges, dtype=np.int64), k] *= 1.0 - ov * (1.0 - inc.factor)
    return fe


def repath_pairs(
    g: Graph,
    pd: PairData,
    pairs: NDArray[np.int32],
    fac_e: NDArray[np.float64],
    t0: float,
    slot_s: float,
) -> PairData:
    """Replace the stored paths of `pairs` with incident-aware earliest-arrival paths at t0."""
    N = pd.N
    new: dict[int, NDArray[np.int32]] = {}
    by_src: dict[int, list[int]] = {}
    for p in pairs:
        by_src.setdefault(int(p) // N, []).append(int(p))
    for i, plist in by_src.items():
        arr, pe = td_tree(g, fac_e, int(pd.nodes[i]), t0, slot_s, per_edge=True)
        for p in plist:
            j = p % N
            cur, seq = int(pd.nodes[j]), []
            while cur != int(pd.nodes[i]):
                e = int(pe[cur])
                seq.append(e)
                cur = int(g.edge_from[e])
            new[p] = np.asarray(seq[::-1], dtype=np.int32)
    chunks, ptr = [], np.zeros(N * N + 1, dtype=np.int64)
    for q in range(N * N):
        seg = new[q] if q in new else pd.path_edges[pd.path_ptr[q] : pd.path_ptr[q + 1]]
        chunks.append(seg)
        ptr[q + 1] = ptr[q] + len(seg)
    edges = np.concatenate(chunks) if chunks else np.empty(0, dtype=np.int32)
    pair_of = np.repeat(np.arange(N * N, dtype=np.int32), np.diff(ptr))
    order = np.argsort(edges, kind="stable")
    cnt = np.bincount(edges, minlength=g.n_edges)
    inv_ptr = np.zeros(g.n_edges + 1, dtype=np.int64)
    inv_ptr[1:] = np.cumsum(cnt)
    return PairData(pd.nodes, ptr, edges.astype(np.int32), inv_ptr, pair_of[order])
