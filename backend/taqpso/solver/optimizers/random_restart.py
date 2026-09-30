"""Random restart: fresh uniform keys every step (global best kept by the runner)."""

from __future__ import annotations

import numpy as np

from taqpso.config import Config
from taqpso.solver.optimizers.base import F64, BaseOptimizer, Swarm


class RandomRestart(BaseOptimizer):
    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg.swarm.size)

    def step(self, swarm: Swarm, progress: float, rng: np.random.Generator) -> F64:
        return np.asarray(rng.random(swarm.x.shape), dtype=np.float64)
