"""Experiment driver: one (instance, solver, seed) per single-threaded process; scored by sim."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Any

for _v in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import numpy as np  # noqa: E402

from taqpso.config import CONFIG_DIR, load_config, load_yaml, tuned_overrides  # noqa: E402
from taqpso.store.results import RunRecord, save_run  # noqa: E402

log = logging.getLogger(__name__)

SOLVER_CFG: dict[str, dict[str, Any]] = {
    # ablation variants (all use the same runner; only these switches differ)
    "qpso": {},
    "pso": {},
    "ga": {},
    "random": {},
    "qpso_novnd": {"vnd": {"enabled": False}},
    "random_novnd": {"vnd": {"enabled": False}},
    "qpso_nowb": {"write_back": False},
    # the QPSO of the first E2 round: textbook update, alpha 1.0 -> 0.5, full VND on every particle
    "qpso_v1": {
        "swarm": {"size": 12, "alpha_start": 1.0, "alpha_end": 0.5},
        "qpso": {"attractor": "dimension", "space": "key"},
        "vnd": {"gate_tolerance": None},
    },
    "qpso_nogate": {"vnd": {"gate_tolerance": None}},
}
OPT_OF = {
    "qpso_novnd": "qpso",
    "random_novnd": "random",
    "qpso_nowb": "qpso",
    "qpso_v1": "qpso",
    "qpso_nogate": "qpso",
}


def seeds_for(n: int, cfg: Any) -> int:
    return cfg.seeds.small_n if n <= cfg.seeds.small_n_threshold else cfg.seeds.default_n


def _load(name: str) -> Any:
    from taqpso.bench import cvrplib
    from taqpso.bench.make_scenarios import load_scenario

    if name.startswith("delhi"):
        return load_scenario(name)
    inst, bks = cvrplib.load(name)
    return inst, bks


def run_job(spec: dict[str, Any]) -> dict[str, Any]:
    """Execute one job and persist its run record. Top-level so it pickles."""
    from dataclasses import replace

    from taqpso.baselines.pyvrp_adapter import slot_matrix, solve_pyvrp
    from taqpso.core.instance import Instance, TravelTables
    from taqpso.core.objective import Objective, evaluate_solution
    from taqpso.sim.simulator import simulate
    from taqpso.solver.runner import solve

    name, solver, seed, budget = spec["instance"], spec["solver"], spec["seed"], spec["budget_s"]
    # frozen tuned parameters (configs/tuned.yaml) unless this is a tuning job; ablation switches
    # and explicit overrides go on top
    tuned = tuned_overrides(OPT_OF.get(solver, solver)) if spec.get("use_tuned", True) else None
    cfg = load_config(
        *(spec.get("cfg_files") or []), tuned, SOLVER_CFG.get(solver, {}), spec.get("cfg_over")
    )
    loaded = _load(name)
    net = None
    if isinstance(loaded, tuple):
        inst = loaded[0]
    else:
        inst, net = loaded.inst, loaded.net
    if spec.get("depart_h") is not None:
        inst = replace(inst, depart_s=float(spec["depart_h"]) * 3600.0, _cand={})
    obj = Objective.from_instance(inst, cfg, spec.get("preset"))  # scoring objective (TD refs)
    plan_inst = inst
    if spec.get("plan") == "static" and net is not None:  # plan on free-flow tables only
        from taqpso.traffic.pair_tables import build_tables

        free = build_tables(
            net.graph,
            net.pairs,
            np.ones((net.fac.shape[0], net.fac.shape[1])),
            net.slot_s,
            cfg.objective.congestion_ratio_threshold,
        )
        st = TravelTables.static(free.tau[:, :, 0], free.dist, net.slot_s)
        plan_inst = Instance(
            inst.name,
            inst.coords,
            inst.demand,
            inst.Q,
            st,
            inst.service,
            inst.K,
            inst.depart_s,
            dict(inst.meta),
        )
    plan_obj = Objective.from_instance(plan_inst, cfg, spec.get("preset"))
    work: dict[str, int] = {}
    if solver == "pyvrp":
        import time as _t

        t0 = _t.perf_counter()
        sol = solve_pyvrp(plan_inst, budget, seed, slot_matrix(plan_inst))
        elapsed, trace = _t.perf_counter() - t0, []
        feasible = sol.is_feasible(inst)
    else:
        r = solve(
            plan_inst, cfg, OPT_OF.get(solver, solver), seed, budget_s=budget, objective=plan_obj
        )
        sol, elapsed, trace, feasible = r.solution, r.elapsed_s, r.trace, r.feasible
        work = {"iterations": r.iterations, "evaluations": r.evaluations, "full_vnd": r.full_vnd}
    m = simulate(inst, net, sol, obj) if net is not None else evaluate_solution(inst, sol, obj)
    import resource
    import sys

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (
        1e6 if sys.platform == "darwin" else 1e3
    )
    metrics = {
        **m.as_dict(),
        "feasible": bool(feasible),
        "elapsed_s": elapsed,
        "n": inst.n,
        "rss_mb": rss,
        "tables_mb": inst.tables.nbytes / 1e6,
        "tau_mb": inst.tables.tau.nbytes / 1e6,
        **work,
    }
    if net is not None:
        mt = evaluate_solution(inst, sol, obj)
        metrics["table_T"] = mt.T
    if isinstance(loaded, tuple) and loaded[1]:
        metrics["bks"] = loaded[1]
    rec = RunRecord(
        experiment=spec["exp"],
        instance_id=name,
        instance_hash=inst.hash(),
        config=cfg.to_dict(),
        config_hash=cfg.hash(),
        solver=solver,
        seed=seed,
        budget_s=budget,
        metrics=metrics,
        solution={"routes": sol.routes, "depart": inst.depart_s},
        trace=trace,
        extra={k: spec[k] for k in ("plan", "depart_h", "preset", "tag") if k in spec},
    )
    save_run(rec)
    return {"run_id": rec.run_id, **{k: metrics[k] for k in ("T", "J", "feasible")}}


def run_jobs(
    jobs: list[dict[str, Any]], workers: int | None = None, fn: Any = None
) -> list[dict[str, Any]]:
    import multiprocessing as mp

    workers = workers or max(1, (os.cpu_count() or 2) - 2)
    ctx = mp.get_context("spawn")
    out: list[dict[str, Any]] = []
    with ProcessPoolExecutor(workers, mp_context=ctx) as ex:
        for i, r in enumerate(ex.map(fn or run_job, jobs, chunksize=1)):
            out.append(r)
            if (i + 1) % 20 == 0:
                log.info("%d/%d jobs done", i + 1, len(jobs))
    return out


def load_experiment(eid: str) -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "experiments" / f"{eid}.yaml")
