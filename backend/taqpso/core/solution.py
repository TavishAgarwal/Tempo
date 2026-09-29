"""Solution = list of routes (customer ids); validation per FR1."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from taqpso.core.instance import Instance


class InfeasibleSolution(ValueError):
    pass


@dataclass
class Solution:
    routes: list[list[int]]
    meta: dict[str, object] = field(default_factory=dict)

    def giant_tour(self) -> NDArray[np.int32]:
        flat = [c for r in self.routes for c in r]
        return np.asarray(flat, dtype=np.int32)

    @staticmethod
    def from_giant_tour(tour: NDArray[np.int32], cuts: list[int]) -> Solution:
        """cuts: start indices of each route in the giant tour."""
        bounds = [*cuts, len(tour)]
        return Solution(
            [[int(c) for c in tour[a:b]] for a, b in zip(bounds[:-1], bounds[1:], strict=True)]
        )

    @property
    def n_routes(self) -> int:
        return sum(1 for r in self.routes if r)

    def compact(self) -> Solution:
        return Solution([r for r in self.routes if r], dict(self.meta))

    def loads(self, inst: Instance) -> list[int]:
        return [int(inst.demand[r].sum()) if r else 0 for r in self.routes]

    def validate(self, inst: Instance) -> None:
        """FR1: each customer exactly once, load <= Q, K respected."""
        seen = np.zeros(inst.n + 1, dtype=np.int32)
        for r in self.routes:
            for c in r:
                if c < 1 or c > inst.n:
                    raise InfeasibleSolution(f"Unknown customer id {c}")
                seen[c] += 1
        if (seen[1:] > 1).any():
            raise InfeasibleSolution(f"Customer {int(np.argmax(seen[1:] > 1)) + 1} visited twice")
        if (seen[1:] < 1).any():
            raise InfeasibleSolution(f"Customer {int(np.argmax(seen[1:] < 1)) + 1} not visited")
        for i, ld in enumerate(self.loads(inst)):
            if ld > inst.Q:
                raise InfeasibleSolution(f"Route {i} load {ld} exceeds capacity {inst.Q}")
        if inst.K is not None and self.n_routes > inst.K:
            raise InfeasibleSolution(f"Uses {self.n_routes} vehicles, fleet limit is {inst.K}")

    def is_feasible(self, inst: Instance) -> bool:
        try:
            self.validate(inst)
        except InfeasibleSolution:
            return False
        return True
