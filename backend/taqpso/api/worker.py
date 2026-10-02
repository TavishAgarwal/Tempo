"""Process-pool job bodies. One solve = one process, one thread; progress goes to a queue."""

from __future__ import annotations

import os
import time
from dataclasses import replace
from typing import Any

for _v in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from taqpso.api.geometry import leg_coords, route_geometry  # noqa: E402
from taqpso.config import load_config, tuned_overrides  # noqa: E402
from taqpso.core.objective import Objective, evaluate_solution  # noqa: E402
from taqpso.core.solution import Solution  # noqa: E402
from taqpso.store.results import RunRecord, save_run  # noqa: E402

OPT = {"qpso": "qpso", "pso": "pso", "ga": "ga", "random": "random"}


def warmup() -> None:
    """JIT/load every kernel once so the first request has no compile lag."""
    from taqpso.bench.make_scenarios import SCEN, load_scenario
    from taqpso.solver.runner import solve

    f = next(iter(sorted(SCEN.glob("*.json"))), None)
    if f is None:
        return
    sc = load_scenario(f.stem)
    res = solve(sc.inst, load_config({"swarm": {"size": 2}}), "qpso", 0, max_iters=1)
    _warm_incident(sc, res.solution)
    _warm_paths(sc)


def _warm_incident(sc: Any, sol: Solution) -> None:
    """Compile the incident kernels (per-edge IGP, re-pathing, fallback) before the demo."""
    from taqpso.dynamic.fallback import apply_incident, safe_plan
    from taqpso.traffic.incidents import Incident

    pd = sc.net.pairs
    edges = tuple(int(e) for e in pd.path_edges[: min(5, len(pd.path_edges))])
    t_e = sc.inst.depart_s + 900.0
    inc = Incident(edges, 0.1, t_e, t_e + 3600.0)
    safe_plan(sc.inst, sc.net, sol, [inc], t_e)
    world = apply_incident(sc.inst, sc.net, [inc], t_e)
    nodes = sc.net.pairs.nodes
    if int(nodes[0]) != int(nodes[-1]):
        from taqpso.paths.td_dijkstra import td_shortest_path

        td_shortest_path(
            world.net.graph,
            world.net.fac,
            int(nodes[0]),
            int(nodes[-1]),
            t_e,
            world.net.slot_s,
            per_edge=True,
        )


def _warm_paths(sc: Any) -> None:
    from taqpso.paths.td_dijkstra import td_shortest_path

    g, pd = sc.net.graph, sc.net.pairs
    a, b = int(pd.nodes[0]), int(pd.nodes[min(1, len(pd.nodes) - 1)])
    if a != b:
        td_shortest_path(g, sc.net.fac, a, b, sc.inst.depart_s, sc.net.slot_s)


def ready() -> None:
    """No-op task: submitting it starts (and warms) a pool worker ahead of the first job."""


def _metrics(m: Any) -> dict[str, Any]:
    return m.as_dict()  # type: ignore[no-any-return]


def solve_job(spec: dict[str, Any], q: Any, stop: Any) -> dict[str, Any]:
    # every failure (scenario load, live-traffic fetch, solver) must reach the queue as an
    # error, or the job manager waits for a final message forever
    try:
        out = _solve(spec, q, stop)
    except Exception as e:  # noqa: BLE001 - surfaced to the UI with its cause
        out = {"type": "error", "message": str(e)}
    q.put(out)
    return out


