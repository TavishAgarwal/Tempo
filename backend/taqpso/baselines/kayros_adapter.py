"""KAYROS reference runs on Poryos2026 (Phase 8, F20). Baseline only, MIT-licensed `kayros` package.

Never called from inside TA-QPSO (rules.md). KAYROS works on the official instance file and prices
its own solutions with the reference checker; we additionally re-score with `official_cost` so every
solver goes through the same checker.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class KayrosResult:
    routes: list[list[int]]
    duration: float
    trace: list[tuple[float, float]]  # (seconds, best duration) per incumbent
    version: str
    note: str = ""  # e.g. kayros' own final check failed and the last incumbent was used instead


def solve_kayros(path: str | Path, time_limit_s: float, seed: int = 0) -> KayrosResult:
    import kayros

    trace: list[tuple[float, float]] = []
    last: list[list[int]] = []

    def hook(inc, routes):  # type: ignore[no-untyped-def]
        trace.append((float(inc.seconds), float(inc.value)))
        last[:] = [[int(c) for c in r] for r in routes]

    try:
        sol = kayros.solve(str(path), time_limit=time_limit_s, seed=seed, on_incumbent=hook)
    except kayros.KayrosError as e:
        # kayros 1.6.0 occasionally rejects its own solution at ulp level against the checker
        # (td-fold/2 contract); fall back to its last streamed incumbent and say so.
        if not last:
            raise
        return KayrosResult(last, trace[-1][1], trace, str(kayros.version), f"kayros error: {e}")
    return KayrosResult(
        [[int(c) for c in r] for r in sol.routes], float(sol.duration), trace, str(kayros.version)
    )
