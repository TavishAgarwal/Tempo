"""Time-dependent route propagation (Numba). Static mode = one constant slot."""

from __future__ import annotations

import numpy as np
from numba import njit
from numpy.typing import NDArray

from taqpso.core.instance import Instance


@njit(cache=True, inline="always")
def lookup(tab: NDArray[np.float32], i: int, j: int, t: float, slot_s: float) -> float:
    """Linear interpolation between slot-start samples; wraps modulo the horizon."""
    S = tab.shape[2]
    if S == 1:
        return float(tab[i, j, 0])
    horizon = S * slot_s
    tt = t - horizon * np.floor(t / horizon)
    x = tt / slot_s
    k = int(x)
    if k >= S:
        k = S - 1
    f = x - k
    k2 = k + 1
    if k2 == S:
        k2 = 0
    return float(tab[i, j, k]) * (1.0 - f) + float(tab[i, j, k2]) * f


@njit(cache=True, inline="always")
def tw_arrival(arr, c, svc):  # type: ignore[no-untyped-def]
    """Time window of customer c applied to arrival `arr`: (service start, wait, within due)."""
    ready = svc[c, 1]
    s = ready if arr < ready else arr
    return s, s - arr, s <= svc[c, 2]


@njit(cache=True)
def route_pass(route, rlen, start, t0, tau, dist, cong, svc, slot_s):  # type: ignore[no-untyped-def]
    """Forward pass of one route from node `start` at time t0.

    Returns (T_drive, D, C, W, F): driving time, distance, congestion seconds, total waiting W and
    the forward slack F = min_k(W_k + due_k - s_k), where W_k is the waiting accumulated up to and
    including customer k. Delaying the depot departure by d <= min(W, F) removes d of waiting and
    keeps every due time (Savelsbergh), so the unavoidable waiting is W - min(W, F). F < 0 marks a
    due-time violation. Without time windows W = 0.
    """
    t = t0
    prev = start
    Td = 0.0
    D = 0.0
    C = 0.0
    W = 0.0
    F = 1e18
    for k in range(rlen):
        c = route[k]
        tt = lookup(tau, prev, c, t, slot_s)
        Td += tt
        D += dist[prev, c]
        C += lookup(cong, prev, c, t, slot_s)
        s, w, ok = tw_arrival(t + tt, c, svc)
        if not ok:
            return Td, D, C, W, -1.0
        W += w
        slack = W + svc[c, 2] - s
        if slack < F:
            F = slack
        t = s + svc[c, 0]
        prev = c
    tt = lookup(tau, prev, 0, t, slot_s)
    Td += tt
    D += dist[prev, 0]
    C += lookup(cong, prev, 0, t, slot_s)
    return Td, D, C, W, F


@njit(cache=True)
def route_components(route, rlen, tau, dist, cong, svc, depart, slot_s):  # type: ignore[no-untyped-def]
    """Return (T, D, C) of one depot route departing at `depart` (empty route = 0).

    `svc` is the (N,3) kernel view [service, ready, due]. T = driving + unavoidable waiting;
    a violated due time returns T = 1e12 (infeasible marker).
    """
    if rlen == 0:
        return 0.0, 0.0, 0.0
    Td, D, C, W, F = route_pass(route, rlen, 0, depart, tau, dist, cong, svc, slot_s)
    if F < 0.0:
        return 1e12, D, C
    return Td + W - min(W, F), D, C


@njit(cache=True)
def route_cost(route, rlen, tau, dist, cong, svc, depart, slot_s, cw):  # type: ignore[no-untyped-def]
    T, D, C = route_components(route, rlen, tau, dist, cong, svc, depart, slot_s)
    return cw[0] * T + cw[1] * D + cw[2] * C


def route_times(
    inst: Instance, route: list[int], depart: float | None = None
) -> NDArray[np.float64]:
    """Arrival time at each customer then back at depot (python helper, for reporting/tests)."""
    from taqpso.core.evaluate import lookup as _lk  # noqa: F401  (jit fn usable from python)

    t = inst.depart_s if depart is None else depart
    tb = inst.tables
    out: list[float] = []
    prev = 0
    sv = inst.sv
    for c in [*route, 0]:
        t += _lk(tb.tau, prev, c, t, tb.slot_s)
        if c != 0 and t < sv[c, 1]:
            t = float(sv[c, 1])
        out.append(t)
        if c != 0:
            t += float(inst.service[c])
        prev = c
    return np.asarray(out)


def route_duration(inst: Instance, route: list[int]) -> float:
    """Duration = driving + unavoidable waiting + service; inf if infeasible.

    Waiting that a later depot departure can absorb is free (see `route_pass`).
    """
    if not route:
        return 0.0
    arr = np.asarray(route, dtype=np.int32)
    tb = inst.tables
    T, _, _ = route_components(
        arr, len(arr), tb.tau, tb.dist, tb.cong, inst.sv, inst.depart_s, tb.slot_s
    )
    if T >= 1e12:
        return float("inf")
    return float(T + inst.service[arr].sum())
