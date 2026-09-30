"""Variable neighbourhood descent (Numba): relocate, swap, 2-opt, 2-opt*, or-opt.

Granular candidate lists, first improvement, suffix re-evaluation (a modified route is
re-propagated only from its first changed position, using cached prefix state). A move is
accepted only if capacity holds and J strictly decreases, so J never worsens and feasibility
is never broken.
"""

from __future__ import annotations

import numpy as np
from numba import njit
from numpy.typing import NDArray

from taqpso.core.evaluate import lookup, route_pass, tw_arrival
from taqpso.core.fleet import Fleet
from taqpso.core.instance import Instance

NB_CODES = {"relocate": 0, "swap": 1, "two_opt": 2, "two_opt_star": 3, "or_opt": 4}
EPS = 1e-10


@njit(cache=True)
def _tw_cost(route, rlen, start, t0, tau, dist, cong, svc, slot_s, cw):  # type: ignore[no-untyped-def]
    """Whole-route cost under time windows (1e18 if a due time is violated)."""
    Td, D, C, W, F = route_pass(route, rlen, start, t0, tau, dist, cong, svc, slot_s)
    if F < 0.0:
        return 1e18
    return cw[0] * (Td + W - min(W, F)) + cw[1] * D + cw[2] * C


@njit(cache=True)
def _rebuild(
    r,
    routes,
    lens,
    loads,
    pos,
    rid,
    dep,
    cst,
    rc,
    demand,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
):  # type: ignore[no-untyped-def]
    L = lens[r]
    t = stime[r]
    acc = 0.0
    prev = snode[r]
    ld = 0
    dep[r, 0] = t
    cst[r, 0] = 0.0
    for k in range(L):
        c = routes[r, k]
        pos[c] = k
        rid[c] = r
        tt = lookup(tau, prev, c, t, slot_s)
        acc += cw[0] * tt + cw[1] * dist[prev, c] + cw[2] * lookup(cong, prev, c, t, slot_s)
        arr, w, ok = tw_arrival(t + tt, c, svc)
        acc += cw[0] * w
        t = arr + svc[c, 0]
        prev = c
        ld += demand[c]
        dep[r, k + 1] = t
        cst[r, k + 1] = acc
    loads[r] = ld
    rt = lookup(tau, prev, 0, t, slot_s)
    rc[r] = acc + cw[0] * rt + cw[1] * dist[prev, 0] + cw[2] * lookup(cong, prev, 0, t, slot_s)
    if svc[0, 1] > 0.5:  # time windows active: price the whole route with departure shifting
        rc[r] = _tw_cost(routes[r], L, snode[r], stime[r], tau, dist, cong, svc, slot_s, cw)


@njit(cache=True)
def _eval_buf(buf, blen, m, r_old, dep, cst, tau, dist, cong, svc, snode, stime, slot_s, cw):  # type: ignore[no-untyped-def]
    """Cost of `buf`, whose first m entries equal route r_old's first m (suffix re-evaluation)."""
    if svc[0, 1] > 0.5:  # time windows: departure shifting makes the cost non-suffix-local
        return _tw_cost(buf, blen, snode[r_old], stime[r_old], tau, dist, cong, svc, slot_s, cw)
    t = stime[r_old]
    acc = 0.0
    prev = snode[r_old]
    if m > 0:
        t = dep[r_old, m]
        acc = cst[r_old, m]
        prev = buf[m - 1]
    for k in range(m, blen):
        c = buf[k]
        tt = lookup(tau, prev, c, t, slot_s)
        acc += cw[0] * tt + cw[1] * dist[prev, c] + cw[2] * lookup(cong, prev, c, t, slot_s)
        arr, w, ok = tw_arrival(t + tt, c, svc)
        if not ok:
            return 1e18
        acc += cw[0] * w
        t = arr + svc[c, 0]
        prev = c
    rt = lookup(tau, prev, 0, t, slot_s)
    return acc + cw[0] * rt + cw[1] * dist[prev, 0] + cw[2] * lookup(cong, prev, 0, t, slot_s)


@njit(cache=True)
def _load(buf, blen, demand):  # type: ignore[no-untyped-def]
    s = 0
    for k in range(blen):
        s += demand[buf[k]]
    return s


