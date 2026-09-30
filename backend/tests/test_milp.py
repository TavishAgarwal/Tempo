from __future__ import annotations

import itertools

import numpy as np

from taqpso.baselines.milp import solve_milp
from taqpso.config import load_config
from taqpso.solver.runner import solve
from tests.conftest import make_instance


def brute_opt(inst):
    n = inst.n
    d = inst.tables.tau[:, :, 0]
    best = np.inf
    for perm in itertools.permutations(range(1, n + 1)):
        for mask in itertools.product([0, 1], repeat=n - 1):
            segs, cur = [], [perm[0]]
            for c, b in zip(perm[1:], mask, strict=True):
                if b:
                    segs.append(cur)
                    cur = [c]
                else:
                    cur.append(c)
            segs.append(cur)
            if any(inst.demand[s].sum() > inst.Q for s in segs):
                continue
            tot = sum(
                d[0, s[0]] + sum(d[a, b] for a, b in zip(s[:-1], s[1:], strict=True)) + d[s[-1], 0]
                for s in segs
            )
            best = min(best, tot)
    return best


def test_milp_matches_brute_force_on_tiny():
    inst = make_instance(6, 11, Q=15)
    res = solve_milp(inst, 30)
    assert res.optimal and abs(res.objective - brute_opt(inst)) < 1e-6
    res.solution.validate(inst)


def test_taqpso_reaches_optimum_tiny():
    inst = make_instance(8, 3, Q=18)
    opt = solve_milp(inst, 60).objective
    r = solve(inst, load_config({"swarm": {"size": 6}}), "qpso", 0, budget_s=2)
    assert r.metrics.T >= opt - 1e-6 and r.metrics.T <= opt * 1.05
