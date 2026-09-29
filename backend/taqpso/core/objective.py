"""T (primary), D, C and the normalised objective J (rules.md Modelling)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from taqpso.config import Config
from taqpso.core.evaluate import route_components
from taqpso.core.instance import Instance
from taqpso.core.solution import Solution


@dataclass(frozen=True)
class Metrics:
    T: float  # total driving time (s)
    D: float  # distance (m)
    C: float  # congestion exposure (s on edges slower than threshold * free-flow)
    J: float
    K: int
    route_T: tuple[float, ...] = ()
    route_load: tuple[int, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "T": self.T,
            "D": self.D,
            "C": self.C,
            "J": self.J,
            "K": self.K,
            "route_T": list(self.route_T),
            "route_load": list(self.route_load),
        }


@dataclass(frozen=True)
class Objective:
    """J = w_T T/T_ref + w_D D/D_ref + w_C C/C_ref ; refs from the nearest-neighbour solution."""

    w_T: float
    w_D: float
    w_C: float
    T_ref: float
    D_ref: float
    C_ref: float

    @property
    def cw(self) -> NDArray[np.float64]:
        """Per-unit coefficients (a_T, a_D, a_C) used inside kernels."""
        return np.array(
            [self.w_T / self.T_ref, self.w_D / self.D_ref, self.w_C / self.C_ref],
            dtype=np.float64,
        )

    def J(self, T: float, D: float, C: float) -> float:
        a = self.cw
        return float(a[0] * T + a[1] * D + a[2] * C)

    @staticmethod
    def from_instance(inst: Instance, cfg: Config, preset: str | None = None) -> Objective:
        from taqpso.solver.seeds import nearest_neighbour

        w = cfg.objective.presets[preset or cfg.objective.preset]
        nn = nearest_neighbour(inst)
        T, D, C = raw_components(inst, nn)
        T_ref = max(T, 1e-9)
        D_ref = max(D, 1e-9)
        C_ref = max(C, cfg.objective.c_ref_floor_fraction * T_ref)
        return Objective(w.w_T, w.w_D, w.w_C, T_ref, D_ref, C_ref)

    def with_weights(self, w_T: float, w_D: float, w_C: float) -> Objective:
        return Objective(w_T, w_D, w_C, self.T_ref, self.D_ref, self.C_ref)


def raw_components(inst: Instance, sol: Solution) -> tuple[float, float, float]:
    tb = inst.tables
    T = D = C = 0.0
    for r in sol.routes:
        if not r:
            continue
        arr = np.asarray(r, dtype=np.int32)
        t, d, c = route_components(
            arr, len(arr), tb.tau, tb.dist, tb.cong, inst.sv, inst.depart_s, tb.slot_s
        )
        T += t
        D += d
        C += c
    return T, D, C


def evaluate_solution(inst: Instance, sol: Solution, obj: Objective) -> Metrics:
    tb = inst.tables
    T = D = C = 0.0
    rT: list[float] = []
    for r in sol.routes:
        if not r:
            continue
        arr = np.asarray(r, dtype=np.int32)
        t, d, c = route_components(
            arr, len(arr), tb.tau, tb.dist, tb.cong, inst.sv, inst.depart_s, tb.slot_s
        )
        T += t
        D += d
        C += c
        rT.append(t)
    loads = tuple(int(inst.demand[r].sum()) for r in sol.routes if r)
    return Metrics(T, D, C, obj.J(T, D, C), len(rT), tuple(rT), loads)
