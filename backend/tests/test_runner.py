from __future__ import annotations

import numpy as np

from taqpso.config import load_config
from taqpso.solver.runner import solve
from tests.conftest import make_instance


def test_determinism_same_seed_same_result():
    inst = make_instance(25, 2, Q=30)
    cfg = load_config({"swarm": {"size": 4}})
    a = solve(inst, cfg, "qpso", 7, max_iters=5)
    b = solve(inst, cfg, "qpso", 7, max_iters=5)
    assert a.solution.routes == b.solution.routes and a.J == b.J


def test_all_optimizers_feasible_and_anytime():
    inst = make_instance(20, 4, Q=25, K=None)
    cfg = load_config({"swarm": {"size": 4}})
    for s in ["qpso", "pso", "ga", "random"]:
        seen = []
        r = solve(
            inst,
            cfg,
            s,
            1,
            max_iters=4,
            on_improvement=lambda t, J, sol, d, seen=seen: seen.append(J),
        )
        r.solution.validate(inst)
        assert r.feasible and seen and seen == sorted(seen, reverse=True)


def test_fixed_fleet_respected():
    inst = make_instance(20, 4, Q=40, K=None)
    from taqpso.solver.seeds import nearest_neighbour

    k = nearest_neighbour(inst).n_routes + 1
    inst.K = k
    r = solve(inst, load_config({"swarm": {"size": 4}}), "qpso", 1, max_iters=4)
    assert r.feasible and r.solution.n_routes <= k


def test_optimizers_only_implement_step():
    from taqpso.solver.optimizers import REGISTRY
    from taqpso.solver.optimizers.base import BaseOptimizer

    for cls in REGISTRY.values():
        own = {k for k in vars(cls) if not k.startswith("__")}
        assert own == {"step"}, (cls, own)
        assert issubclass(cls, BaseOptimizer)
    assert np  # keep numpy imported for clarity


def test_vnd_gate_runs_full_vnd_only_on_promising_particles():
    inst = make_instance(25, 2, Q=30)
    base = {"swarm": {"size": 4}}
    full = solve(inst, load_config(base), "qpso", 0, max_iters=5)
    assert full.full_vnd == full.evaluations  # no gate: every evaluation runs the full VND
    never = solve(
        inst, load_config(base, {"vnd": {"gate_tolerance": -1.0}}), "qpso", 0, max_iters=5
    )
    # first visit of each particle has no pbest yet, so it always gets the full VND
    assert never.full_vnd == 4 and never.evaluations == 20
    always = solve(
        inst, load_config(base, {"vnd": {"gate_tolerance": 1e9}}), "qpso", 0, max_iters=5
    )
    assert always.full_vnd == always.evaluations
    for r in (never, always):
        r.solution.validate(inst)
