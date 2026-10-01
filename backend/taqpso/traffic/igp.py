"""Ichoua-Gendreau-Potvin propagation: stepwise-constant edge speeds, FIFO by construction."""

from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def edge_time_c(length, v0, fac, t_enter, slot_s, thr):  # type: ignore[no-untyped-def]
    """Return (travel seconds, seconds driven where fac < thr) for one edge entered at t_enter.

    fac: per-slot speed factors (speed = v0 * fac[slot]). Distance is consumed slot by slot, so
    the arrival function is non-decreasing (FIFO) by construction.
    """
    S = fac.shape[0]
    horizon = S * slot_s
    rem = length
    t = t_enter
    cong = 0.0
    while rem > 1e-9:
        tw = t - horizon * np.floor(t / horizon)
        k = int(tw / slot_s)
        if k >= S:
            k = S - 1
        to_end = (k + 1) * slot_s - tw
        v = v0 * fac[k]
        d = v * to_end
        if d >= rem:
            dt = rem / v
            rem = 0.0
        else:
            dt = to_end
            rem -= d
        if fac[k] < thr:
            cong += dt
        t += dt
    return t - t_enter, cong


@njit(cache=True)
def edge_time(length, v0, fac, t_enter, slot_s):  # type: ignore[no-untyped-def]
    dt, _ = edge_time_c(length, v0, fac, t_enter, slot_s, 0.0)
    return dt


@njit(cache=True)
def path_time(edges, length, v0, cls_fac, road_class, t0, slot_s, thr):  # type: ignore[no-untyped-def]
    """Chain edges. cls_fac: (n_classes, S) factors or (E, S) per-edge when road_class is empty.

    Returns (T, D, C).
    """
    t = t0
    D = 0.0
    C = 0.0
    for q in range(edges.shape[0]):
        e = edges[q]
        row = cls_fac[road_class[e]] if road_class.shape[0] > 0 else cls_fac[e]
        dt, c = edge_time_c(length[e], v0[e], row, t, slot_s, thr)
        t += dt
        C += c
        D += length[e]
    return t - t0, D, C
