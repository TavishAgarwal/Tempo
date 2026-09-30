"""Optimizer plug-in point: step 6 of the loop only. Everything else lives in runner.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]


@dataclass
class Swarm:
    x: F64  # (M, n) current keys (already written back after VND)
    cost: F64  # (M,) cost of the current keys
    pbest: F64  # (M, n)
    pbest_cost: F64  # (M,)
    gbest: F64  # (n,)
    gbest_cost: float
    extra: dict[str, Any] = field(default_factory=dict)  # optimizer-private state

    @property
    def size(self) -> int:
        return int(self.x.shape[0])


class Optimizer(Protocol):
    def init(self, n: int, rng: np.random.Generator, seeds: list[F64]) -> Swarm: ...

    def step(self, swarm: Swarm, progress: float, rng: np.random.Generator) -> F64:
        """Return the next keys (M x n) in [0,1]."""
        ...


class BaseOptimizer:
    """Shared initialisation (seed particles first, then uniform random keys)."""

    def __init__(self, size: int) -> None:
        self.size = size

    def init(self, n: int, rng: np.random.Generator, seeds: list[F64]) -> Swarm:
        M = self.size
        x = rng.random((M, n))
        for i, s in enumerate(seeds[:M]):
            x[i] = s
        return Swarm(
            x=x.copy(),
            cost=np.full(M, np.inf),
            pbest=x.copy(),
            pbest_cost=np.full(M, np.inf),
            gbest=x[0].copy(),
            gbest_cost=float("inf"),
        )
