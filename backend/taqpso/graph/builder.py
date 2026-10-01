"""OSMnx -> CSR road graph arrays (build step only; the only module allowed to use osmnx)."""

from __future__ import annotations

import logging

import numpy as np

from taqpso.config import CONFIG_DIR, DATA_DIR, load_yaml

log = logging.getLogger(__name__)

CLASS_NAMES = ["motorway", "trunk", "primary", "secondary", "tertiary", "residential", "other"]


def _road_class(hw: object) -> int:
    h = hw[0] if isinstance(hw, list) else hw
    h = str(h).replace("_link", "")
    return CLASS_NAMES.index(h) if h in CLASS_NAMES else CLASS_NAMES.index("other")


def _parse_speed(v: object) -> float | None:
    v = v[0] if isinstance(v, list) else v
    try:
        return float(str(v).split()[0])
    except (ValueError, IndexError):
        return None


def build_graph(zone_yaml: str = "delhi_zone.yaml") -> dict[str, object]:
    import osmnx as ox

    z = load_yaml(CONFIG_DIR / zone_yaml)
    b = z["bbox"]
    G = ox.graph_from_bbox(
        (b["west"], b["south"], b["east"], b["north"]), network_type=z["network_type"]
    )
    G = ox.truncate.largest_component(G, strongly=True)
    nodes = list(G.nodes)
    idx = {n: i for i, n in enumerate(nodes)}
    coords = np.array([[G.nodes[n]["x"], G.nodes[n]["y"]] for n in nodes], dtype=np.float64)
    frm, to, length, ff, rc = [], [], [], [], []
    filled = 0
    defaults = z["default_speed_kph"]
    for u, v, d in G.edges(data=True):
        cls = _road_class(d.get("highway"))
        sp = _parse_speed(d.get("maxspeed"))
        if sp is None:
            sp = float(defaults.get(CLASS_NAMES[cls], defaults["other"]))
            filled += 1
        frm.append(idx[u])
        to.append(idx[v])
        length.append(float(d.get("length", 1.0)))
        ff.append(sp / 3.6)
        rc.append(cls)
    order = np.argsort(frm, kind="stable")
    arr = {
        "node_xy": coords,
        "edge_from": np.asarray(frm, dtype=np.int32)[order],
        "edge_to": np.asarray(to, dtype=np.int32)[order],
        "length_m": np.asarray(length, dtype=np.float64)[order],
        "freeflow_mps": np.asarray(ff, dtype=np.float64)[order],
        "road_class": np.asarray(rc, dtype=np.int8)[order],
    }
    log.info(
        "graph: %d nodes, %d edges, maxspeed fill rate %.1f%%",
        len(nodes),
        len(frm),
        100 * filled / max(len(frm), 1),
    )
    arr["fill_rate"] = np.asarray(filled / max(len(frm), 1))
    return arr


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    from taqpso.graph.profiles import write_profiles

    arr = build_graph()
    out = DATA_DIR / "processed"
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "graph.npz", **arr)  # type: ignore[arg-type]
    write_profiles(out / "profiles.json")
    log.info("wrote %s", out / "graph.npz")


if __name__ == "__main__":
    main()
