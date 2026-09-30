from __future__ import annotations

import itertools

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from taqpso.config import load_config
from taqpso.core.evaluate import route_cost
from taqpso.core.objective import Objective
from taqpso.solver.split import split
from taqpso.solver.split_fleet import split_fleet
from tests.conftest import make_instance


def brute(inst, g, cw, K=None):
    n = len(g)
    tb = inst.tables
    best = np.inf
    for mask in itertools.product([0, 1], repeat=n - 1):
        cuts = [0] + [i + 1 for i, b in enumerate(mask) if b]
        if K is not None and len(cuts) > K:
            continue
        bounds = cuts + [n]
        tot = 0.0
        ok = True
        for a, b in zip(bounds[:-1], bounds[1:], strict=True):
            seg = np.asarray(g[a:b], dtype=np.int32)
            if inst.demand[seg].sum() > inst.Q:
                ok = False
                break
            tot += route_cost(
                seg, len(seg), tb.tau, tb.dist, tb.cong, inst.sv, inst.depart_s, tb.slot_s, cw
            )
        if ok:
            best = min(best, tot)
    return best


@given(st.integers(2, 8), st.integers(0, 10_000), st.sampled_from([1, 6]))
@settings(max_examples=40, deadline=None)
def test_split_matches_brute_force(n, seed, slots):
    inst = make_instance(n, seed, Q=15, slots=slots)
    cw = Objective.from_instance(inst, load_config()).cw
    g = (np.random.default_rng(seed).permutation(n) + 1).astype(np.int32)
    cuts, cost = split(g, inst, cw)
    assert abs(cost - brute(inst, g, cw)) < 1e-9
    assert cuts[0] == 0


@given(st.integers(3, 8), st.integers(0, 10_000), st.integers(2, 4))
@settings(max_examples=40, deadline=None)
def test_split_fixed_k_matches_brute_force(n, seed, K):
    inst = make_instance(n, seed, Q=25, K=K)
    cw = Objective.from_instance(inst, load_config()).cw
    g = (np.random.default_rng(seed).permutation(n) + 1).astype(np.int32)
    ref = brute(inst, g, cw, K)
    cuts, cost, excess = split_fleet(g, inst, cw, K)
    if np.isfinite(ref):
        assert excess == 0 and abs(cost - ref) < 1e-9 and len(cuts) <= K
    else:
        assert excess > 0
