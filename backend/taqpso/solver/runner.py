"""Anytime loop shared by every key-based optimizer (steps 1-5 and 7; step 6 is the optimizer)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from taqpso.config import Config
from taqpso.core.fleet import Fleet
from taqpso.core.instance import Instance
from taqpso.core.objective import Metrics, Objective, evaluate_solution
from taqpso.core.solution import Solution
from taqpso.solver.keys import decode_order, write_back
from taqpso.solver.optimizers import Optimizer, get_optimizer
from taqpso.solver.optimizers.base import Swarm
from taqpso.solver.seeds import nearest_neighbour, sweep_tour, tour_to_keys
from taqpso.solver.split import max_route_len, split
from taqpso.solver.split_fleet import split_fleet, split_vehicles
from taqpso.solver.vnd import array_to_tour, cuts_to_array, improve_arrays

log = logging.getLogger(__name__)

# (elapsed s, J, solution, diversity)
INFEASIBLE_FIT = 1e6
ImprovementCb = Callable[[float, float, Solution, float], None]


@dataclass
class RunResult:
    solution: Solution
    metrics: Metrics
    J: float
    feasible: bool
    iterations: int
    evaluations: int
    elapsed_s: float
    trace: list[list[float]] = field(default_factory=list)  # [t, J, T]
    full_vnd: int = 0  # evaluations that ran the full VND (the rest stopped after the light pass)


class Runner:
    def __init__(
        self,
        inst: Instance,
        cfg: Config,
        optimizer: Optimizer,
        rng: np.random.Generator,
        objective: Objective | None = None,
        on_improvement: ImprovementCb | None = None,
        extra_seeds: list[np.ndarray] | None = None,
        fleet: Fleet | None = None,
        prev_assign: np.ndarray | None = None,
        mu: float = 0.0,
        default_seeds: bool = True,
    ) -> None:
        self.inst = inst
        self.cfg = cfg
        self.opt = optimizer
        self.rng = rng
        self.obj = objective or Objective.from_instance(inst, cfg)
        self.cw = self.obj.cw
        self.cb = on_improvement
        self.B = max_route_len(inst)
        self.L = self.B + 1
        self.extra_seeds = extra_seeds or []
        self.fleet = fleet
        self.prev_assign = prev_assign
        self.mu = mu
        self.default_seeds = default_seeds
        self.best: Solution | None = None
        self.best_J = float("inf")
        self.best_any: Solution | None = None  # best even if fleet-infeasible
        self.best_any_J = float("inf")
        self.trace: list[list[float]] = []
        self.t0 = 0.0
        self.evals = 0
        self.full_vnd = 0

    # ---- steps 1-4 for one particle -------------------------------------------------------
    def evaluate(
        self, keys: np.ndarray, ref_cost: float = float("inf")
    ) -> tuple[np.ndarray, float, Solution | None, int]:
        """Steps 1-4. ref_cost (the particle's pbest cost) drives the VND gate."""
        inst, cfg = self.inst, self.cfg
        tour = decode_order(keys)
        excess = 0
        fl = self.fleet
        if fl is not None:
            cuts_all, cost = split_vehicles(tour, inst, self.cw, fl, self.B)
            if not np.isfinite(cost) or cost >= 1e299:
                return keys, INFEASIBLE_FIT, None, 1
            cuts = cuts_all[:-1]
        elif inst.K is None:
            cuts, cost = split(tour, inst, self.cw, self.B)
        else:
            cuts, cost, excess = split_fleet(tour, inst, self.cw, inst.K, self.B)
        routes, lens = cuts_to_array(tour, cuts, self.L)
        if cfg.vnd.enabled:
            v = cfg.vnd
            order = (self.rng.permutation(inst.n) + 1).astype(np.int32)

            def vnd(names: list[str], passes: int) -> float:
                return improve_arrays(
                    routes, lens, inst, self.cw, order, v.candidate_k, names, passes, fl
                )

            if v.gate_tolerance is None or not np.isfinite(ref_cost):
                cost = vnd(v.neighbourhoods, v.max_passes)
                self.full_vnd += 1
            else:  # light pass for everyone, full VND only where it looks worth the time
                cost = vnd(v.light_neighbourhoods, v.light_passes)
                if cost <= ref_cost * (1.0 + v.gate_tolerance):
                    cost = vnd(v.neighbourhoods, v.max_passes)
                    self.full_vnd += 1
        tour2 = array_to_tour(routes, lens)
        new_keys = write_back(keys, tour2) if cfg.write_back else keys
        rl = [[int(c) for c in routes[r, : lens[r]]] for r in range(len(lens))]
        if fl is not None:
            sol = Solution(rl)  # vehicle slots preserved (empty routes kept)
            if self.mu and self.prev_assign is not None:
                cost += self.mu * float(self._changed(rl))
        else:
            sol = Solution(rl).compact()
            excess = max(0, sol.n_routes - inst.K) if inst.K is not None else 0
        return new_keys, float(cost), sol, excess

    def _changed(self, routes: list[list[int]]) -> int:
        assert self.prev_assign is not None
        return sum(1 for v, r in enumerate(routes) for c in r if self.prev_assign[c] not in (-1, v))

    def best_so_far(self) -> tuple[Solution | None, float]:
        if self.best is not None:
            return self.best, self.best_J
        return self.best_any, self.best_any_J

    def _record(self, sol: Solution, J: float, feasible: bool, swarm: Swarm | None) -> None:
        t = time.perf_counter() - self.t0
        if feasible:
            if J < self.best_J - 1e-12:
                self.best, self.best_J = sol, J
                m = evaluate_solution(self.inst, sol, self.obj)
                self.trace.append([t, J, m.T])
                if self.cb:
                    div = float(swarm.pbest.std(axis=0).mean()) if swarm is not None else 0.0
                    self.cb(t, J, sol, div)
        elif J < self.best_any_J:
            self.best_any, self.best_any_J = sol, J

    def run(
        self,
        budget_s: float | None = None,
        max_iters: int | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> RunResult:
        inst, cfg = self.inst, self.cfg
        if budget_s is None and max_iters is None:
            budget_s = cfg.budget_s.default
        n = inst.n
        seeds = (
            [tour_to_keys(self._seed_tour_nn()), tour_to_keys(sweep_tour(inst))]
            if self.default_seeds
            else []
        )
        seeds += [np.asarray(s, dtype=np.float64) for s in self.extra_seeds]
        swarm = self.opt.init(n, self.rng, seeds)
        pen = cfg.objective.excess_vehicle_penalty
        self.t0 = time.perf_counter()
        it = 0
        stall = 0
        M = swarm.size
        while True:
            improved_g = False
            for i in range(M):
                if (
                    budget_s is not None and it > 0 and time.perf_counter() - self.t0 >= budget_s
                ) or (
                    should_stop is not None and self.best_so_far()[0] is not None and should_stop()
                ):
                    return self._finish(it)
                keys, cost, sol, excess = self.evaluate(swarm.x[i], swarm.pbest_cost[i])
                self.evals += 1
                fit = cost + pen * excess
                swarm.x[i] = keys
                swarm.cost[i] = fit
                if fit < swarm.pbest_cost[i]:
                    swarm.pbest_cost[i] = fit
                    swarm.pbest[i] = keys
                if fit < swarm.gbest_cost - 1e-12:
                    swarm.gbest_cost = fit
                    swarm.gbest = keys.copy()
                    improved_g = True
                if sol is not None:
                    self._record(sol, cost, excess == 0, swarm)
            it += 1
            if max_iters is not None and it >= max_iters:
                return self._finish(it)
            if budget_s is not None and time.perf_counter() - self.t0 >= budget_s:
                return self._finish(it)
            stall = 0 if improved_g else stall + 1
            if stall >= cfg.stall.iterations:  # step 7: re-randomise the worst particles
                k = max(1, round(cfg.stall.reinit_fraction * M))
                worst = np.argsort(-swarm.pbest_cost, kind="stable")[:k]
                fresh = self.rng.random((k, n))
                swarm.pbest[worst] = fresh
                swarm.pbest_cost[worst] = np.inf
                swarm.x[worst] = fresh
                stall = 0
            else:  # step 6: optimizer update
                new_x = self.opt.step(swarm, self._progress(it, max_iters, budget_s), self.rng)
                assert np.isfinite(new_x).all() and new_x.min() >= 0.0 and new_x.max() <= 1.0
                swarm.x = new_x

    def _progress(self, it: int, max_iters: int | None, budget_s: float | None) -> float:
        if budget_s is not None:
            return (time.perf_counter() - self.t0) / budget_s
        assert max_iters is not None
        return it / max_iters

    def _seed_tour_nn(self) -> np.ndarray:
        return nearest_neighbour(self.inst).giant_tour()

    def _finish(self, it: int) -> RunResult:
        sol, J = self.best_so_far()
        assert sol is not None
        feasible = self.best is not None
        if feasible:
            sol.validate(self.inst)
        if self.fleet is None:
            m = evaluate_solution(self.inst, sol, self.obj)
        else:  # per-vehicle start states: callers score with the dynamic simulator
            m = Metrics(0.0, 0.0, 0.0, J, sol.n_routes)
        return RunResult(
            sol,
            m,
            J,
            feasible,
            it,
            self.evals,
            time.perf_counter() - self.t0,
            self.trace,
            self.full_vnd,
        )


def solve(
    inst: Instance,
    cfg: Config,
    solver: str = "qpso",
    seed: int = 0,
    budget_s: float | None = None,
    max_iters: int | None = None,
    on_improvement: ImprovementCb | None = None,
    objective: Objective | None = None,
) -> RunResult:
    rng = np.random.Generator(np.random.PCG64(seed))
    runner = Runner(inst, cfg, get_optimizer(solver, cfg), rng, objective, on_improvement)
    return runner.run(budget_s, max_iters)
