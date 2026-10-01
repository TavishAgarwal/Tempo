"""Vehicle states at incident time t_e: position, committed next stop, ETA, remaining load."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from taqpso.core.instance import Instance
from taqpso.core.solution import Solution
from taqpso.sim.simulator import Network
from taqpso.traffic.igp import edge_time_c


@dataclass
class VehicleState:
    vehicle: int
    status: str  # not_started | enroute | servicing | returning | done
    graph_node: int  # graph node where the vehicle can next be redirected (end of current edge)
    t_free: float  # time it is at graph_node
    committed: int  # customer it must reach next (0 = depot return, -1 = none)
    remaining: list[int] = field(default_factory=list)  # unserved customers incl. committed
    served_load: int = 0  # demand already delivered (committed stop NOT included)
    eta_committed: float = 0.0  # old-plan ETA at the committed stop
    start_orig: int = (
        0  # table node the (re)plan starts from: committed stop, serviced stop or depot
    )
    ready_hint: float = 0.0  # for servicing / not_started / done states

    @property
    def free_capacity_base(self) -> int:
        return self.served_load


def _leg_exit_times(net: Network, edges: NDArray[np.int32], t0: float) -> list[float]:
    g = net.graph
    out: list[float] = []
    t = t0
    for e in edges:
        row = net.fac[e] if net.per_edge else net.fac[g.road_class[e]]
        dt, _ = edge_time_c(g.length_m[e], g.freeflow_mps[e], row, t, net.slot_s, net.thr)
        t += dt
        out.append(t)
    return out


def vehicle_states(inst: Instance, net: Network, plan: Solution, t_e: float) -> list[VehicleState]:
    """Walk each planned route under the pre-incident network and locate its vehicle at t_e."""
    g, pd = net.graph, net.pairs
    states: list[VehicleState] = []
    for v, route in enumerate(plan.routes):
        t = inst.depart_s
        if t_e < t:
            states.append(
                VehicleState(v, "not_started", int(pd.nodes[0]), t, -1, list(route), 0, 0.0, 0, t)
            )
            continue
        prev = 0
        served = 0
        stops = [*route, 0]
        st: VehicleState | None = None
        for k, c in enumerate(stops):
            edges = pd.path(prev, c)
            ex = _leg_exit_times(net, edges, t)
            t_arr = ex[-1] if ex else t
            if t_e < t_arr or (c == 0 and t_e < t_arr):
                # on this leg: find the edge being driven at t_e
                idx = int(np.searchsorted(np.asarray(ex), t_e, side="right")) if ex else 0
                idx = min(idx, len(edges) - 1) if len(edges) else 0
                node = int(g.edge_to[edges[idx]]) if len(edges) else int(pd.nodes[prev])
                tx = ex[idx] if ex else t
                st = VehicleState(
                    v,
                    "returning" if c == 0 else "enroute",
                    node,
                    tx,
                    c,
                    [] if c == 0 else list(route[k:]),
                    served,
                    t_arr,
                    int(c),
                    t_arr,
                )
                break
            t = t_arr
            if c == 0:
                break
            t_dep = t_arr + float(inst.service[c])
            if t_e < t_dep:  # being serviced at c
                served += int(inst.demand[c])
                st = VehicleState(
                    v,
                    "servicing",
                    int(pd.nodes[c]),
                    t_dep,
                    -1,
                    list(route[k + 1 :]),
                    served,
                    t_arr,
                    int(c),
                    t_dep,
                )
                break
            served += int(inst.demand[c])
            t = t_dep
            prev = c
        if st is None:  # finished before t_e
            st = VehicleState(v, "done", int(pd.nodes[0]), t, -1, [], served, t, 0, t)
        states.append(st)
    return states
