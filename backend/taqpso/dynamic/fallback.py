"""Incident application + fallback B0: keep every vehicle's remaining sequence, detour legs."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from taqpso.core.instance import Instance, TravelTables
from taqpso.core.solution import Solution
from taqpso.dynamic.vehicle_state import VehicleState, vehicle_states
from taqpso.sim.simulator import Network
from taqpso.traffic.incidents import Incident, apply_incidents, repath_pairs
from taqpso.traffic.pair_tables import build_tables


@dataclass
class IncidentWorld:
    """Network + tables after an incident (affected pair rows re-pathed and recomputed)."""

    net: Network
    tables: TravelTables
    fac_e: NDArray[np.float64]
    affected_pairs: int
    prep_s: float


def apply_incident(
    inst: Instance,
    net: Network,
    incidents: list[Incident],
    t_e: float,
    only_pairs: NDArray[np.int32] | None = None,
) -> IncidentWorld:
    """Apply incidents; with `only_pairs` just those affected pairs are re-pathed/recomputed
    (the safe plan only needs the legs it drives; the full world follows for re-optimisation)."""
    t0 = time.perf_counter()
    g, pd = net.graph, net.pairs
    fac_e = apply_incidents(g, net.fac, incidents, net.slot_s)
    edges = np.unique(np.concatenate([np.asarray(i.edges, dtype=np.int32) for i in incidents]))
    aff = pd.pairs_using(edges)
    n_affected = int(len(aff))
    if only_pairs is not None:
        aff = np.intersect1d(aff, only_pairs.astype(aff.dtype))
    pd2 = repath_pairs(g, pd, aff, fac_e, t_e, net.slot_s) if len(aff) else pd
    tb = (
        build_tables(
            g,
            pd2,
            fac_e,
            net.slot_s,
            net.thr,
            per_edge=True,
            tables=inst.tables,
            pairs=aff if len(aff) else None,
        )
        if len(aff)
        else inst.tables
    )
    net2 = Network(g, pd2, fac_e, net.slot_s, net.thr, per_edge=True)
    return IncidentWorld(net2, tb, fac_e, n_affected, time.perf_counter() - t0)


@dataclass
class FallbackPlan:
    routes: list[list[int]]  # per vehicle: remaining customers after any committed stop, in order
    states: list[VehicleState]
    latency_s: float


def fallback_plan(inst: Instance, net: Network, plan: Solution, t_e: float) -> FallbackPlan:
    """B0: same remaining sequences as the old plan (committed stop first); legs are re-pathed
    by the incident world, so crossing legs detour automatically."""
    t0 = time.perf_counter()
    states = vehicle_states(inst, net, plan, t_e)
    routes = []
    for s in states:
        rem = list(s.remaining)
        if s.committed > 0 and rem and rem[0] == s.committed:
            rem = rem[1:]
        routes.append(rem)
    return FallbackPlan(routes, states, time.perf_counter() - t0)


def leg_pairs(states: list[VehicleState], routes: list[list[int]], N: int) -> NDArray[np.int32]:
    """Pair ids (i*N + j) of every customer-to-customer leg the given plan drives."""
    out: set[int] = set()
    for s, r in zip(states, routes, strict=True):
        cur = (
            s.committed
            if s.status in ("enroute", "returning")
            else (s.start_orig if s.status == "servicing" else 0)
        )
        for c in [*r, 0]:
            if c != cur:
                out.add(cur * N + c)
            cur = c
    return np.fromiter(out, dtype=np.int32, count=len(out))


def safe_plan(
    inst: Instance, net: Network, plan: Solution, incidents: list[Incident], t_e: float
) -> tuple[FallbackPlan, IncidentWorld]:
    """Fallback B0 with a lean incident world (only the legs the old sequences drive)."""
    fb = fallback_plan(inst, net, plan, t_e)
    world = apply_incident(
        inst, net, incidents, t_e, only_pairs=leg_pairs(fb.states, fb.routes, net.pairs.N)
    )
    return fb, world
