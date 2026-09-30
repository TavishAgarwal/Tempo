"""Standard inertia-weight PSO on keys."""

from __future__ import annotations

import numpy as np

from taqpso.config import Config
from taqpso.solver.keys import reflect_clip
from taqpso.solver.optimizers.base import F64, BaseOptimizer, Swarm


class PSO(BaseOptimizer):
    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg.swarm.size)
        self.p = cfg.pso

    def step(self, swarm: Swarm, progress: float, rng: np.random.Generator) -> F64:
        M, n = swarm.x.shape
        v = swarm.extra.get("v")
        if v is None:
            v = np.zeros((M, n))
        w = self.p.inertia_start + (self.p.inertia_end - self.p.inertia_start) * min(progress, 1.0)
        r1 = rng.random((M, n))
        r2 = rng.random((M, n))
        v = (
            w * v
            + self.p.c1 * r1 * (swarm.pbest - swarm.x)
            + self.p.c2 * r2 * (swarm.gbest - swarm.x)
        )
        v = np.clip(v, -self.p.vmax, self.p.vmax)
        swarm.extra["v"] = v
        return reflect_clip(swarm.x + v)
