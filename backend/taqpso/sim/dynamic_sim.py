"""Ground-truth cost of a (re)plan from t_e onward, under the post-incident network."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from taqpso.core.instance import Instance
from taqpso.core.objective import Metrics, Objective
from taqpso.dynamic.vehicle_state import VehicleState
from taqpso.paths.td_dijkstra import td_shortest_path
from taqpso.sim.simulator import Network
from taqpso.traffic.igp import path_time


def _leg(net: Network, edges: NDArray[np.int32], t: float) -> tuple[float, float, float]:
    g = net.graph
    T, D, C = path_time(
        edges, g.length_m, g.freeflow_mps, net.fac, net.road_class, t, net.slot_s, net.thr
    )
    return float(T), float(D), float(C)


def simulate_remaining(
    inst: Instance,
    net: Network,
    states: list[VehicleState],
    routes: list[list[int]],
    obj: Objective,
    t_e: float,
) -> Metrics:
    """Remaining T/D/C from t_e: finish the current edge, reach the committed stop (TD path under
    the incident), then follow `routes[v]` over the stored (re-pathed) leg paths."""
    g, pd = net.graph, net.pairs
    T = D = C = 0.0
    used = 0
    rT: list[float] = []
    loads: list[int] = []
    for s, route in zip(states, routes, strict=True):
        t = t_e
        vT = 0.0
        cur = 0
        if s.status in ("enroute", "returning"):
            vT += s.t_free - t_e
            t = s.t_free
            dest = int(s.committed)
            p = td_shortest_path(
                g, net.fac, s.graph_node, int(pd.nodes[dest]), t, net.slot_s, per_edge=net.per_edge
            )
            tt, d, c = _leg(net, p.edges, t)
            vT += tt
            D += d
            C += c
            t += tt
            if dest > 0:
                t += float(inst.service[dest])
            cur = dest
        elif s.status == "servicing":
            t = s.t_free
            cur = s.start_orig
        else:
            t = max(t_e, s.ready_hint)
            cur = 0
        for c_next in [*route, 0]:
            if cur == c_next:
                continue
            tt, d, c = _leg(net, pd.path(cur, c_next), t)
            vT += tt
            D += d
            C += c
            t += tt + (float(inst.service[c_next]) if c_next else 0.0)
            cur = c_next
        T += vT
        if route or s.status in ("enroute", "servicing", "returning"):
            used += 1
        rT.append(vT)
        loads.append(int(inst.demand[route].sum()) if route else 0)
    return Metrics(T, D, C, obj.J(T, D, C), used, tuple(rT), tuple(loads))
