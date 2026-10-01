from __future__ import annotations

import numpy as np
import pytest

from taqpso.config import load_config
from taqpso.core.instance import Instance, TravelTables
from taqpso.core.objective import Objective, evaluate_solution
from taqpso.graph.model import Graph
from taqpso.sim.simulator import Network, simulate
from taqpso.solver.runner import solve
from taqpso.traffic.fifo_check import FifoViolation, check_fifo
from taqpso.traffic.igp import edge_time, edge_time_c
from taqpso.traffic.pair_tables import build_pair_paths, build_tables


def test_igp_constant_speed():
    fac = np.ones(96)
    assert edge_time(1000.0, 10.0, fac, 123.0, 900.0) == pytest.approx(100.0)


def test_igp_crosses_slot_boundary_hand_computed():
    fac = np.ones(96)
    fac[1] = 0.5  # second slot at half speed (5 m/s)
    # enter 10 s before boundary at 10 m/s -> 100 m, remaining 400 m at 5 m/s = 80 s
    dt, cong = edge_time_c(500.0, 10.0, fac, 890.0, 900.0, 0.6)
    assert dt == pytest.approx(10.0 + 80.0)
    assert cong == pytest.approx(80.0)


def test_igp_is_fifo_with_speed_drop():
    fac = np.ones(96)
    fac[10:14] = 0.2
    ts = np.linspace(0, 86400, 3000)
    arr = np.array([t + edge_time(3000.0, 12.0, fac, t, 900.0) for t in ts])
    assert (np.diff(arr) >= -1e-9).all()


def test_fifo_check_fails_on_non_fifo_table():
    tau = np.ones((2, 2, 4), dtype=np.float32) * 10
    tau[0, 1, 1] = 2000.0  # arrival at slot 1 is far later than slot 2 departure
    tb = TravelTables(tau, np.ones((2, 2), dtype=np.float32), np.zeros_like(tau), 900.0)
    with pytest.raises(FifoViolation):
        check_fifo(tb)


def grid_graph(w=5, h=5, length=200.0, v=10.0):
    ids = lambda x, y: y * w + x  # noqa: E731
    fr, to = [], []
    for x in range(w):
        for y in range(h):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    fr.append(ids(x, y))
                    to.append(ids(nx, ny))
    E = len(fr)
    xy = np.array([[x, y] for y in range(h) for x in range(w)], dtype=float)
    return Graph.from_arrays(
        xy, fr, to, np.full(E, length), np.full(E, v), np.zeros(E, dtype=np.int8)
    )


def test_tables_fifo_and_simulator_agrees_at_constant_speed():
    g = grid_graph()
    nodes = np.array([12, 0, 4, 20, 24, 6, 18], dtype=np.int32)
    pd = build_pair_paths(g, nodes)
    fac = np.ones((1, 96))
    tb = build_tables(g, pd, fac, 900.0, 0.5)
    check_fifo(tb)
    n = len(nodes) - 1
    demand = np.r_[0, np.full(n, 2)].astype(np.int32)
    inst = Instance("grid", g.node_xy[nodes], demand, 6, tb, depart_s=3600.0)
    obj = Objective.from_instance(inst, load_config())
    r = solve(inst, load_config({"swarm": {"size": 4}}), "qpso", 0, max_iters=3)
    net = Network(g, pd, fac, 900.0, 0.5)
    m_sim = simulate(inst, net, r.solution, obj)
    m_tab = evaluate_solution(inst, r.solution, obj)
    assert m_sim.T == pytest.approx(m_tab.T, rel=1e-4)
    assert m_sim.D == pytest.approx(m_tab.D, rel=1e-4)


def test_td_tables_vs_simulator_gap_is_small_on_peak_profile():
    g = grid_graph()
    nodes = np.arange(0, 25, 3, dtype=np.int32)
    pd = build_pair_paths(g, nodes)
    S = 96
    fac = np.ones((1, S))
    fac[0, 68:80] = 0.4  # evening peak
    tb = build_tables(g, pd, fac, 900.0, 0.5)
    check_fifo(tb)
    n = len(nodes) - 1
    inst = Instance(
        "g2",
        g.node_xy[nodes],
        np.r_[0, np.full(n, 1)].astype(np.int32),
        4,
        tb,
        np.r_[0, np.full(n, 60.0)].astype(np.float32),
        depart_s=17.2 * 3600,
    )
    obj = Objective.from_instance(inst, load_config())
    r = solve(inst, load_config({"swarm": {"size": 4}}), "qpso", 0, max_iters=3)
    m_sim = simulate(inst, Network(g, pd, fac, 900.0, 0.5), r.solution, obj)
    m_tab = evaluate_solution(inst, r.solution, obj)
    assert abs(m_sim.T - m_tab.T) / m_sim.T < 0.05


def test_tomtom_parse_and_live_overlay(monkeypatch):
    from taqpso.bench import tomtom
    from taqpso.graph.builder import CLASS_NAMES
    from taqpso.graph.profiles import apply_live_ratios

    payload = {
        "flowSegmentData": {
            "frc": "FRC2",
            "currentSpeed": 15,
            "freeFlowSpeed": 30,
            "confidence": 0.9,
        }
    }
    s = tomtom.parse_flow(28.6, 77.2, payload)
    assert s.ratio == pytest.approx(0.5)
    ratios = tomtom.class_ratios([s])
    assert ratios["primary"] == pytest.approx(0.5)
    base = np.ones((len(CLASS_NAMES), 96))
    out = apply_live_ratios(base, ratios, now_slot=70)
    assert out[CLASS_NAMES.index("primary"), 70] == pytest.approx(0.5)
    assert out[:, 0].min() == 1.0 and (base == 1.0).all()
    monkeypatch.delenv("TOMTOM_API_KEY", raising=False)
    with pytest.raises(tomtom.TomTomError):
        tomtom.api_key()


def test_hourly_profile_is_constant_within_each_hour():
    from taqpso.graph.profiles import _hourly_profile

    hr = [1.0] * 24
    hr[18] = 0.5
    p = _hourly_profile(hr, 96)
    assert p.shape == (96,)
    assert (p[72:76] == 0.5).all() and p[71] == 1.0 and p[76] == 1.0
    assert _hourly_profile(hr, 48)[36] == 0.5  # other slot widths work too
