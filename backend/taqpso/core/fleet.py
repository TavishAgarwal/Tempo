"""Per-vehicle start states (node, time, remaining capacity). Depot fleet = all start at depot."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass
class Fleet:
    snode: NDArray[np.int32]  # start node of each vehicle (0 = depot)
    stime: NDArray[np.float64]  # time the vehicle is ready at that node
    cap: NDArray[np.int64]  # capacity available for the customers still to be served

    @property
    def size(self) -> int:
        return int(self.snode.shape[0])

    @staticmethod
    def depot(R: int, depart_s: float, Q: int) -> Fleet:
        return Fleet(
            np.zeros(R, dtype=np.int32),
            np.full(R, depart_s, dtype=np.float64),
            np.full(R, Q, dtype=np.int64),
        )
