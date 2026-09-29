from __future__ import annotations

import numpy as np
import pytest

from taqpso.core.instance import Instance, TravelTables


def make_instance(
    n: int, seed: int = 0, Q: int = 20, K: int | None = None, slots: int = 1, dmax: int = 9
) -> Instance:
    rng = np.random.default_rng(seed)
    xy = rng.random((n + 1, 2)) * 100
    d = np.rint(np.linalg.norm(xy[:, None] - xy[None], axis=2))
    if slots == 1:
        tb = TravelTables.static(d)
    else:  # time-dependent but FIFO-safe: smooth multiplicative factor per slot
        fac = 1.0 + 0.4 * np.sin(np.linspace(0, 2 * np.pi, slots, endpoint=False))
        tau = (d[:, :, None] * fac[None, None, :]).astype(np.float32)
        cong = np.where(fac[None, None, :] > 1.2, tau, 0.0).astype(np.float32)
        tb = TravelTables(tau, d.astype(np.float32), cong, 900.0)
    dem = np.r_[0, rng.integers(1, dmax + 1, n)]
    svc = np.r_[0, rng.integers(0, 30, n)].astype(np.float32) if slots > 1 else None
    kw = {} if svc is None else {"service": svc}
    return Instance(f"rand{n}_{seed}", xy, dem, Q, tb, K=K, depart_s=0.0, **kw)  # type: ignore[arg-type]


@pytest.fixture
def small_inst() -> Instance:
    return make_instance(8, 3)
