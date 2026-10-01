"""FIFO check: tau(t+dt) - tau(t) >= -dt for every pair and adjacent breakpoints."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from taqpso.core.instance import TravelTables


class FifoViolation(RuntimeError):
    pass


def fifo_violations(tb: TravelTables, tol: float = 1e-2) -> NDArray[np.int64]:
    """Return array of (i, j, slot) where FIFO fails (including the wrap-around slot)."""
    S = tb.n_slots
    if S == 1:
        return np.empty((0, 3), dtype=np.int64)
    tau = tb.tau.astype(np.float64)
    nxt = np.roll(tau, -1, axis=2)
    horizon_wrap = np.zeros(S)
    horizon_wrap[-1] = 0.0  # tau is periodic, so wrap uses the same dt = slot_s
    diff = nxt - tau
    bad = diff < -tb.slot_s - tol
    return np.argwhere(bad)


def check_fifo(tb: TravelTables, tol: float = 1e-2) -> None:
    v = fifo_violations(tb, tol)
    if len(v):
        i, j, k = v[0]
        raise FifoViolation(f"FIFO violated on {len(v)} samples, first at pair ({i},{j}) slot {k}")
