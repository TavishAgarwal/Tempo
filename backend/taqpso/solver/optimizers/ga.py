"""Random-key GA (BRKGA style): elites, biased uniform crossover, random mutants."""

from __future__ import annotations

import numpy as np

from taqpso.config import Config
from taqpso.solver.optimizers.base import F64, BaseOptimizer, Swarm


class GA(BaseOptimizer):
    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg.swarm.size)
        self.p = cfg.ga

    def step(self, swarm: Swarm, progress: float, rng: np.random.Generator) -> F64:
        M, n = swarm.x.shape
        order = np.argsort(swarm.cost, kind="stable")
        pop = swarm.x[order]
        n_el = max(1, int(np.ceil(self.p.elite_fraction * M)))
        n_mut = max(0, int(np.ceil(self.p.mutant_fraction * M)))
        n_off = max(0, M - n_el - n_mut)
        new = np.empty_like(pop)
        new[:n_el] = pop[:n_el]
        for k in range(n_off):
            e = pop[rng.integers(0, n_el)]
            o = pop[rng.integers(n_el, M)] if n_el < M else pop[rng.integers(0, M)]
            take = rng.random(n) < self.p.inherit_prob
            new[n_el + k] = np.where(take, e, o)
        new[n_el + n_off :] = rng.random((M - n_el - n_off, n))
        return new
