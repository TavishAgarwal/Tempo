"""Road graph as CSR arrays (edges sorted by origin node)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


@dataclass
class Graph:
    node_xy: NDArray[np.float64]  # (V,2) lon, lat
    edge_from: NDArray[np.int32]
    edge_to: NDArray[np.int32]
    length_m: NDArray[np.float64]
    freeflow_mps: NDArray[np.float64]
    road_class: NDArray[np.int8]
    indptr: NDArray[np.int32]

    @property
    def n_nodes(self) -> int:
        return int(self.node_xy.shape[0])

    @property
    def n_edges(self) -> int:
        return int(self.edge_to.shape[0])

    @staticmethod
    def from_arrays(node_xy, edge_from, edge_to, length_m, freeflow_mps, road_class) -> Graph:  # type: ignore[no-untyped-def]
        order = np.argsort(edge_from, kind="stable")
        ef = np.asarray(edge_from, dtype=np.int32)[order]
        indptr = np.searchsorted(ef, np.arange(len(node_xy) + 1)).astype(np.int32)
        return Graph(
            np.asarray(node_xy, dtype=np.float64),
            ef,
            np.asarray(edge_to, dtype=np.int32)[order],
            np.asarray(length_m, dtype=np.float64)[order],
            np.asarray(freeflow_mps, dtype=np.float64)[order],
            np.asarray(road_class, dtype=np.int8)[order],
            indptr,
        )

    @staticmethod
    def load(path: Path) -> Graph:
        z = np.load(path)
        return Graph.from_arrays(
            z["node_xy"],
            z["edge_from"],
            z["edge_to"],
            z["length_m"],
            z["freeflow_mps"],
            z["road_class"],
        )

    def freeflow_time(self) -> NDArray[np.float64]:
        return self.length_m / self.freeflow_mps
