from __future__ import annotations

import numpy as np

from taqpso.config import load_config
from taqpso.solver.optimizers import get_optimizer


def test_qpso_keys_stay_bounded_and_finite():
    cfg = load_config({"swarm": {"size": 6}})
    opt = get_optimizer("qpso", cfg)
    rng = np.random.default_rng(0)
    n = 20
    sw = opt.init(n, rng, [])
    cases = [
        lambda s: (s.pbest.__setitem__(slice(None), s.gbest), None)[1],  # pbest = gbest
        lambda s: s.x.__setitem__(slice(None), 0.0),  # x at lower bound
        lambda s: s.x.__setitem__(slice(None), 1.0),  # x at upper bound
    ]
    for prep in cases:
        prep(sw)
        for k in range(200):
            sw.x = opt.step(sw, k / 200, rng)
            assert np.isfinite(sw.x).all() and sw.x.min() >= 0.0 and sw.x.max() <= 1.0


def test_u_floor_prevents_inf(monkeypatch):
    cfg = load_config({"swarm": {"size": 4}})
    opt = get_optimizer("qpso", cfg)
    rng = np.random.default_rng(1)
    sw = opt.init(10, rng, [])

    class Zero:
        def random(self, shape):
            return np.zeros(shape)

        def integers(self, *a, **k):
            return 0

    x = opt.step(sw, 0.5, Zero())  # u -> 0 everywhere
    assert np.isfinite(x).all()


def test_rank_space_decodes_to_the_same_tour():
    from taqpso.solver.keys import decode_order
    from taqpso.solver.optimizers.qpso import to_ranks

    x = np.random.default_rng(2).random((5, 30))
    r = to_ranks(x)
    assert r.min() == 0.0 and r.max() == 1.0
    for a, b in zip(x, r, strict=True):
        assert (decode_order(a) == decode_order(b)).all()


def test_new_update_modes_bounded_and_local():
    from taqpso.solver.keys import decode_order

    for att in ("dimension", "particle"):
        for space in ("key", "rank"):
            cfg = load_config(
                {
                    "swarm": {"size": 6, "alpha_start": 0.02, "alpha_end": 0.005},
                    "qpso": {"attractor": att, "space": space},
                }
            )
            opt = get_optimizer("qpso", cfg)
            rng = np.random.default_rng(3)
            sw = opt.init(40, rng, [])
            sw.pbest[:] = sw.gbest  # converged swarm: a small alpha must keep the tour
            sw.x[:] = sw.gbest
            x = opt.step(sw, 0.5, rng)
            assert np.isfinite(x).all() and x.min() >= 0.0 and x.max() <= 1.0
            assert all((decode_order(r) == decode_order(sw.gbest)).all() for r in x)
