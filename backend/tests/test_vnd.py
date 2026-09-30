from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from taqpso.config import load_config
from taqpso.core.objective import Objective, evaluate_solution
from taqpso.core.solution import Solution
from taqpso.solver.seeds import nearest_neighbour
from taqpso.solver.split import max_route_len
from taqpso.solver.vnd import NB_CODES, cuts_to_array, improve_arrays
from tests.conftest import make_instance


def run_vnd(inst, g_tour, cuts, names, seed=0):
    cfg = load_config()
    obj = Objective.from_instance(inst, cfg)
    L = max_route_len(inst) + 1
    routes, lens = cuts_to_array(g_tour, cuts, L)
    before = Solution([[int(c) for c in routes[r, : lens[r]]] for r in range(len(lens))])
    order = (np.random.default_rng(seed).permutation(inst.n) + 1).astype(np.int32)
    total = improve_arrays(routes, lens, inst, obj.cw, order, 15, names, 50)
    after = Solution([[int(c) for c in routes[r, : lens[r]]] for r in range(len(lens))]).compact()
    return inst, obj, before, after, total


@pytest.mark.parametrize("nb", list(NB_CODES) + ["all"])
@given(st.integers(6, 40), st.integers(0, 5000), st.sampled_from([1, 8]))
@settings(max_examples=15, deadline=None)
def test_vnd_never_worsens_and_stays_feasible(nb, n, seed, slots):
    inst = make_instance(n, seed, Q=30, slots=slots)
    names = list(NB_CODES) if nb == "all" else [nb]
    nn = nearest_neighbour(inst)
    tour = nn.giant_tour()
    cuts, acc = [], 0
    for r in nn.routes:
        cuts.append(acc)
        acc += len(r)
    _, obj, before, after, total = run_vnd(
        inst, tour, np.asarray(cuts, dtype=np.int32), names, seed
    )
    after.validate(inst)
    jb = evaluate_solution(inst, before, obj).J
    ja = evaluate_solution(inst, after, obj).J
    assert ja <= jb + 1e-9
    assert abs(ja - total) < 1e-6  # cached suffix evaluation agrees with full re-evaluation


def test_vnd_improves_random_tour():
    inst = make_instance(30, 5, Q=40)
    g = (np.random.default_rng(0).permutation(inst.n) + 1).astype(np.int32)
    from taqpso.solver.split import split

    obj = Objective.from_instance(inst, load_config())
    cuts, c0 = split(g, inst, obj.cw)
    _, _, _, _, total = run_vnd(inst, g, cuts, list(NB_CODES))
    assert total < c0