@njit(cache=True)
def _commit(
    ra,
    bufA,
    la,
    rb,
    bufB,
    lb,
    routes,
    lens,
    loads,
    pos,
    rid,
    dep,
    cst,
    rc,
    demand,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
):  # type: ignore[no-untyped-def]
    for k in range(la):
        routes[ra, k] = bufA[k]
    lens[ra] = la
    _rebuild(
        ra,
        routes,
        lens,
        loads,
        pos,
        rid,
        dep,
        cst,
        rc,
        demand,
        tau,
        dist,
        cong,
        svc,
        snode,
        stime,
        slot_s,
        cw,
    )
    if rb >= 0:
        for k in range(lb):
            routes[rb, k] = bufB[k]
        lens[rb] = lb
        _rebuild(
            rb,
            routes,
            lens,
            loads,
            pos,
            rid,
            dep,
            cst,
            rc,
            demand,
            tau,
            dist,
            cong,
            svc,
            snode,
            stime,
            slot_s,
            cw,
        )


@njit(cache=True)
def _try(
    ra,
    la,
    mA,
    rb,
    lb,
    mB,
    bufA,
    bufB,
    cap,
    routes,
    lens,
    loads,
    pos,
    rid,
    dep,
    cst,
    rc,
    demand,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
):  # type: ignore[no-untyped-def]
    """Evaluate the (one or two) rebuilt routes; commit if feasible and strictly better."""
    if _load(bufA, la, demand) > cap[ra]:
        return False
    old = rc[ra]
    new = _eval_buf(bufA, la, mA, ra, dep, cst, tau, dist, cong, svc, snode, stime, slot_s, cw)
    if rb >= 0:
        if _load(bufB, lb, demand) > cap[rb]:
            return False
        old += rc[rb]
        new += _eval_buf(bufB, lb, mB, rb, dep, cst, tau, dist, cong, svc, snode, stime, slot_s, cw)
    if new < old - EPS:
        _commit(
            ra,
            bufA,
            la,
            rb,
            bufB,
            lb,
            routes,
            lens,
            loads,
            pos,
            rid,
            dep,
            cst,
            rc,
            demand,
            tau,
            dist,
            cong,
            svc,
            snode,
            stime,
            slot_s,
            cw,
        )
        return True
    return False


@njit(cache=True)
def _seg_move(
    u,
    s,
    rev,
    v,
    after,
    cap,
    bufA,
    bufB,
    routes,
    lens,
    loads,
    pos,
    rid,
    dep,
    cst,
    rc,
    demand,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
):  # type: ignore[no-untyped-def]
    """Move segment routes[ru, pu:pu+s] next to v (after/before), optionally reversed."""
    ru = rid[u]
    pu = pos[u]
    Lu = lens[ru]
    if pu + s > Lu:
        return False
    rv = rid[v]
    pv = pos[v]
    segload = 0
    for k in range(s):
        segload += demand[routes[ru, pu + k]]
    if rv == ru:
        if pv >= pu and pv < pu + s:
            return False
        pvr = pv if pv < pu else pv - s
        ins = pvr + 1 if after else pvr
        if ins == pu and rev == 0:
            return False
        # removed route into bufB scratch, then assemble in bufA
        n_rem = 0
        for k in range(Lu):
            if k < pu or k >= pu + s:
                bufB[n_rem] = routes[ru, k]
                n_rem += 1
        w = 0
        for k in range(ins):
            bufA[w] = bufB[k]
            w += 1
        for k in range(s):
            idx = pu + (s - 1 - k) if rev == 1 else pu + k
            bufA[w] = routes[ru, idx]
            w += 1
        for k in range(ins, n_rem):
            bufA[w] = bufB[k]
            w += 1
        m = pu if pu < ins else ins
        return _try(
            ru,
            w,
            m,
            -1,
            0,
            0,
            bufA,
            bufB,
            cap,
            routes,
            lens,
            loads,
            pos,
            rid,
            dep,
            cst,
            rc,
            demand,
            tau,
            dist,
            cong,
            svc,
            snode,
            stime,
            slot_s,
            cw,
        )
    if loads[rv] + segload > cap[rv]:
        return False
    la = 0
    for k in range(Lu):
        if k < pu or k >= pu + s:
            bufA[la] = routes[ru, k]
            la += 1
    ins = pv + 1 if after else pv
    Lv = lens[rv]
    lb = 0
    for k in range(ins):
        bufB[lb] = routes[rv, k]
        lb += 1
    for k in range(s):
        idx = pu + (s - 1 - k) if rev == 1 else pu + k
        bufB[lb] = routes[ru, idx]
        lb += 1
    for k in range(ins, Lv):
        bufB[lb] = routes[rv, k]
        lb += 1
    return _try(
        ru,
        la,
        pu,
        rv,
        lb,
        ins,
        bufA,
        bufB,
        cap,
        routes,
        lens,
        loads,
        pos,
        rid,
        dep,
        cst,
        rc,
        demand,
        tau,
        dist,
        cong,
        svc,
        snode,
        stime,
        slot_s,
        cw,
    )


