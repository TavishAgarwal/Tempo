"""Pair paths (free-flow fastest), inverted index edge -> pairs, and tau/dist/cong tables."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numba import njit, prange  # noqa: F401
from numpy.typing import NDArray
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from taqpso.core.instance import TravelTables
from taqpso.graph.model import Graph
from taqpso.traffic.igp import path_time


@dataclass
class PairData:
    nodes: NDArray[np.int32]  # graph node of each instance node (depot first)
    path_ptr: NDArray[np.int64]  # (N*N+1)
    path_edges: NDArray[np.int32]
    inv_ptr: NDArray[np.int64]  # (E+1)
    inv_pairs: NDArray[np.int32]  # pair index i*N+j

    @property
    def N(self) -> int:
        return int(self.nodes.shape[0])

    def path(self, i: int, j: int) -> NDArray[np.int32]:
        p = i * self.N + j
        return self.path_edges[self.path_ptr[p] : self.path_ptr[p + 1]]

    def pairs_using(self, edge_ids: NDArray[np.int32]) -> NDArray[np.int32]:
        out = [self.inv_pairs[self.inv_ptr[e] : self.inv_ptr[e + 1]] for e in edge_ids]
        return np.unique(np.concatenate(out)) if out else np.empty(0, dtype=np.int32)


def snap_nodes(g: Graph, lonlat: NDArray[np.float64]) -> NDArray[np.int32]:
    lat0 = np.deg2rad(g.node_xy[:, 1].mean())
    scale = np.array([np.cos(lat0), 1.0])
    tree = cKDTree(g.node_xy * scale)
    _, idx = tree.query(lonlat * scale)
    return np.asarray(idx, dtype=np.int32)


def csgraph_matrix(g: Graph, w: NDArray[np.float64]) -> tuple[csr_matrix, NDArray[np.int64]]:
    """Dedupe parallel edges keeping the cheapest; return (matrix, kept edge ids sorted by key)."""
    V = g.n_nodes
    key = g.edge_from.astype(np.int64) * V + g.edge_to
    order = np.lexsort((w, key))
    key_s = key[order]
    first = np.r_[True, key_s[1:] != key_s[:-1]]
    keep = order[first]
    m = csr_matrix((w[keep], (g.edge_from[keep], g.edge_to[keep])), shape=(V, V))
    return m, keep


def build_pair_paths(g: Graph, nodes: NDArray[np.int32]) -> PairData:
    N = len(nodes)
    w = g.freeflow_time()
    m, keep = csgraph_matrix(g, w)
    V = g.n_nodes
    key_keep = g.edge_from[keep].astype(np.int64) * V + g.edge_to[keep]
    srt = np.argsort(key_keep)
    key_sorted = key_keep[srt]
    eid_sorted = keep[srt]
    _, pred = dijkstra(m, directed=True, indices=nodes, return_predecessors=True)
    ptr = np.zeros(N * N + 1, dtype=np.int64)
    chunks: list[NDArray[np.int32]] = []
    for i in range(N):
        pr = pred[i]
        for j in range(N):
            seq: list[int] = []
            cur = int(nodes[j])
            src = int(nodes[i])
            while cur != src:
                p = int(pr[cur])
                if p < 0:
                    raise ValueError(f"node {j} unreachable from {i}")
                seq.append(p * V + cur)
                cur = p
            seq.reverse()
            if seq:
                k = np.asarray(seq, dtype=np.int64)
                chunks.append(eid_sorted[np.searchsorted(key_sorted, k)].astype(np.int32))
            ptr[i * N + j + 1] = ptr[i * N + j] + len(seq)
    edges = np.concatenate(chunks) if chunks else np.empty(0, dtype=np.int32)
    # inverted index
    pair_of = np.repeat(np.arange(N * N, dtype=np.int32), np.diff(ptr))
    order = np.argsort(edges, kind="stable")
    cnt = np.bincount(edges, minlength=g.n_edges)
    inv_ptr = np.zeros(g.n_edges + 1, dtype=np.int64)
    inv_ptr[1:] = np.cumsum(cnt)
    return PairData(nodes, ptr, edges, inv_ptr, pair_of[order])


@njit(cache=True)
def _fill(ptr, edges, length, v0, fac, road_class, N, S, slot_s, thr, rows, tau, cong, dist):  # type: ignore[no-untyped-def]
    for r in range(rows.shape[0]):
        p = rows[r]
        e = edges[ptr[p] : ptr[p + 1]]
        i = p // N
        j = p % N
        for k in range(S):
            T, D, C = path_time(e, length, v0, fac, road_class, k * slot_s, slot_s, thr)
            tau[i, j, k] = T
            cong[i, j, k] = C
        T, D, C = path_time(e, length, v0, fac, road_class, 0.0, slot_s, thr)
        dist[i, j] = D


def build_tables(
    g: Graph,
    pd: PairData,
    fac: NDArray[np.float64],
    slot_s: float,
    thr: float,
    per_edge: bool = False,
    tables: TravelTables | None = None,
    pairs: NDArray[np.int32] | None = None,
) -> TravelTables:
    """tau/cong/dist tables from IGP propagation along the stored pair paths.

    fac: (n_classes, S) or, when per_edge, (E, S). If `tables` and `pairs` are given only those
    pair rows are recomputed (incident re-pathing).
    """
    N = pd.N
    S = fac.shape[1]
    if tables is None:
        tau = np.zeros((N, N, S), dtype=np.float32)
        cong = np.zeros((N, N, S), dtype=np.float32)
        dist = np.zeros((N, N), dtype=np.float32)
    else:
        tau, cong, dist = tables.tau.copy(), tables.cong.copy(), tables.dist.copy()
    need = g.n_edges if per_edge else int(g.road_class.max()) + 1
    if fac.shape[0] < need:
        raise ValueError(f"factor table has {fac.shape[0]} rows, need {need}")
    rows = np.arange(N * N, dtype=np.int64) if pairs is None else pairs.astype(np.int64)
    rc = np.empty(0, dtype=np.int8) if per_edge else g.road_class
    _fill(
        pd.path_ptr,
        pd.path_edges,
        g.length_m,
        g.freeflow_mps,
        np.ascontiguousarray(fac),
        rc,
        N,
        S,
        slot_s,
        thr,
        rows,
        tau,
        cong,
        dist,
    )
    return TravelTables(tau, dist, cong, slot_s)
