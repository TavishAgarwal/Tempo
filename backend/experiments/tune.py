"""Tune each optimizer on the tuning instances (never on test): grid over common + own axes."""

from __future__ import annotations

import itertools
import logging
from typing import Any

import numpy as np
import yaml

from experiments.driver import load_experiment, run_jobs
from taqpso.config import CONFIG_DIR, deep_merge
from taqpso.store.results import load_runs

log = logging.getLogger("tune")


def _axis_overrides(axis: dict[str, Any]) -> list[dict[str, Any]]:
    """An axis is {path: [section, key], values: [...]} or {values: [override dict, ...]}."""
    if "path" not in axis:
        return [dict(v) for v in axis["values"]]
    sec, key = axis["path"]
    return [{sec: {key: v}} for v in axis["values"]]


def grid(t: dict[str, Any], opt: str) -> list[dict[str, Any]]:
    axes = [*t["common_axes"], *(t["own_axes"].get(opt) or [])]
    out = []
    for combo in itertools.product(*(_axis_overrides(a) for a in axes)):
        over: dict[str, Any] = {}
        for part in combo:
            over = deep_merge(over, part)
        out.append(over)
    return out


def main(select_only: bool = False) -> None:
    logging.basicConfig(level=logging.INFO)
    t = load_experiment("tuning")
    for eid in ("e2", "e2_large"):
        test = load_experiment(eid)["instances"]
        assert not set(t["instances"]) & set(test), f"tuning set must be disjoint from {eid}"
    grids = {opt: grid(t, opt) for opt in t["own_axes"]}
    if not select_only:
        run_jobs(_missing_jobs(t, grids))
    select(t, grids)


def _missing_jobs(
    t: dict[str, Any], grids: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Every grid job without a saved run record (so an interrupted tuning run resumes)."""
    done = {(r.extra["tag"], r.instance_id, r.seed) for r in load_runs(experiment="tuning")}
    jobs = []
    for opt, overs in grids.items():
        for i, over in enumerate(overs):
            for inst in t["instances"]:
                for seed in range(t["seeds"]):
                    if (f"{opt}|{i}", inst, 1000 + seed) in done:
                        continue
                    jobs.append(
                        {
                            "exp": "tuning",
                            "instance": inst,
                            "solver": opt,
                            "seed": 1000 + seed,
                            "budget_s": t.get("budgets", {}).get(inst, t["budget_s"]),
                            "cfg_over": over,
                            "use_tuned": False,
                            "tag": f"{opt}|{i}",
                        }
                    )
    log.info("%d tuning jobs to run", len(jobs))
    return jobs


def select(t: dict[str, Any], grids: dict[str, list[dict[str, Any]]]) -> None:
    """Score = mean over instances of the config's median relative gap to the best run on that
    instance, so every tuning instance counts equally (a pooled median would be decided by the
    small instances, where most configs tie); ties broken by the median time of the last
    improvement."""
    runs = load_runs(experiment="tuning")
    best_J = {i: min(r.metrics["J"] for r in runs if r.instance_id == i) for i in t["instances"]}
    gap: dict[tuple[str, str], list[float]] = {}
    when: dict[str, list[float]] = {}
    for r in runs:
        tag = r.extra["tag"]
        gap.setdefault((tag, r.instance_id), []).append(r.metrics["J"] / best_J[r.instance_id] - 1)
        when.setdefault(tag, []).append(r.trace[-1][0] if r.trace else r.metrics["elapsed_s"])
    best: dict[str, dict[str, Any]] = {}
    for opt, overs in grids.items():
        tags = [f"{opt}|{i}" for i in range(len(overs)) if f"{opt}|{i}" in when]
        key = {
            k: (
                round(float(np.mean([np.median(gap[(k, i)]) for i in t["instances"]])), 5),
                float(np.median(when[k])),
            )
            for k in tags
        }
        tag = min(tags, key=key.__getitem__)
        best[opt] = overs[int(tag.split("|")[1])]
        log.info(
            "%s -> %s (mean of per-instance median gaps %.3f%%, t_last %.2f s)",
            opt,
            best[opt],
            100 * key[tag][0],
            key[tag][1],
        )
    (CONFIG_DIR / "tuned.yaml").write_text(yaml.safe_dump(best))


if __name__ == "__main__":
    import sys

    main(select_only="--select-only" in sys.argv)
