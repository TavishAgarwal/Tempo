"""Build Delhi demo instances (graph -> snapped nodes -> pair paths -> tau tables -> FIFO check)."""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from taqpso.config import CONFIG_DIR, DATA_DIR, load_config, load_yaml
from taqpso.core.instance import Instance, TravelTables
from taqpso.graph.model import Graph
from taqpso.graph.profiles import load_profiles
from taqpso.sim.simulator import Network
from taqpso.traffic.fifo_check import check_fifo
from taqpso.traffic.pair_tables import PairData, build_pair_paths, build_tables, snap_nodes

log = logging.getLogger(__name__)
PROC = DATA_DIR / "processed"
SCEN = DATA_DIR / "scenarios"


@dataclass
class Scenario:
    name: str
    inst: Instance
    net: Network
    meta: dict[str, object]


def build_scenario(
    name: str,
    depot_lonlat: NDArray[np.float64],
    cust_lonlat: NDArray[np.float64],
    demand: NDArray[np.int32],
    Q: int,
    K: int | None,
    depart_s: float,
    service_s: float = 120.0,
) -> Scenario:
    """Snap points to the graph, build pair paths + TD tables, run the FIFO check."""
    cfg = load_config()
    g = Graph.load(PROC / "graph.npz")
    fac = load_profiles(PROC / "profiles.json")
    pts = np.vstack([np.atleast_2d(depot_lonlat), cust_lonlat])
    nodes = snap_nodes(g, pts)
    pd = build_pair_paths(g, nodes)
    thr = cfg.objective.congestion_ratio_threshold
    tb = build_tables(g, pd, fac, cfg.time.slot_minutes * 60.0, thr)
    check_fifo(tb)
    n = len(cust_lonlat)
    svc = np.r_[0, np.full(n, service_s)].astype(np.float32)
    dem = np.r_[0, np.asarray(demand)].astype(np.int32)
    inst = Instance(
        name,
        g.node_xy[nodes],
        dem,
        int(Q),
        tb,
        svc,
        K=K,
        depart_s=depart_s,
        meta={"nodes": nodes.tolist()},
    )
    net = Network(g, pd, fac, tb.slot_s, thr)
    return Scenario(name, inst, net, {"label": "Calibrated time-of-day profile (synthetic)"})


def make_scenario(
    name: str,
    n: int,
    n_vehicles: int,
    depart_h: float,
    seed: int,
    Q_total_vehicles: int | None = None,
) -> Scenario:
    z = load_yaml(CONFIG_DIR / "delhi_zone.yaml")
    g = Graph.load(PROC / "graph.npz")
    rng = np.random.default_rng(seed)
    hint = np.array([[z["depot_hint"]["lon"], z["depot_hint"]["lat"]]])
    depot = snap_nodes(g, hint)
    cust = rng.choice(np.setdiff1d(np.arange(g.n_nodes), depot), size=n, replace=False)
    demand = rng.integers(1, 10, n).astype(np.int32)
    Q = int(np.ceil(demand.sum() / max(1, (Q_total_vehicles or n_vehicles) - 1)))
    Q = max(Q, int(demand.max()))
    sc = build_scenario(
        name, g.node_xy[depot], g.node_xy[cust], demand, Q, n_vehicles, depart_h * 3600.0
    )
    sc.meta["seed"] = seed
    return sc


def save_scenario(sc: Scenario) -> None:
    SCEN.mkdir(parents=True, exist_ok=True)
    inst = sc.inst
    np.savez_compressed(
        SCEN / f"{sc.name}_tables.npz",
        tau=inst.tables.tau,
        dist=inst.tables.dist,
        cong=inst.tables.cong,
    )
    with open(SCEN / f"{sc.name}_pairs.pkl", "wb") as f:
        pickle.dump(sc.net.pairs, f)
    (SCEN / f"{sc.name}.json").write_text(
        json.dumps(
            {
                "name": inst.name,
                "coords": inst.coords.tolist(),
                "demand": inst.demand.tolist(),
                "service": inst.service.tolist(),
                "Q": inst.Q,
                "K": inst.K,
                "depart_s": inst.depart_s,
                "slot_s": inst.tables.slot_s,
                "nodes": inst.meta["nodes"],
                "meta": sc.meta,
            }
        )
    )


def load_scenario(name: str) -> Scenario:
    cfg = load_config()
    d = json.loads((SCEN / f"{name}.json").read_text())
    z = np.load(SCEN / f"{name}_tables.npz")
    tb = TravelTables(z["tau"], z["dist"], z["cong"], d["slot_s"])
    inst = Instance(
        d["name"],
        np.asarray(d["coords"]),
        np.asarray(d["demand"]),
        d["Q"],
        tb,
        np.asarray(d["service"], dtype=np.float32),
        d["K"],
        d["depart_s"],
        {"nodes": d["nodes"]},
    )
    with open(SCEN / f"{name}_pairs.pkl", "rb") as f:
        pd: PairData = pickle.load(f)  # noqa: S301 - our own build artefact
    g = Graph.load(PROC / "graph.npz")
    fac = load_profiles(PROC / "profiles.json")
    net = Network(g, pd, fac, tb.slot_s, cfg.objective.congestion_ratio_threshold)
    return Scenario(name, inst, net, d["meta"])


SPECS = {
    "delhi_demo": dict(n=100, n_vehicles=8, depart_h=17.5, seed=2026),
    "delhi_n30": dict(n=30, n_vehicles=4, depart_h=17.5, seed=11),
    "delhi_n50": dict(n=50, n_vehicles=6, depart_h=17.5, seed=12),
    "delhi_n200": dict(n=200, n_vehicles=14, depart_h=17.5, seed=13),
    "delhi_n500": dict(n=500, n_vehicles=40, depart_h=17.5, seed=14, Q_total_vehicles=34),
    "delhi_tune1": dict(n=40, n_vehicles=5, depart_h=17.5, seed=101),
    "delhi_tune2": dict(n=40, n_vehicles=5, depart_h=10.0, seed=102),
    "delhi_tune3": dict(n=150, n_vehicles=11, depart_h=17.5, seed=103),
}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    for name, spec in SPECS.items():
        sc = make_scenario(name, **spec)  # type: ignore[arg-type]
        save_scenario(sc)
        log.info("built %s (n=%d, tables %.1f MB)", name, sc.inst.n, sc.inst.tables.nbytes / 1e6)


if __name__ == "__main__":
    main()
