"""Calibrated time-of-day speed profiles (synthetic): 96 x 15-min factors per road class."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from taqpso.config import CONFIG_DIR, load_yaml

LABEL = "Calibrated time-of-day profile (synthetic)"


def _bump(h: float, start: float, end: float, depth: float) -> float:
    """Smooth dip (cosine bell) between start and end hours; 0 outside."""
    if h <= start or h >= end:
        return 0.0
    x = (h - start) / (end - start)
    return float(depth * 0.5 * (1.0 - np.cos(2.0 * np.pi * x)))


def _hourly_profile(hourly: list[float], n_slots: int) -> NDArray[np.float64]:
    """Network-wide ratio per slot: constant within each clock hour (hours are TomTom's bins)."""
    hr = np.asarray(hourly, dtype=np.float64)
    h = np.minimum((np.arange(n_slots) * 24) // n_slots, 23)
    return np.asarray(hr[h], dtype=np.float64)


def class_profile(zone: dict[str, Any], cls: str, n_slots: int = 96) -> NDArray[np.float64]:
    p = zone["profile"]
    sens = p["class_sensitivity"][cls]
    if "hourly_ratio" in p:
        base_h = _hourly_profile(p["hourly_ratio"], n_slots)
        return np.asarray(np.clip(1.0 - sens * (1.0 - base_h), 0.05, 1.0), dtype=np.float64)
    out = np.empty(n_slots)
    for k in range(n_slots):
        h = (k + 0.5) * 24.0 / n_slots
        base = p["night_ratio"]
        if 7.0 < h < 21.5:
            base = min(base, p["midday_ratio"] + (1 - p["midday_ratio"]) * 0.0)
        dip = _bump(
            h,
            p["morning_peak"]["start_h"],
            p["morning_peak"]["end_h"],
            1.0 - p["morning_peak"]["min_ratio"],
        )
        dip = max(
            dip,
            _bump(
                h,
                p["evening_peak"]["start_h"],
                p["evening_peak"]["end_h"],
                1.0 - p["evening_peak"]["min_ratio"],
            ),
        )
        mid = (1.0 - p["midday_ratio"]) if 7.0 < h < 21.5 else 0.0
        out[k] = 1.0 - sens * max(dip, mid)
    return np.clip(out, 0.05, 1.0)


def build_profiles(zone_yaml: str = "delhi_zone.yaml") -> dict[str, list[float]]:
    z = load_yaml(CONFIG_DIR / zone_yaml)
    return {c: class_profile(z, c).tolist() for c in z["road_classes"]}


def write_profiles(path: Path) -> None:
    path.write_text(json.dumps({"label": LABEL, "profiles": build_profiles()}))


def load_profiles(path: Path) -> NDArray[np.float64]:
    """Return array (n_classes, 96) in builder.CLASS_NAMES order."""
    from taqpso.graph.builder import CLASS_NAMES

    d = json.loads(path.read_text())["profiles"]
    return np.asarray([d[c] for c in CLASS_NAMES], dtype=np.float64)


def apply_live_ratios(
    factors: NDArray[np.float64],
    live: dict[str, float],
    now_slot: int,
    hold_slots: int = 4,
    decay_slots: int = 8,
) -> NDArray[np.float64]:
    """Overlay measured current speed ratios on the calibrated profile (live-traffic mode).

    For `hold_slots` slots from `now_slot` the factor equals the live ratio; it then relaxes
    linearly back to the calibrated profile over `decay_slots`. Pure numpy; input not modified.
    The result is still a stepwise speed profile, so IGP and FIFO are unaffected.
    """
    from taqpso.graph.builder import CLASS_NAMES

    out = factors.copy()
    n = out.shape[1]
    for ci, c in enumerate(CLASS_NAMES):
        r = float(np.clip(live.get(c, 1.0), 0.05, 1.0))
        for d in range(hold_slots + decay_slots):
            k = (now_slot + d) % n
            w = 1.0 if d < hold_slots else 1.0 - (d - hold_slots + 1) / (decay_slots + 1)
            out[ci, k] = w * r + (1.0 - w) * factors[ci, k]
    return out
