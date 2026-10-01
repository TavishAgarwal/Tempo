"""E4: incident recovery: fallback latency, first improvement, quality vs B0-B3, stability."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from experiments import plots, stats
from experiments.driver import load_experiment, run_jobs
from taqpso.baselines.pyvrp_reopt import solve_pyvrp_reopt
from taqpso.bench.make_scenarios import load_scenario
from taqpso.config import REPO_ROOT, load_config
from taqpso.core.instance import TravelTables
from taqpso.core.objective import Objective
from taqpso.core.solution import Solution
from taqpso.dynamic.fallback import apply_incident, safe_plan
from taqpso.dynamic.reopt import build_reopt, reoptimize
from taqpso.sim.dynamic_sim import simulate_remaining
from taqpso.solver.runner import solve
from taqpso.store.results import RunRecord, load_runs, save_run
from taqpso.traffic.incidents import Incident

log = logging.getLogger("e4")
OUT = REPO_ROOT / "results" / "e4"


def base_plan(name: str, seed: int = 0, budget_s: float = 10.0) -> list[list[int]]:
    f = OUT / f"base_{name}.json"
    if f.exists():
        return json.loads(f.read_text())["routes"]  # type: ignore[no-any-return]
    sc = load_scenario(name)
    cfg = load_config()
    r = solve(sc.inst, cfg, "qpso", seed, budget_s=budget_s)
    OUT.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"routes": r.solution.routes}))
    return r.solution.routes


def pick_edges(sc, routes: list[list[int]], k: int) -> tuple[int, ...]:  # type: ignore[no-untyped-def]
    pd_ = sc.net.pairs
    cnt: dict[int, int] = {}
    for r in routes:
        prev = 0
        for c in [*r, 0]:
            for e in pd_.path(prev, c):
                cnt[int(e)] = cnt.get(int(e), 0) + 1
            prev = c
    top = sorted(cnt, key=lambda e: -cnt[e])[:k]
    return tuple(top)


def moved_and_changed(fb: list[list[int]], new: list[list[int]]) -> tuple[int, int]:
    veh_fb = {c: v for v, r in enumerate(fb) for c in r}
    pred_fb = {c: (v, r[i - 1] if i else 0) for v, r in enumerate(fb) for i, c in enumerate(r)}
    moved = changed = 0
    for v, r in enumerate(new):
        for i, c in enumerate(r):
            moved += veh_fb.get(c, v) != v
            changed += pred_fb.get(c) != (v, r[i - 1] if i else 0)
    return moved, changed


def run_inc_job(spec: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config()
    sc = load_scenario(spec["instance"])
    inst = sc.inst
    obj = Objective.from_instance(inst, cfg)
    plan = Solution(spec["plan"])
    t_e = spec["t_e"]
    inc = Incident(tuple(spec["edges"]), spec["factor"], t_e, t_e + spec["duration_s"])
    safe_plan(inst, sc.net, plan, [inc], t_e)  # untimed: the API warms the kernels at startup
    t0 = time.perf_counter()
    fb, world_fb = safe_plan(inst, sc.net, plan, [inc], t_e)
    simulate_remaining(inst, world_fb.net, fb.states, fb.routes, obj, t_e)
    latency = time.perf_counter() - t0  # safe plan, lean world (what the API streams first)
    world = apply_incident(inst, sc.net, [inc], t_e)  # full world for re-optimisation
    method, seed, budget = spec["method"], spec["seed"], spec["budget_s"]
    trace: list[list[float]] = []
    routes = fb.routes
    first = float("nan")
    prob = build_reopt(inst, world, fb.states, fb.routes, t_e)
    ts = time.perf_counter()
    if method == "b0_fallback" or prob.sub.n == 0:
        routes = fb.routes
    elif method == "b3_pyvrp":
        routes = solve_pyvrp_reopt(prob, budget, seed, t_e)
    else:
        warm = method in ("taqpso_warm", "b2_static") or method.startswith("mu")
        p = prob
        if method == "b2_static":
            tb = prob.sub.tables
            k = int((t_e // tb.slot_s) % tb.n_slots)
            p = replace(
                prob,
                sub=replace(
                    prob.sub,
                    tables=TravelTables.static(tb.tau[:, :, k], tb.dist, tb.slot_s),
                    _cand={},
                ),
            )
        mu = spec.get("mu")
        r = reoptimize(p, cfg, obj, seed, budget, warm=warm, mu=mu)
        routes = p.to_original(r.solution.routes)
        trace = r.trace
        first = trace[0][0] if trace else float("nan")
    solve_s = time.perf_counter() - ts
    m = simulate_remaining(inst, world.net, fb.states, routes, obj, t_e)
    moved, changed = moved_and_changed(fb.routes, routes)
    metrics = {
        **m.as_dict(),
        "fallback_latency_s": latency,
        "affected_pairs": world.affected_pairs,
        "time_first_s": first,
        "solve_s": solve_s,
        "moved": moved,
        "changed_stops": changed,
        "feasible": True,
    }
    rec = RunRecord(
        experiment="e4",
        instance_id=spec["instance"],
        instance_hash=inst.hash(),
        config=cfg.to_dict(),
        config_hash=cfg.hash(),
        solver=method,
        seed=seed,
        budget_s=budget,
        metrics=metrics,
        trace=trace,
        solution={"routes": routes, "t_e": t_e},
        extra={"scenario": spec["scenario"], "mu": spec.get("mu"), "tag": spec.get("tag")},
    )
    save_run(rec)
    return {"J": m.J}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    spec = load_experiment("e4")
    name = spec["instance"]
    sc = load_scenario(name)
    plan = base_plan(name)
    t_e = spec["t_e_h"] * 3600.0
    jobs = []
    for scen, p in spec["scenarios"].items():
        edges = pick_edges(sc, plan, p["k_edges"])
        base = {
            "instance": name,
            "plan": plan,
            "t_e": t_e,
            "edges": list(edges),
            "factor": p["factor"],
            "duration_s": spec["duration_h"] * 3600.0,
            "scenario": scen,
            "budget_s": spec["budget_s"],
        }
        for m in spec["methods"]:
            for s in range(1 if m == "b0_fallback" else spec["seeds"]):
                jobs.append({**base, "method": m, "seed": s})
        for mu in spec["mu_values"]:
            for s in range(spec["mu_seeds"]):
                jobs.append({**base, "method": f"mu{mu}", "seed": s, "mu": mu, "tag": "mu"})
    run_jobs(jobs, fn=run_inc_job)
    analyse(spec)


def analyse(spec: dict[str, Any]) -> None:
    recs = load_runs(experiment="e4")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in recs:
        rows.append(
            {
                "scenario": r.extra["scenario"],
                "method": r.solver,
                "seed": r.seed,
                "mu": r.extra.get("mu"),
                **{k: v for k, v in r.metrics.items() if not isinstance(v, (list, dict))},
                "trace_final": r.trace[-1][1] if r.trace else np.nan,
                "trace": r.trace,
            }
        )
    df = pd.DataFrame(rows)
    out_rows = []
    for scen, g in df[df.mu.isna()].groupby("scenario"):
        b0 = float(g[g.method == "b0_fallback"]["J"].iloc[0])
        best_trace = g["trace_final"].min()
        for m, gm in g.groupby("method"):
            ttw = []
            for tr in gm["trace"]:
                if tr:
                    ttw.append(
                        next((p[0] for p in tr if p[1] <= best_trace * 1.01 + 1e-12), np.nan)
                    )
            q = g[g.method == "taqpso_warm"].sort_values("seed")["J"].to_numpy()
            x = gm.sort_values("seed")["J"].to_numpy()
            out_rows.append(
                {
                    "scenario": scen,
                    "method": m,
                    "n": len(gm),
                    "median_J_rem": gm["J"].median(),
                    "median_T_rem_min": gm["T"].median() / 60,
                    "delta_vs_B0_pct": 100 * (gm["J"].median() - b0) / b0,
                    "median_fallback_latency_s": gm["fallback_latency_s"].median(),
                    "median_time_first_s": gm["time_first_s"].median(),
                    "median_time_within_1pct_s": float(np.nanmedian(ttw)) if ttw else np.nan,
                    "median_moved": gm["moved"].median(),
                    "median_changed_stops": gm["changed_stops"].median(),
                    "A12_taqpso_better": stats.a12(q, x)
                    if m not in ("taqpso_warm", "b0_fallback") and len(q) and len(x)
                    else np.nan,
                    "wilcoxon_p": stats.wilcoxon_p(q[: len(x)], x[: len(q)])
                    if m not in ("taqpso_warm", "b0_fallback") and len(q) == len(x) and len(q) > 4
                    else np.nan,
                }
            )
    pd.DataFrame(out_rows).to_csv(OUT / "table.csv", index=False)
    mu_df = (
        df[df.mu.notna()]
        .groupby(["scenario", "mu"])
        .agg(J=("J", "median"), moved=("moved", "median"))
        .reset_index()
    )
    mu_df.to_csv(OUT / "stability_curve.csv", index=False)
    for scen, g in mu_df.groupby("scenario"):
        plots.line(
            g["moved"].tolist(),
            {"J remaining": g["J"].tolist()},
            OUT,
            f"stability_{scen}",
            f"{scen}: quality vs stability",
            "customers moved",
            "median J (remaining)",
        )
    log.info("wrote %s", OUT)


if __name__ == "__main__":
    main()
