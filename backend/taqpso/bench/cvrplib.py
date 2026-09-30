"""CVRPLIB reader (A, B, X sets): rounded Euclidean distances as static travel times."""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

import numpy as np
import vrplib

from taqpso.config import DATA_DIR
from taqpso.core.instance import Instance, TravelTables

log = logging.getLogger(__name__)
RAW = DATA_DIR / "raw" / "cvrplib"


MIRRORS = [
    "https://raw.githubusercontent.com/PyVRP/PyVRP/main/examples/data",
    "https://raw.githubusercontent.com/PyVRP/VRPLIB/main/tests/data",
]


def _download(url: str, dest: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310
            dest.write_bytes(r.read())
        return True
    except OSError:
        return False


def fetch(name: str) -> Path:
    """Download instance (+ BKS file) from public GitHub mirrors (data/ is gitignored)."""
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / f"{name}.vrp"
    if not p.exists():
        if not any(_download(f"{m}/{name}.vrp", p) for m in MIRRORS):
            raise FileNotFoundError(f"cannot download CVRPLIB instance {name}")
    sp = RAW / f"{name}.sol"
    if not sp.exists():
        any(_download(f"{m}/{name}.sol", sp) for m in MIRRORS)
    return p


def load(name: str) -> tuple[Instance, float | None]:
    """Return (Instance, best-known cost or None)."""
    p = fetch(name)
    d = vrplib.read_instance(str(p))
    xy = np.asarray(d["node_coord"], dtype=np.float64)
    dist = np.rint(np.linalg.norm(xy[:, None] - xy[None], axis=2))
    inst = Instance(
        name,
        xy,
        np.asarray(d["demand"], dtype=np.int32),
        int(d["capacity"]),
        TravelTables.static(dist),
    )
    bks = None
    sp = RAW / f"{name}.sol"
    if sp.exists():
        bks = float(vrplib.read_solution(str(sp))["cost"])
    return inst, bks
