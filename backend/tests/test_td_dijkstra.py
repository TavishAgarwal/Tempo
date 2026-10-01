from __future__ import annotations

import numpy as np
import pytest

from taqpso.paths.td_dijkstra import td_shortest_path
from taqpso.traffic.incidents import Incident, apply_incidents
from tests.test_traffic import grid_graph


def test_equals_static_dijkstra_at_free_flow():
    from scipy.sparse.csgraph import dijkstra

    from taqpso.traffic.pair_tables import csgraph_matrix

    g = grid_graph(6, 6)
    rng = np.random.default_rng(0)
    g.length_m[:] = rng.uniform(100, 400, g.n_edges)
    m, _ = csgraph_matrix(g, g.freeflow_time())
    ref = dijkstra(m, indices=0)
    fac = np.ones((1, 96))
    for dst in (5, 17, 35):
        p = td_shortest_path(g, fac, 0, dst, 1234.0)
        assert p.travel_s == pytest.approx(ref[dst], rel=1e-9)


def test_td_path_avoids_incident():
    g = grid_graph(5, 5)
    fac = np.ones((1, 96))
    base = td_shortest_path(g, fac, 0, 24, 0.0)
    inc = Incident(tuple(int(e) for e in base.edges), 0.1, 0.0, 3600.0)
    fe = apply_incidents(g, fac, [inc], 900.0)
    p = td_shortest_path(g, fe, 0, 24, 0.0, per_edge=True)
    assert set(p.edges.tolist()) != set(base.edges.tolist())
    assert p.travel_s <= base.travel_s * 10  # detour beats crawling along the blocked path
