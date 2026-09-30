"""Random-key utilities: decode (sort), reflect+clip, write-back. No transcendental calls here."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]
I32 = NDArray[np.int32]

# spacing used to make written-back keys strictly increasing (decode is then unambiguous)
_TIE_EPS = 1e-12


def decode_order(keys: F64) -> I32:
    """Keys in [0,1]^n -> giant tour of customer ids 1..n (stable tie-break by index)."""
    return (np.argsort(keys, kind="stable") + 1).astype(np.int32)


def reflect_clip(x: F64) -> F64:
    """Reflect values into [0,1] (fold at the borders), then clip as a safety net."""
    y = np.abs(x)
    y = np.mod(y, 2.0)
    y = np.where(y > 1.0, 2.0 - y, y)
    return np.clip(y, 0.0, 1.0)


def write_back(keys: F64, tour: I32) -> F64:
    """Reassign the particle's own sorted key values so that decode_order == tour exactly."""
    n = len(tour)
    vals = np.sort(keys)
    vals = (vals + np.arange(n) * _TIE_EPS) / (1.0 + n * _TIE_EPS)  # strictly increasing, <= 1
    out = np.empty(n, dtype=np.float64)
    out[tour - 1] = vals
    return out