@njit(cache=True)
def _swap(
    u,
    v,
    cap,
    bufA,
    bufB,
    routes,
    lens,
    loads,
    pos,
    rid,
    dep,
    cst,
    rc,
    demand,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
):  # type: ignore[no-untyped-def]
    ru = rid[u]
    rv = rid[v]
    pu = pos[u]
    pv = pos[v]
    if ru == rv:
        L = lens[ru]
        for k in range(L):
            bufA[k] = routes[ru, k]
        bufA[pu] = v
        bufA[pv] = u
        m = pu if pu < pv else pv
        return _try(
            ru,
            L,
            m,
            -1,
            0,
            0,
            bufA,
            bufB,
            cap,
            routes,
            lens,
            loads,
            pos,
            rid,
            dep,
            cst,
            rc,
            demand,
            tau,
            dist,
            cong,
            svc,
            snode,
            stime,
            slot_s,
            cw,
        )
    if loads[ru] - demand[u] + demand[v] > cap[ru] or loads[rv] - demand[v] + demand[u] > cap[rv]:
        return False
    La = lens[ru]
    Lb = lens[rv]
    for k in range(La):
        bufA[k] = routes[ru, k]
    for k in range(Lb):
        bufB[k] = routes[rv, k]
    bufA[pu] = v
    bufB[pv] = u
    return _try(
        ru,
        La,
        pu,
        rv,
        Lb,
        pv,
        bufA,
        bufB,
        cap,
        routes,
        lens,
        loads,
        pos,
        rid,
        dep,
        cst,
        rc,
        demand,
        tau,
        dist,
        cong,
        svc,
        snode,
        stime,
        slot_s,
        cw,
    )


@njit(cache=True)
def _two_opt(
    u,
    v,
    cap,
    bufA,
    bufB,
    routes,
    lens,
    loads,
    pos,
    rid,
    dep,
    cst,
    rc,
    demand,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
):  # type: ignore[no-untyped-def]
    r = rid[u]
    if rid[v] != r:
        return False
    L = lens[r]
    p1 = pos[u] if pos[u] < pos[v] else pos[v]
    p2 = pos[v] if pos[u] < pos[v] else pos[u]
    # variant A: reverse [p1+1 .. p2]  -> new edge (r[p1], r[p2])
    if p2 >= p1 + 2:
        for k in range(L):
            bufA[k] = routes[r, k]
        a = p1 + 1
        b = p2
        while a < b:
            tmp = bufA[a]
            bufA[a] = bufA[b]
            bufA[b] = tmp
            a += 1
            b -= 1
        if _try(
            r,
            L,
            p1 + 1,
            -1,
            0,
            0,
            bufA,
            bufB,
            cap,
            routes,
            lens,
            loads,
            pos,
            rid,
            dep,
            cst,
            rc,
            demand,
            tau,
            dist,
            cong,
            svc,
            snode,
            stime,
            slot_s,
            cw,
        ):
            return True
    # variant B: reverse [p1 .. p2-1]  -> new edge (r[p1], r[p2]) at the other side
    if p2 - 1 > p1:
        for k in range(L):
            bufA[k] = routes[r, k]
        a = p1
        b = p2 - 1
        while a < b:
            tmp = bufA[a]
            bufA[a] = bufA[b]
            bufA[b] = tmp
            a += 1
            b -= 1
        if _try(
            r,
            L,
            p1,
            -1,
            0,
            0,
            bufA,
            bufB,
            cap,
            routes,
            lens,
            loads,
            pos,
            rid,
            dep,
            cst,
            rc,
            demand,
            tau,
            dist,
            cong,
            svc,
            snode,
            stime,
            slot_s,
            cw,
        ):
            return True
    return False


