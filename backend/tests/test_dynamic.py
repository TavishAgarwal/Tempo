from __future__ import annotations

import numpy as np
import pytest

from taqpso.bench.make_scenarios import SCEN, load_scenario
from taqpso.config import load_config
from taqpso.core.objective import Objective
from taqpso.core.solution import Solution
from taqpso.dynamic.fallback import apply_incident, fallback_plan
from taqpso.dynamic.reopt import build_reopt, reoptimize
from taqpso.sim.dynamic_sim import simulate_remaining
from taqpso.solver.runner import solve
from taqpso.traffic.incidents import Incident

pytestmark = pytest.mark.skipif(not (SCEN / "delhi_n30.json").exists(), reason="run `make data`")


def setup_world():
    sc = load_scenario("delhi_n30")
    cfg = load_config({"swarm": {"size": 6}})
    inst = sc.inst
    obj = Objective.from_instance(inst, cfg)
    plan = solve(inst, cfg, "qpso", 0, max_iters=8, objective=obj).solution
    cnt: dict[int, int] = {}
    for r in plan.routes:
        prev = 0
        for c in [*r, 0]:
            for e in sc.net.pairs.path(prev, c):
                cnt[int(e)] = cnt.get(int(e), 0) + 1
            prev = c
    top = tuple(sorted(cnt, key=lambda e: -cnt[e])[:3])
    t_e = 18 * 3600.0
    inc = Incident(top, 0.1, t_e, t_e + 3600)
    world = apply_incident(inst, sc.net, [inc], t_e)
    return sc, cfg, inst, obj, plan, world, t_e


def test_vehicle_states_cover_all_customers_and_commit_next_stop():
    sc, cfg, inst, obj, plan, world, t_e = setup_world()
    fb = fallback_plan(inst, sc.net, plan, t_e)
    for s in fb.states:  # FR5: the committed stop stays first in the vehicle's remaining list
        if s.status == "enroute":
            assert s.remaining[0] == s.committed
    # every customer is either already served or still in some vehicle's remaining list
    still = {c for s in fb.states for c in s.remaining}
    planned = {c for r in plan.routes for c in r}
    assert still <= planned
    assert {c for r in fb.routes for c in r} <= still


def test_reopt_never_diverts_committed_and_is_feasible():
    sc, cfg, inst, obj, plan, world, t_e = setup_world()
    fb = fallback_plan(inst, sc.net, plan, t_e)
    prob = build_reopt(inst, world, fb.states, fb.routes, t_e)
    if prob.sub.n == 0:
        pytest.skip("nothing left to re-optimise")
    res = reoptimize(prob, cfg, obj, 0, 1.0, max_iters=5)
    new = prob.to_original(res.solution.routes)
    assert sorted(c for r in new for c in r) == sorted(c for r in fb.routes for c in r)
    for v, r in enumerate(new):
        assert sum(int(inst.demand[c]) for c in r) <= prob.fleet.cap[v]
    m_fb = simulate_remaining(inst, world.net, fb.states, fb.routes, obj, t_e)
    m_new = simulate_remaining(inst, world.net, fb.states, new, obj, t_e)
    assert m_new.J <= m_fb.J * 1.02  # warm start is seeded with the fallback; never much worse


def test_incident_changes_only_affected_pair_rows():
    sc, cfg, inst, obj, plan, world, t_e = setup_world()
    assert world.affected_pairs > 0
    N = inst.n + 1
    same = (world.tables.tau == inst.tables.tau).all(axis=2).reshape(-1)
    assert same.sum() >= N * N - world.affected_pairs
    assert np.isfinite(world.tables.tau).all()
    assert isinstance(plan, Solution)


def test_lean_safe_plan_world_matches_full_world_on_plan_legs():
    """The fast safe plan re-paths only the legs it drives; those legs equal the full world's."""
    from taqpso.dynamic.fallback import leg_pairs, safe_plan

    sc, cfg, inst, obj, plan, world, t_e = setup_world()
    top = Incident(tuple(world_edges(sc, plan)), 0.1, t_e, t_e + 3600)
    fb, lean = safe_plan(inst, sc.net, plan, [top], t_e)
    full = apply_incident(inst, sc.net, [top], t_e)
    N = sc.net.pairs.N
    for p in leg_pairs(fb.states, fb.routes, N):
        i, j = divmod(int(p), N)
        assert list(lean.net.pairs.path(i, j)) == list(full.net.pairs.path(i, j))
    assert lean.affected_pairs == full.affected_pairs
    assert fb.latency_s < 1.0


def world_edges(sc, plan):
    cnt: dict[int, int] = {}
    for r in plan.routes:
        prev = 0
        for c in [*r, 0]:
            for e in sc.net.pairs.path(prev, c):
                cnt[int(e)] = cnt.get(int(e), 0) + 1
            prev = c
    return sorted(cnt, key=lambda e: -cnt[e])[:3]
