from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from taqpso.solver.keys import decode_order, reflect_clip, write_back


@given(st.integers(2, 60), st.integers(0, 10_000))
@settings(max_examples=60, deadline=None)
def test_write_back_roundtrip(n, seed):
    rng = np.random.default_rng(seed)
    keys = rng.random(n)
    if n > 3:
        keys[1] = keys[2]  # force a tie
    tour = (rng.permutation(n) + 1).astype(np.int32)
    out = write_back(keys, tour)
    assert (decode_order(out) == tour).all()
    assert out.min() >= 0 and out.max() <= 1


def test_reflect_clip_range():
    x = np.array([-3.7, -0.2, 0.0, 0.5, 1.0, 1.3, 5.9, 1e9, -1e9])
    y = reflect_clip(x)
    assert (y >= 0).all() and (y <= 1).all() and np.isfinite(y).all()
    assert abs(y[1] - 0.2) < 1e-12 and abs(y[5] - 0.7) < 1e-12
