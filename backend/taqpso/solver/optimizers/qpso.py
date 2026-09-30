"""Quantum-inspired PSO sampling rule (classical computation)."""

from __future__ import annotations

import numpy as np

from taqpso.config import Config
from taqpso.solver.keys import reflect_clip
from taqpso.solver.optimizers.base import F64, BaseOptimizer, Swarm


def to_ranks(x: F64) -> F64:
    """Keys -> normalised ranks in [0,1] along the last axis; decodes to the same tour."""
    n = x.shape[-1]
    r = np.argsort(np.argsort(x, axis=-1, kind="stable"), axis=-1, kind="stable")
    out: F64 = r.astype(np.float64) / max(n - 1, 1)
    return out


class QPSO(BaseOptimizer):
    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg.swarm.size)
        self.a0 = cfg.swarm.alpha_start
        self.a1 = cfg.swarm.alpha_end
        self.u_floor = cfg.qpso.u_floor
        self.per_particle = cfg.qpso.attractor == "particle"
        self.rank = cfg.qpso.space == "rank"

    def step(self, swarm: Swarm, progress: float, rng: np.random.Generator) -> F64:
        M, n = swarm.x.shape
        alpha = self.a0 + (self.a1 - self.a0) * min(max(progress, 0.0), 1.0)
        x, pbest, gbest = swarm.x, swarm.pbest, swarm.gbest
        if self.rank:
            x, pbest, gbest = to_ranks(x), to_ranks(pbest), to_ranks(gbest)
        mbest = pbest.mean(axis=0)
        phi = rng.random((M, 1) if self.per_particle else (M, n))
        P = phi * pbest + (1.0 - phi) * gbest
        u = np.maximum(rng.random((M, n)), self.u_floor)
        sign = np.where(rng.random((M, n)) < 0.5, 1.0, -1.0)
        x = P + sign * alpha * np.abs(mbest - x) * np.log(1.0 / u)
        x = reflect_clip(x)
        assert np.isfinite(x).all()
        return x
