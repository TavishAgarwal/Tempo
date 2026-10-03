"""Export the real Delhi demo (road graph, customers, plan, incident re-plan) for the landing page.

Writes frontend/public/landing-data.json. Everything comes from the same code path the API uses:
the delhi_demo scenario, the stored E4 base plan, and the E4 'zone' incident at 18:00.
Run from backend/:  .venv/bin/python ../scripts/export_landing_data.py
"""

from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from taqpso.api.geometry import leg_coords
from taqpso.bench.make_scenarios import load_scenario
from taqpso.config import REPO_ROOT, load_config, tuned_overrides
from taqpso.core.objective import Objective
from taqpso.core.solution import Solution
from taqpso.dynamic.fallback import apply_incident, safe_plan
from taqpso.dynamic.reopt import build_reopt, reoptimize
from taqpso.paths.td_dijkstra import td_shortest_path
from taqpso.sim.simulator import simulate
from taqpso.traffic.incidents import Incident

OUT = REPO_ROOT / "frontend" / "public" / "landing-data.json"


def r5(x: float) -> float:
    return round(float(x), 5)


def main() -> None:
    sc = load_scenario("delhi_demo")
    inst, net = sc.inst, sc.net
    g, pd = net.graph, net.pairs
    cfg = load_config(tuned_overrides("qpso"), {"objective": {"preset": "fastest"}})
    obj = Objective.from_instance(inst, cfg)
    plan = json.loads((REPO_ROOT / "results/e4/base_delhi_demo.json").read_text())["routes"]
    t_e, dur, k_edges = 18 * 3600.0, 3600.0, 30

    # --- road network: undirected, deduplicated, with the 17:30 and 03:00 speed ratios per class
    slot_peak = int(inst.depart_s // net.slot_s)
    slot_night = int(3 * 3600 // net.slot_s)
    seen: dict[tuple[int, int], int] = {}
    for e in range(g.n_edges):
        a, b = int(g.edge_from[e]), int(g.edge_to[e])
        seen.setdefault((min(a, b), max(a, b)), e)
    used = sorted({i for k in seen for i in k})
    remap = {n: i for i, n in enumerate(used)}
    nodes = [[r5(g.node_xy[n][0]), r5(g.node_xy[n][1])] for n in used]
    edges = [[remap[a], remap[b], int(g.road_class[e]), r5(net.fac[g.road_class[e]][slot_peak])]
             for (a, b), e in seen.items()]
    edge_index = {k: i for i, k in enumerate(seen)}
    ratios_night = {int(c): r5(net.fac[c][slot_night]) for c in np.unique(g.road_class)}
    ratios_peak = {int(c): r5(net.fac[c][slot_peak]) for c in np.unique(g.road_class)}

    # --- customers and base plan
    veh_of = {c: v for v, r in enumerate(plan) for c in r}
    cust = [[r5(inst.coords[c][0]), r5(inst.coords[c][1]), int(inst.demand[c]), veh_of[c]]
            for c in range(1, inst.n + 1)]
    depot = [r5(inst.coords[0][0]), r5(inst.coords[0][1])]

    def pl(points):  # type: ignore[no-untyped-def]
        return [[r5(x), r5(y)] for x, y in points]

    def full_route(r):  # type: ignore[no-untyped-def]
        pts: list = []
        prev = 0
        for c in [*r, 0]:
            pts.extend(leg_coords(net, prev, c))
            prev = c
        return pl(pts)

    m0 = simulate(inst, net, Solution(plan), obj)

    # --- incident: top-k shared edges, blocked 18:00-19:00
    cnt: dict[int, int] = {}
    for r in plan:
        prev = 0
        for c in [*r, 0]:
            for e in pd.path(prev, c):
                cnt[int(e)] = cnt.get(int(e), 0) + 1
            prev = c
    inc_edges = tuple(sorted(cnt, key=lambda e: -cnt[e])[:k_edges])
    inc = Incident(inc_edges, 0.1, t_e, t_e + dur)
    seg = lambda e: [[r5(x), r5(y)] for x, y in (g.node_xy[g.edge_from[e]], g.node_xy[g.edge_to[e]])]  # noqa: E731

    safe_plan(inst, net, Solution(plan), [inc], t_e)  # warm kernels
    t0 = time.perf_counter()
    fb, world_fb = safe_plan(inst, net, Solution(plan), [inc], t_e)
    from taqpso.sim.dynamic_sim import simulate_remaining

    mfb = simulate_remaining(inst, world_fb.net, fb.states, fb.routes, obj, t_e)
    latency = time.perf_counter() - t0
    world = apply_incident(inst, net, [inc], t_e)
    prob = build_reopt(inst, world, fb.states, fb.routes, t_e)
    res = reoptimize(prob, cfg, obj, 0, 10.0, True, None, None)
    best = prob.to_original(res.solution.routes)
    mnew = simulate_remaining(inst, world.net, fb.states, best, obj, t_e)
    wg, wpd = world.net.graph, world.net.pairs

    def geometry(routes):  # type: ignore[no-untyped-def]
        out = []
        for s, r in zip(fb.states, routes, strict=True):
            pts: list = []
            cur = 0
            if s.status in ("enroute", "returning"):
                p = td_shortest_path(wg, world.net.fac, s.graph_node, int(wpd.nodes[s.committed]),
                                     s.t_free, world.net.slot_s, per_edge=True)
                pts = [[float(x), float(y)] for x, y in wg.node_xy[p.nodes]]
                cur = s.committed
            elif s.status == "servicing":
                cur = s.start_orig
            for c in [*r, 0]:
                if c != cur:
                    pts += leg_coords(world.net, cur, c)
                cur = c
            out.append(pl(pts))
        return out

    veh_fb = {c: v for v, r in enumerate(fb.routes) for c in r}
    moved = [{"customer": c, "from": veh_fb.get(c, v), "to": v}
             for v, r in enumerate(best) for c in r if veh_fb.get(c, v) != v]
    vehicles = [{"v": s.vehicle, "status": s.status, "lon": r5(wg.node_xy[s.graph_node][0]),
                 "lat": r5(wg.node_xy[s.graph_node][1])} for s in fb.states]

    data = {
        "source": "delhi_demo · calibrated time-of-day profile (TomTom-anchored, synthetic) · OSM",
        "nodes": nodes,
        "edges": edges,
        "ratios": {"peak": ratios_peak, "night": ratios_night},
        # mean speed ratio per hour of day, by road class (the 24-hour dial on the landing page)
        "hourly": {str(int(c)): [round(float(np.mean(net.fac[c][h * 4 : h * 4 + 4])), 3) for h in range(24)]
                   for c in np.unique(g.road_class)},
        "depot": depot,
        "customers": cust,
        "capacity": int(inst.Q),
        "plan": {"routes": plan, "geometry": [full_route(r) for r in plan],
                 "T_min": round(m0.T / 60, 1), "D_km": round(m0.D / 1000, 1),
                 "C_min": round(m0.C / 60, 1), "J": round(m0.J, 4)},
        "incident": {
            "t_start_h": t_e / 3600, "t_end_h": (t_e + dur) / 3600, "factor": 0.1,
            "segments": [seg(e) for e in inc_edges],
            "fallback_latency_s": round(latency, 3),
            "fallback": {"T_rem_min": round(mfb.T / 60, 1), "J": round(mfb.J, 4)},
            "final": {"T_rem_min": round(mnew.T / 60, 1), "J": round(mnew.J, 4)},
            "vehicles": vehicles,
            "moved": moved,
            "geometry": geometry(best),
            "fallback_geometry": geometry(fb.routes),
        },
    }
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(OUT, OUT.stat().st_size // 1024, "KB", "moved", len(moved), "latency", latency)
    print({k: v for k, v in data["plan"].items() if k not in ("routes", "geometry")})
    print(data["incident"]["fallback"], data["incident"]["final"])


if __name__ == "__main__":
    main()