@njit(cache=True)
def _two_opt_star(
    u,
    v,
    cap,
    bufA,
    bufB,
    routes,
    lens,
    loads,
    pos,
    rid,
    dep,
    cst,
    rc,
    demand,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
):  # type: ignore[no-untyped-def]
    ru = rid[u]
    rv = rid[v]
    if ru == rv:
        return False
    pu = pos[u]
    pv = pos[v]
    Lu = lens[ru]
    Lv = lens[rv]
    # (a) A' = ru[:pu+1] + rv[pv:] ; B' = rv[:pv] + ru[pu+1:]
    la = 0
    for k in range(pu + 1):
        bufA[la] = routes[ru, k]
        la += 1
    for k in range(pv, Lv):
        bufA[la] = routes[rv, k]
        la += 1
    lb = 0
    for k in range(pv):
        bufB[lb] = routes[rv, k]
        lb += 1
    for k in range(pu + 1, Lu):
        bufB[lb] = routes[ru, k]
        lb += 1
    if _try(
        ru,
        la,
        pu + 1,
        rv,
        lb,
        pv,
        bufA,
        bufB,
        cap,
        routes,
        lens,
        loads,
        pos,
        rid,
        dep,
        cst,
        rc,
        demand,
        tau,
        dist,
        cong,
        svc,
        snode,
        stime,
        slot_s,
        cw,
    ):
        return True
    # (c) A' = ru[:pu+1] + rev(rv[:pv+1]) ; B' = rev(ru[pu+1:]) + rv[pv+1:]
    la = 0
    for k in range(pu + 1):
        bufA[la] = routes[ru, k]
        la += 1
    for k in range(pv, -1, -1):
        bufA[la] = routes[rv, k]
        la += 1
    lb = 0
    for k in range(Lu - 1, pu, -1):
        bufB[lb] = routes[ru, k]
        lb += 1
    for k in range(pv + 1, Lv):
        bufB[lb] = routes[rv, k]
        lb += 1
    return _try(
        ru,
        la,
        pu + 1,
        rv,
        lb,
        0,
        bufA,
        bufB,
        cap,
        routes,
        lens,
        loads,
        pos,
        rid,
        dep,
        cst,
        rc,
        demand,
        tau,
        dist,
        cong,
        svc,
        snode,
        stime,
        slot_s,
        cw,
    )


@njit(cache=True)
def _scan(
    nb,
    order,
    cand,
    cap,
    bufA,
    bufB,
    routes,
    lens,
    loads,
    pos,
    rid,
    dep,
    cst,
    rc,
    demand,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
):  # type: ignore[no-untyped-def]
    applied = 0
    K = cand.shape[1]
    for oi in range(order.shape[0]):
        u = order[oi]
        for ci in range(K):
            v = cand[u, ci]
            if v == 0 or v == u:
                continue
            ok = False
            if nb == 0:
                ok = _seg_move(
                    u,
                    1,
                    0,
                    v,
                    True,
                    cap,
                    bufA,
                    bufB,
                    routes,
                    lens,
                    loads,
                    pos,
                    rid,
                    dep,
                    cst,
                    rc,
                    demand,
                    tau,
                    dist,
                    cong,
                    svc,
                    snode,
                    stime,
                    slot_s,
                    cw,
                )
                if not ok:
                    ok = _seg_move(
                        u,
                        1,
                        0,
                        v,
                        False,
                        cap,
                        bufA,
                        bufB,
                        routes,
                        lens,
                        loads,
                        pos,
                        rid,
                        dep,
                        cst,
                        rc,
                        demand,
                        tau,
                        dist,
                        cong,
                        svc,
                        snode,
                        stime,
                        slot_s,
                        cw,
                    )
            elif nb == 1:
                ok = _swap(
                    u,
                    v,
                    cap,
                    bufA,
                    bufB,
                    routes,
                    lens,
                    loads,
                    pos,
                    rid,
                    dep,
                    cst,
                    rc,
                    demand,
                    tau,
                    dist,
                    cong,
                    svc,
                    snode,
                    stime,
                    slot_s,
                    cw,
                )
            elif nb == 2:
                ok = _two_opt(
                    u,
                    v,
                    cap,
                    bufA,
                    bufB,
                    routes,
                    lens,
                    loads,
                    pos,
                    rid,
                    dep,
                    cst,
                    rc,
                    demand,
                    tau,
                    dist,
                    cong,
                    svc,
                    snode,
                    stime,
                    slot_s,
                    cw,
                )
            elif nb == 3:
                ok = _two_opt_star(
                    u,
                    v,
                    cap,
                    bufA,
                    bufB,
                    routes,
                    lens,
                    loads,
                    pos,
                    rid,
                    dep,
                    cst,
                    rc,
                    demand,
                    tau,
                    dist,
                    cong,
                    svc,
                    snode,
                    stime,
                    slot_s,
                    cw,
                )
            else:
                for s in range(2, 4):
                    for rev in range(2):
                        for aft in range(2):
                            if not ok:
                                ok = _seg_move(
                                    u,
                                    s,
                                    rev,
                                    v,
                                    aft == 1,
                                    cap,
                                    bufA,
                                    bufB,
                                    routes,
                                    lens,
                                    loads,
                                    pos,
                                    rid,
                                    dep,
                                    cst,
                                    rc,
                                    demand,
                                    tau,
                                    dist,
                                    cong,
                                    svc,
                                    snode,
                                    stime,
                                    slot_s,
                                    cw,
                                )
            if ok:
                applied += 1
                break
    return applied


