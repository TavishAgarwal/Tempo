"""TomTom Traffic Flow Segment Data adapter (Phase 8 live-traffic mode, F17).

I/O module (network): lives in bench/ per rules.md. The API key is read from the environment
(TOMTOM_API_KEY) only and is never logged or written to disk.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from taqpso.config import CONFIG_DIR, DATA_DIR, load_yaml

log = logging.getLogger(__name__)
LABEL = "Live traffic (TomTom Flow Segment Data)"
URL = (
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/{zoom}/json"
    "?point={lat:.6f},{lon:.6f}&unit=KMPH&key={key}"
)
# TomTom functional road class -> our road class (graph/builder.CLASS_NAMES)
FRC_TO_CLASS = {
    "FRC0": "motorway",
    "FRC1": "trunk",
    "FRC2": "primary",
    "FRC3": "secondary",
    "FRC4": "tertiary",
    "FRC5": "residential",
    "FRC6": "residential",
    "FRC7": "other",
}


class TomTomError(RuntimeError):
    pass


@dataclass
class FlowSample:
    lat: float
    lon: float
    frc: str
    current_kmph: float
    freeflow_kmph: float
    confidence: float
    road_closure: bool

    @property
    def ratio(self) -> float:
        return self.current_kmph / self.freeflow_kmph if self.freeflow_kmph > 0 else 1.0


def api_key() -> str:
    key = os.environ.get("TOMTOM_API_KEY", "").strip()
    if not key:
        raise TomTomError("TOMTOM_API_KEY is not set (put it in .env and export it)")
    return key


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env reader (no extra dependency); existing environment variables win."""
    p = path or DATA_DIR.parent / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def parse_flow(lat: float, lon: float, payload: dict[str, Any]) -> FlowSample:
    d = payload["flowSegmentData"]
    return FlowSample(
        lat,
        lon,
        str(d.get("frc", "FRC7")),
        float(d["currentSpeed"]),
        float(d["freeFlowSpeed"]),
        float(d.get("confidence", 0.0)),
        bool(d.get("roadClosure", False)),
    )


def fetch_point(lat: float, lon: float, key: str, zoom: int = 10, retries: int = 2) -> FlowSample:
    url = URL.format(zoom=zoom, lat=lat, lon=lon, key=key)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310 (fixed https host)
                return parse_flow(lat, lon, json.load(r))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise TomTomError(f"TomTom rejected the key (HTTP {e.code})") from None
            if e.code == 429 and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise TomTomError(f"TomTom HTTP {e.code}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries:
                raise TomTomError(f"TomTom request failed: {e}") from None
            time.sleep(1.0)
    raise TomTomError("unreachable")


def grid_points(bbox: dict[str, float], n: int) -> list[tuple[float, float]]:
    lats = np.linspace(bbox["south"], bbox["north"], n)
    lons = np.linspace(bbox["west"], bbox["east"], n)
    return [(float(a), float(b)) for a in lats for b in lons]


def fetch_snapshot(bbox: dict[str, float], n_grid: int = 6) -> list[FlowSample]:
    key = api_key()
    out: list[FlowSample] = []
    for lat, lon in grid_points(bbox, n_grid):
        try:
            out.append(fetch_point(lat, lon, key))
        except TomTomError as e:
            if "rejected the key" in str(e):
                raise
            log.warning("skip point %.4f,%.4f: %s", lat, lon, e)
    if not out:
        raise TomTomError("no TomTom samples retrieved")
    return out


def class_ratios(samples: list[FlowSample], min_conf: float = 0.5) -> dict[str, float]:
    """Median current/free-flow speed ratio per road class (falls back to the overall median)."""
    by: dict[str, list[float]] = {}
    for s in samples:
        if s.confidence >= min_conf:
            by.setdefault(FRC_TO_CLASS.get(s.frc, "other"), []).append(s.ratio)
    allr = [r for v in by.values() for r in v] or [s.ratio for s in samples]
    overall = float(np.median(allr))
    zone = load_yaml(CONFIG_DIR / "delhi_zone.yaml")
    return {c: float(np.median(by[c])) if c in by else overall for c in zone["road_classes"]}


def save_snapshot(samples: list[FlowSample], path: Path | None = None) -> Path:
    p = path or DATA_DIR / "processed" / "tomtom_snapshot.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    p.write_text(
        json.dumps(
            {"label": LABEL, "fetched_at": stamp, "samples": [asdict(s) for s in samples]}, indent=1
        )
    )
    return p


def load_snapshot(path: Path | None = None) -> tuple[list[FlowSample], str] | None:
    p = path or DATA_DIR / "processed" / "tomtom_snapshot.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return [FlowSample(**s) for s in d["samples"]], str(d["fetched_at"])


def snapshot_age_s(path: Path | None = None) -> float | None:
    p = path or DATA_DIR / "processed" / "tomtom_snapshot.json"
    return time.time() - p.stat().st_mtime if p.exists() else None


def live_ratios(max_age_s: float = 900.0, refresh: bool = True) -> tuple[dict[str, float], str]:
    """Class ratios from a snapshot younger than max_age_s, else a fresh fetch (needs the key)."""
    age = snapshot_age_s()
    if (age is None or age > max_age_s) and refresh:
        load_dotenv()
        z = load_yaml(CONFIG_DIR / "delhi_zone.yaml")
        save_snapshot(fetch_snapshot(z["bbox"]))
    snap = load_snapshot()
    if snap is None:
        raise TomTomError("no live traffic snapshot available")
    samples, stamp = snap
    return class_ratios(samples), stamp


def with_live_traffic(sc: Any, ratios: dict[str, float], now_slot: int) -> Any:
    """Copy of a Delhi scenario whose tables and simulator use the live-overlaid profile."""
    from dataclasses import replace

    from taqpso.config import load_config
    from taqpso.graph.profiles import apply_live_ratios
    from taqpso.sim.simulator import Network
    from taqpso.traffic.fifo_check import check_fifo
    from taqpso.traffic.pair_tables import build_tables

    net = sc.net
    fac = apply_live_ratios(net.fac, ratios, now_slot)
    thr = load_config().objective.congestion_ratio_threshold
    tb = build_tables(net.graph, net.pairs, fac, net.slot_s, thr)
    check_fifo(tb)
    inst = replace(sc.inst, tables=tb, _cand={})
    live_net = Network(net.graph, net.pairs, fac, net.slot_s, net.thr)
    return replace(sc, inst=inst, net=live_net, meta={**sc.meta, "label": LABEL})


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    z = load_yaml(CONFIG_DIR / "delhi_zone.yaml")
    samples = fetch_snapshot(z["bbox"])
    path = save_snapshot(samples)
    ratios = class_ratios(samples)
    log.info("%d samples -> %s", len(samples), path)
    for c, r in ratios.items():
        log.info("%-12s live speed ratio %.2f", c, r)


if __name__ == "__main__":
    main()