def _solve(spec: dict[str, Any], q: Any, stop: Any) -> dict[str, Any]:
    from taqpso.baselines.pyvrp_adapter import slot_matrix, solve_pyvrp
    from taqpso.bench.make_scenarios import load_scenario
    from taqpso.sim.simulator import simulate
    from taqpso.solver.optimizers import get_optimizer
    from taqpso.solver.runner import Runner

    t0 = time.perf_counter()
    sc = load_scenario(spec["instance_id"])
    if spec.get("live"):
        from taqpso.bench.tomtom import live_ratios, with_live_traffic

        ratios, stamp = live_ratios()
        now = time.localtime()
        slot = int((now.tm_hour * 3600 + now.tm_min * 60) // sc.net.slot_s)
        sc = with_live_traffic(sc, ratios, slot)
        q.put({"type": "note", "message": f"Live traffic (TomTom), snapshot {stamp}"})
    inst = sc.inst
    if spec.get("depart_s") is not None:
        inst = replace(inst, depart_s=float(spec["depart_s"]), _cand={})
    solver = spec["solver"]
    cfg = load_config(
        tuned_overrides(OPT.get(solver, "qpso")), {"objective": {"preset": spec["preset"]}}
    )
    obj = Objective.from_instance(inst, cfg)
    trace: list[list[float]] = []

    def cb(t: float, J: float, sol: Solution, div: float) -> None:
        m = evaluate_solution(inst, sol, obj)
        q.put(
            {
                "type": "improvement",
                "t": t,
                "cost": J,
                "routes": sol.routes,
                "diversity": div,
                "metrics": _metrics(m),
                "geometry": [route_geometry(sc.net, r) for r in sol.routes],
            }
        )

    q.put({"type": "state", "state": "solving"})
    if solver == "pyvrp":
        sol = solve_pyvrp(inst, spec["budget_s"], spec["seed"], slot_matrix(inst))
        sol.validate(inst)
        trace = []
    else:
        runner = Runner(
            inst,
            cfg,
            get_optimizer(OPT[solver], cfg),
            np.random.Generator(np.random.PCG64(spec["seed"])),
            obj,
            cb,
        )
        res = runner.run(spec["budget_s"], should_stop=lambda: bool(stop.is_set()))
        sol, trace = res.solution, res.trace
    sol.validate(inst)
    m = simulate(inst, sc.net, sol, obj)
    rec = RunRecord(
        kind="solve",
        instance_id=inst.name,
        instance_hash=inst.hash(),
        config=cfg.to_dict(),
        config_hash=cfg.hash(),
        solver=solver,
        seed=spec["seed"],
        budget_s=spec["budget_s"],
        metrics={**_metrics(m), "elapsed_s": time.perf_counter() - t0},
        solution={"routes": sol.routes, "depart": inst.depart_s},
        trace=trace,
        extra={"preset": spec["preset"]},
    )
    save_run(rec)
    return {
        "type": "done",
        "run_id": rec.run_id,
        "routes": sol.routes,
        "metrics": _metrics(m),
        "geometry": [route_geometry(sc.net, r) for r in sol.routes],
        "depart": inst.depart_s,
        "stopped": bool(stop.is_set()),
    }


def incident_job(spec: dict[str, Any], q: Any, stop: Any) -> dict[str, Any]:
    from taqpso.bench.make_scenarios import load_scenario
    from taqpso.dynamic.fallback import apply_incident, safe_plan
    from taqpso.dynamic.reopt import build_reopt, reoptimize
    from taqpso.paths.td_dijkstra import td_shortest_path
    from taqpso.sim.dynamic_sim import simulate_remaining
    from taqpso.traffic.incidents import Incident

    try:
        sc = load_scenario(spec["instance_id"])
        inst = replace(sc.inst, depart_s=float(spec["depart"]), _cand={})
        cfg = load_config(tuned_overrides("qpso"), {"objective": {"preset": spec["preset"]}})
        obj = Objective.from_instance(inst, cfg)
        t_e = float(spec["t_start"])
        inc = Incident(tuple(spec["edges"]), float(spec["factor"]), t_e, float(spec["t_end"]))
        t0 = time.perf_counter()
        fb, world = safe_plan(inst, sc.net, Solution(spec["routes"]), [inc], t_e)
        g, pd = world.net.graph, world.net.pairs

        def vehicles_view() -> list[dict[str, Any]]:
            return [
                {
                    "vehicle": s.vehicle,
                    "status": s.status,
                    "lon": float(g.node_xy[s.graph_node][0]),
                    "lat": float(g.node_xy[s.graph_node][1]),
                    "committed": s.committed,
                    "eta_s": s.eta_committed,
                }
                for s in fb.states
            ]

        def geometry(routes: list[list[int]]) -> list[list[list[float]]]:
            out = []
            for s, r in zip(fb.states, routes, strict=True):
                pts: list[list[float]] = []
                cur = 0
                if s.status in ("enroute", "returning"):
                    p = td_shortest_path(
                        g,
                        world.net.fac,
                        s.graph_node,
                        int(pd.nodes[s.committed]),
                        s.t_free,
                        world.net.slot_s,
                        per_edge=True,
                    )
                    pts = [[float(x), float(y)] for x, y in g.node_xy[p.nodes]]
                    cur = s.committed
                elif s.status == "servicing":
                    cur = s.start_orig
                for c in [*r, 0]:
                    if c != cur:
                        pts += leg_coords(world.net, cur, c)
                    cur = c
                out.append(pts)
            return out

        m0 = simulate_remaining(inst, world.net, fb.states, fb.routes, obj, t_e)
        fb_geometry = geometry(fb.routes)
        latency = time.perf_counter() - t0  # everything the UI needs to draw the safe plan
        q.put(
            {
                "type": "fallback",
                "state": "safe_plan",
                "routes": fb.routes,
                "latency_s": latency,
                "affected_pairs": world.affected_pairs,
                "metrics": _metrics(m0),
                "geometry": fb_geometry,
                "vehicles": vehicles_view(),
            }
        )
        world = apply_incident(inst, sc.net, [inc], t_e)  # full world for re-optimisation
        prob = build_reopt(inst, world, fb.states, fb.routes, t_e)
        best = fb.routes
        first = float("nan")
        start = time.perf_counter()

        def cb(t: float, J: float, routes: list[list[int]], div: float) -> None:
            nonlocal best, first
            best = routes
            if first != first:
                first = t
            q.put(
                {
                    "type": "improvement",
                    "t": t,
                    "cost": J,
                    "routes": routes,
                    "diversity": div,
                    "geometry": geometry(routes),
                }
            )

        if prob.sub.n > 0:
            res = reoptimize(prob, cfg, obj, spec["seed"], spec["budget_s"], True, spec["mu"], cb)
            best = prob.to_original(res.solution.routes)
        m1 = simulate_remaining(inst, world.net, fb.states, best, obj, t_e)
        veh_fb = {c: v for v, r in enumerate(fb.routes) for c in r}
        moved = [
            {"customer": c, "from": veh_fb[c], "to": v}
            for v, r in enumerate(best)
            for c in r
            if veh_fb.get(c, v) != v
        ]
        rec = RunRecord(
            kind="incident",
            instance_id=inst.name,
            instance_hash=inst.hash(),
            config=cfg.to_dict(),
            config_hash=cfg.hash(),
            solver="qpso_warm",
            seed=spec["seed"],
            budget_s=spec["budget_s"],
            metrics={
                **_metrics(m1),
                "fallback_latency_s": latency,
                "time_first_s": first,
                "fallback_metrics": _metrics(m0),
                "moved": len(moved),
            },
            solution={"routes": best, "t_e": t_e},
            extra={"incident": spec["edges"], "mu": spec["mu"]},
        )
        save_run(rec)
        out = {
            "type": "done",
            "run_id": rec.run_id,
            "routes": best,
            "metrics": _metrics(m1),
            "fallback_metrics": _metrics(m0),
            "geometry": geometry(best),
            "moved": moved,
            "reopt_s": time.perf_counter() - start,
            "latency_s": latency,
        }
    except Exception as e:  # noqa: BLE001
        out = {"type": "error", "message": str(e)}
    q.put(out)
    return out
