from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException
from numpy.typing import NDArray

from taqpso.api.schemas import CongestionEdge, CongestionOut, PathOut
from taqpso.config import DATA_DIR
from taqpso.graph.model import Graph
from taqpso.graph.profiles import load_profiles
from taqpso.paths.td_dijkstra import Path, td_shortest_path
from taqpso.traffic.pair_tables import snap_nodes

router = APIRouter()
_cache: dict[str, object] = {}


def _world() -> tuple[Graph, NDArray[np.float64]]:
    if "g" not in _cache:
        _cache["g"] = Graph.load(DATA_DIR / "processed" / "graph.npz")
        _cache["fac"] = load_profiles(DATA_DIR / "processed" / "profiles.json")
    return _cache["g"], _cache["fac"]  # type: ignore[return-value]


@router.get("/paths", response_model=PathOut)
def fastest_path(
    from_lon: float, from_lat: float, to_lon: float, to_lat: float, depart: float
) -> PathOut:
    g, fac = _world()
    ids = snap_nodes(g, np.array([[from_lon, from_lat], [to_lon, to_lat]]))
    src, dst = int(ids[0]), int(ids[1])
    if src == dst:
        raise HTTPException(422, "Origin and destination snap to the same road node")
    td = td_shortest_path(g, fac, src, dst, depart)
    ff = td_shortest_path(g, np.ones_like(fac), src, dst, depart)
    # free-flow path evaluated under real traffic (what a static planner would drive)
    from taqpso.traffic.igp import path_time

    t_ff, _, _ = path_time(
        ff.edges, g.length_m, g.freeflow_mps, fac, g.road_class, depart, 900.0, 0.5
    )

    def pts(p: Path) -> list[list[float]]:
        return [[float(x), float(y)] for x, y in g.node_xy[p.nodes]]

    return PathOut(
        travel_s=td.travel_s,
        distance_m=td.distance_m,
        free_flow_travel_s=float(t_ff),
        geometry=pts(td),
        free_flow_geometry=pts(ff),
        depart_s=depart,
    )


@router.get("/congestion", response_model=CongestionOut)
def congestion(slot: int) -> CongestionOut:
    g, fac = _world()
    if not 0 <= slot < fac.shape[1]:
        raise HTTPException(422, "slot must be 0..95")
    ratio = fac[g.road_class, slot]
    edges = [
        CongestionEdge(
            a=(float(g.node_xy[a][0]), float(g.node_xy[a][1])),
            b=(float(g.node_xy[b][0]), float(g.node_xy[b][1])),
            ratio=float(r),
            road_class=int(c),
        )
        for a, b, r, c in zip(g.edge_from, g.edge_to, ratio, g.road_class, strict=True)
    ]
    return CongestionOut(slot=slot, label="Calibrated time-of-day profile (synthetic)", edges=edges)
