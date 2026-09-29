"""Problem instance: depot 0, customers 1..n, travel tables (static = one slot)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

F32 = NDArray[np.float32]
F64 = NDArray[np.float64]
I32 = NDArray[np.int32]


@dataclass
class TravelTables:
    """tau/cong: (N,N,S) seconds at slot-start departures; dist: (N,N) metres.

    A static instance is the single-slot special case (S = 1).
    """

    tau: F32
    dist: F32
    cong: F32
    slot_s: float = 900.0

    @property
    def n_slots(self) -> int:
        return int(self.tau.shape[2])

    @property
    def nbytes(self) -> int:
        return int(self.tau.nbytes + self.dist.nbytes + self.cong.nbytes)

    @staticmethod
    def static(
        tau2d: NDArray[np.float64] | NDArray[np.float32],
        dist2d: NDArray[np.float64] | NDArray[np.float32] | None = None,
        slot_s: float = 900.0,
    ) -> TravelTables:
        t = np.ascontiguousarray(tau2d, dtype=np.float32)[:, :, None]
        d = np.ascontiguousarray(tau2d if dist2d is None else dist2d, dtype=np.float32)
        return TravelTables(t, d, np.zeros_like(t), slot_s)


NO_DUE = 1e18


class InstanceError(ValueError):
    pass


@dataclass
class Instance:
    name: str
    coords: F64  # (N,2) x,y or lon,lat (display only for TD)
    demand: I32  # (N,), depot demand 0
    Q: int
    tables: TravelTables
    service: F32 = field(default_factory=lambda: np.zeros(0, dtype=np.float32))
    K: int | None = None
    depart_s: float = 0.0
    meta: dict[str, object] = field(default_factory=dict)
    n_virtual: int = 0  # trailing table nodes that are vehicle start points, not customers
    tw: NDArray[np.float64] | None = None  # (N,2) [ready, due] seconds; None = no time windows
    _cand: dict[int, I32] = field(default_factory=dict, repr=False)
    _sv: NDArray[np.float64] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.demand = np.ascontiguousarray(self.demand, dtype=np.int32)
        N = self.demand.shape[0]
        if self.service.shape[0] != N:
            self.service = np.zeros(N, dtype=np.float32)
        else:
            self.service = np.ascontiguousarray(self.service, dtype=np.float32)
        self.validate()

    @property
    def has_tw(self) -> bool:
        return self.tw is not None

    @property
    def sv(self) -> NDArray[np.float64]:
        """(N,3) kernel view: [service, ready, due]. No time windows -> [0, 1e18] (never binds).

        Row 0 (depot) column 1 is a flag: 1.0 when time windows are active, else 0.0.
        """
        if self._sv is None:
            N = self.demand.shape[0]
            a = np.zeros((N, 3), dtype=np.float64)
            a[:, 0] = self.service
            a[:, 2] = NO_DUE
            if self.tw is not None:
                a[:, 1:3] = np.asarray(self.tw, dtype=np.float64)
                a[0, 1] = 1.0  # depot ready is unused; kernels read it as the 'TW active' flag
            self._sv = a
        return self._sv

    @property
    def n(self) -> int:
        return int(self.demand.shape[0] - 1 - self.n_virtual)

    def validate(self) -> None:
        N = self.demand.shape[0]
        if self.tables.tau.shape[0] != N or self.tables.tau.shape[1] != N:
            raise InstanceError("Travel table size does not match customer count")
        over = np.nonzero(self.demand > self.Q)[0]
        if over.size:
            raise InstanceError(f"Demand exceeds capacity at customer {int(over[0])}")
        if self.demand[0] != 0:
            raise InstanceError("Depot demand must be 0")

    def candidates(self, k: int) -> I32:
        """k nearest customers by travel time at the departure slot (granular lists)."""
        if k in self._cand:
            return self._cand[k]
        N = self.n + 1
        t = self.tables
        slot = int((self.depart_s // t.slot_s) % t.n_slots) if t.n_slots > 1 else 0
        m = t.tau[:, :, slot].astype(np.float64).copy()
        m = m + m.T  # symmetric proximity
        np.fill_diagonal(m, np.inf)
        m[:, 0] = np.inf  # depot is not a neighbour
        if self.n_virtual:
            m[:, self.n + 1 :] = np.inf
        kk = min(k, max(self.n - 1, 1))
        order = np.argsort(m, axis=1, kind="stable")[:, :kk]
        cand = np.ascontiguousarray(order.astype(np.int32))
        cand[0, :] = 0
        if N <= 1:
            cand = np.zeros((N, 1), dtype=np.int32)
        self._cand[k] = cand
        return cand

    def hash(self) -> str:
        h = hashlib.sha256()
        for a in (self.coords, self.demand, self.service, self.tables.tau, self.tables.dist):
            h.update(np.ascontiguousarray(a).tobytes())
        if self.tw is not None:
            h.update(np.ascontiguousarray(self.tw, dtype=np.float64).tobytes())
        h.update(repr((self.Q, self.K, self.depart_s, self.tables.slot_s)).encode())
        return h.hexdigest()[:16]
