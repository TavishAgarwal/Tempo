"""Speed-based emissions (Phase 8, F18): COPERT-form emission factor integrated along paths.

Pure/Numba. `p` = [a, b, c, d, e, v_min, v_max] from `taqpso.config.load_emission_params`
(`configs/emissions.yaml`). The shipped coefficients are illustrative, not COPERT-calibrated.
"""

from __future__ import annotations

from numba import njit

from taqpso.traffic.igp import edge_time


@njit(cache=True)
def emission_factor(v_kmph, p):  # type: ignore[no-untyped-def]
    """g/km at mean speed v (clamped to the validity range)."""
    v = min(max(v_kmph, p[5]), p[6])
    return (p[0] + p[2] * v + p[4] * v * v) / (1.0 + p[1] * v + p[3] * v * v)


@njit(cache=True)
def path_emissions(edges, length, v0, cls_fac, road_class, t0, slot_s, p):  # type: ignore[no-untyped-def]
    """Grams emitted along a path entered at t0; per-edge mean speed = length / IGP time."""
    t = t0
    g = 0.0
    for q in range(edges.shape[0]):
        e = edges[q]
        row = cls_fac[road_class[e]] if road_class.shape[0] > 0 else cls_fac[e]
        dt = edge_time(length[e], v0[e], row, t, slot_s)
        v_kmph = 3.6 * length[e] / max(dt, 1e-9)
        g += emission_factor(v_kmph, p) * length[e] / 1000.0
        t += dt
    return g
