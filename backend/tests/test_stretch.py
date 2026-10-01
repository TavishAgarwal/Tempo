from __future__ import annotations

import numpy as np
import pytest

from taqpso.config import load_config, load_emission_params
from taqpso.core.evaluate import route_duration
from taqpso.core.instance import Instance, TravelTables
from taqpso.solver.runner import solve
from taqpso.traffic.emissions import emission_factor
from tests.conftest import make_instance


def _tw_instance(n=8, seed=3):
    base = make_instance(n, seed, Q=20)
    rng = np.random.default_rng(seed)
    N = n + 1
    ready = np.zeros(N)
    due = np.full(N, 1e5)
    ready[1:] = rng.uniform(0, 400, n)
    due[1:] = ready[1:] + rng.uniform(1500, 4000, n)
    return Instance(
        base.name,
        base.coords,
        base.demand,
        base.Q,
        base.tables,
        base.service,
        depart_s=0.0,
        tw=np.stack([ready, due], axis=1),
    )


def test_waiting_absorbed_by_later_departure():
    tau = np.full((3, 3), 10.0)
    np.fill_diagonal(tau, 0)
    tb = TravelTables.static(tau)
    tw = np.array([[0, 1e9], [100, 1e9], [500, 1e9]])
    inst = Instance(
        "w",
        np.zeros((3, 2)),
        np.array([0, 1, 1], dtype=np.int32),
        5,
        tb,
        np.zeros(3, dtype=np.float32),
        tw=tw,
    )
    # leaving the depot at t=480 hits both ready times: no waiting, duration = 3 x 10 s
    assert route_duration(inst, [1, 2]) == pytest.approx(30.0)


def test_waiting_limited_by_due_slack():
    tau = np.full((3, 3), 10.0)
    np.fill_diagonal(tau, 0)
    tb = TravelTables.static(tau)
    tw = np.array([[0, 1e9], [0, 20], [500, 520]])
    inst = Instance(
        "w",
        np.zeros((3, 2)),
        np.array([0, 1, 1], dtype=np.int32),
        5,
        tb,
        np.zeros(3, dtype=np.float32),
        tw=tw,
    )
    # customer 1 can be reached at most 10 s late (due 20), so only 10 of the 480 s wait vanish
    assert route_duration(inst, [1, 2]) == pytest.approx(30.0 + 470.0)


def test_due_violation_marks_infeasible():
    tau = np.full((3, 3), 100.0)
    tb = TravelTables.static(tau)
    tw = np.array([[0, 1e9], [0, 50], [0, 1e9]])
    inst = Instance(
        "w",
        np.zeros((3, 2)),
        np.array([0, 1, 1], dtype=np.int32),
        5,
        tb,
        np.zeros(3, dtype=np.float32),
        tw=tw,
    )
    assert route_duration(inst, [1]) == float("inf")


def test_solver_returns_tw_feasible_solution():
    inst = _tw_instance()
    r = solve(inst, load_config(), "qpso", 0, max_iters=15)
    r.solution.validate(inst)
    assert all(np.isfinite(route_duration(inst, rt)) for rt in r.solution.routes if rt)


def test_no_tw_view_never_binds():
    inst = make_instance(5, 1, Q=20)
    assert not inst.has_tw
    assert (inst.sv[:, 1] == 0).all() and (inst.sv[:, 2] >= 1e17).all()


def test_emission_factor_u_shape():
    p = load_emission_params()
    slow, mid, fast = (emission_factor(v, p) for v in (10.0, 60.0, 110.0))
    assert mid < slow and mid < fast