@njit(cache=True)
def vnd_kernel(
    routes,
    lens,
    demand,
    cap,
    tau,
    dist,
    cong,
    svc,
    snode,
    stime,
    slot_s,
    cw,
    cand,
    order,
    nb_list,
    max_passes,
):  # type: ignore[no-untyped-def]
    """Improve routes/lens in place; returns total cost J."""
    R = routes.shape[0]
    L = routes.shape[1]
    N = demand.shape[0]
    loads = np.zeros(R, dtype=np.int64)
    pos = np.zeros(N, dtype=np.int32)
    rid = np.zeros(N, dtype=np.int32)
    dep = np.zeros((R, L + 1))
    cst = np.zeros((R, L + 1))
    rc = np.zeros(R)
    bufA = np.zeros(2 * L + 8, dtype=np.int32)
    bufB = np.zeros(2 * L + 8, dtype=np.int32)
    for r in range(R):
        _rebuild(
            r,
            routes,
            lens,
            loads,
            pos,
            rid,
            dep,
            cst,
            rc,
            demand,
            tau,
            dist,
            cong,
            svc,
            snode,
            stime,
            slot_s,
            cw,
        )
    passes = 0
    k = 0
    while k < nb_list.shape[0] and passes < max_passes:
        cnt = _scan(
            nb_list[k],
            order,
            cand,
            cap,
            bufA,
            bufB,
            routes,
            lens,
            loads,
            pos,
            rid,
            dep,
            cst,
            rc,
            demand,
            tau,
            dist,
            cong,
            svc,
            snode,
            stime,
            slot_s,
            cw,
        )
        passes += 1
        if cnt > 0:
            k = 0
        else:
            k += 1
    total = 0.0
    for r in range(R):
        total += rc[r]
    return total


@njit(cache=True)
def cuts_to_array(g, cuts, L):  # type: ignore[no-untyped-def]
    R = cuts.shape[0]
    n = g.shape[0]
    routes = np.zeros((R, L), dtype=np.int32)
    lens = np.zeros(R, dtype=np.int32)
    for r in range(R):
        a = cuts[r]
        b = cuts[r + 1] if r + 1 < R else n
        lens[r] = b - a
        for k in range(a, b):
            routes[r, k - a] = g[k]
    return routes, lens


@njit(cache=True)
def array_to_tour(routes, lens):  # type: ignore[no-untyped-def]
    tot = 0
    for r in range(routes.shape[0]):
        tot += lens[r]
    tour = np.empty(tot, dtype=np.int32)
    w = 0
    for r in range(routes.shape[0]):
        for k in range(lens[r]):
            tour[w] = routes[r, k]
            w += 1
    return tour


def nb_codes(names: list[str]) -> NDArray[np.int32]:
    return np.asarray([NB_CODES[n] for n in names], dtype=np.int32)


def improve_arrays(
    routes: NDArray[np.int32],
    lens: NDArray[np.int32],
    inst: Instance,
    cw: NDArray[np.float64],
    order: NDArray[np.int32],
    k: int,
    names: list[str],
    max_passes: int,
    fleet: Fleet | None = None,
) -> float:
    tb = inst.tables
    fl = fleet or Fleet.depot(routes.shape[0], inst.depart_s, inst.Q)
    return float(
        vnd_kernel(
            routes,
            lens,
            inst.demand,
            fl.cap,
            tb.tau,
            tb.dist,
            tb.cong,
            inst.sv,
            fl.snode,
            fl.stime,
            tb.slot_s,
            cw,
            inst.candidates(k),
            order,
            nb_codes(names),
            max_passes,
        )
    )
