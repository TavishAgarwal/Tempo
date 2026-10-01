"""Warm re-optimisation after an incident: fleet-aware Split + warm-started swarm + stability mu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from taqpso.config import Config
from taqpso.core.fleet import Fleet
from taqpso.core.instance import Instance, TravelTables
from taqpso.core.objective import Objective
from taqpso.dynamic.fallback import IncidentWorld
from taqpso.dynamic.vehicle_state import VehicleState
from taqpso.paths.td_dijkstra import td_shortest_path
from taqpso.solver.keys import reflect_clip
from taqpso.solver.optimizers import get_optimizer
from taqpso.solver.runner import Runner, RunResult
from taqpso.solver.seeds import tour_to_keys

# (elapsed s, J, per-vehicle routes in original customer ids, diversity)
DynCb = Callable[[float, float, list[list[int]], float], None]


@dataclass
class ReoptProblem:
    sub: Instance
    fleet: Fleet
    remaining: list[int]  # sub customer i (1-based) is original customer remaining[i - 1]
    states: list[VehicleState]
    prev_assign: NDArray[np.int64]  # per sub customer: previous vehicle (-1 none)
    incumbent_tour: NDArray[np.int32]  # sub ids, vehicles concatenated in order

    def to_original(self, sub_routes: list[list[int]]) -> list[list[int]]:
        return [[self.remaining[c - 1] for c in r] for r in sub_routes]


def build_reopt(
    inst: Instance,
    world: IncidentWorld,
    states: list[VehicleState],
    fallback_routes: list[list[int]],
    t_e: float,
) -> ReoptProblem:
    net = world.net
    g, pd = net.graph, net.pairs
    V = len(states)
    start_orig: list[int] = []
    ready: list[float] = []
    cap: list[int] = []
    for s in states:
        if s.status == "enroute":
            b = s.committed
            p = td_shortest_path(
                g, net.fac, s.graph_node, int(pd.nodes[b]), s.t_free, net.slot_s, per_edge=True
            )
            start_orig.append(b)
            ready.append(p.arrival_s + float(inst.service[b]))
            cap.append(inst.Q - s.served_load - int(inst.demand[b]))
        elif s.status == "returning":
            p = td_shortest_path(
                g, net.fac, s.graph_node, int(pd.nodes[0]), s.t_free, net.slot_s, per_edge=True
            )
            start_orig.append(0)
            ready.append(p.arrival_s)
            cap.append(inst.Q)
        elif s.status == "servicing":
            start_orig.append(s.start_orig)
            ready.append(s.t_free)
            cap.append(inst.Q - s.served_load)
        else:
            start_orig.append(0)
            ready.append(max(t_e, s.ready_hint))
            cap.append(inst.Q)
    remaining = sorted({c for r in fallback_routes for c in r})
    m = len(remaining)
    orig_ids = np.asarray([0, *remaining, *[so for so in start_orig]], dtype=np.int64)
    tb = world.tables
    ix = np.ix_(orig_ids, orig_ids)
    sub_tb = TravelTables(
        np.ascontiguousarray(tb.tau[ix[0], ix[1], :]),
        np.ascontiguousarray(tb.dist[ix]),
        np.ascontiguousarray(tb.cong[ix[0], ix[1], :]),
        tb.slot_s,
    )
    demand = np.zeros(len(orig_ids), dtype=np.int32)
    demand[1 : m + 1] = inst.demand[remaining]
    sub = Instance(
        inst.name + "_reopt",
        inst.coords[orig_ids],
        demand,
        inst.Q,
        sub_tb,
        inst.service[orig_ids],
        None,
        t_e,
        {},
        n_virtual=V,
    )
    snode = np.asarray([m + 1 + v if start_orig[v] > 0 else 0 for v in range(V)], dtype=np.int32)
    fleet = Fleet(snode, np.asarray(ready, dtype=np.float64), np.asarray(cap, dtype=np.int64))
    idx_of = {c: i + 1 for i, c in enumerate(remaining)}
    prev = np.full(m + 1, -1, dtype=np.int64)
    tour: list[int] = []
    for v, r in enumerate(fallback_routes):
        for c in r:
            prev[idx_of[c]] = v
            tour.append(idx_of[c])
    return ReoptProblem(sub, fleet, remaining, states, prev, np.asarray(tour, dtype=np.int32))


def reoptimize(
    prob: ReoptProblem,
    cfg: Config,
    obj: Objective,
    seed: int,
    budget_s: float,
    warm: bool = True,
    mu: float | None = None,
    on_improvement: DynCb | None = None,
    solver: str = "qpso",
    max_iters: int | None = None,
) -> RunResult:
    rng = np.random.Generator(np.random.PCG64(seed))
    M = cfg.swarm.size
    n = prob.sub.n
    extra: list[NDArray[np.float64]] = []
    if warm and len(prob.incumbent_tour) == n:
        base = tour_to_keys(prob.incumbent_tour)
        k = max(1, round(cfg.reopt.warm_fraction * M))
        extra = [base.copy()] + [
            reflect_clip(base + rng.normal(0.0, cfg.reopt.warm_noise, n)) for _ in range(k - 1)
        ]

    def cb(t: float, J: float, sol, div: float) -> None:  # type: ignore[no-untyped-def]
        if on_improvement:
            on_improvement(t, J, prob.to_original(sol.routes), div)

    runner = Runner(
        prob.sub,
        cfg,
        get_optimizer(solver, cfg),
        rng,
        obj,
        cb,
        extra,
        prob.fleet,
        prob.prev_assign,
        cfg.reopt.stability_mu if mu is None else mu,
        default_seeds=not warm,
    )
    return runner.run(budget_s if max_iters is None else None, max_iters)
