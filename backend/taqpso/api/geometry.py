"""Route polylines on the real road graph (from the stored pair paths)."""

from __future__ import annotations

from taqpso.sim.simulator import Network


def leg_coords(net: Network, a: int, b: int) -> list[list[float]]:
    g, pd = net.graph, net.pairs
    edges = pd.path(a, b)
    pts = [g.node_xy[pd.nodes[a]]]
    pts += [g.node_xy[g.edge_to[e]] for e in edges]
    return [[float(x), float(y)] for x, y in pts]


def route_geometry(net: Network, route: list[int]) -> list[list[float]]:
    out: list[list[float]] = []
    prev = 0
    for c in [*route, 0]:
        out.extend(leg_coords(net, prev, c))
        prev = c
    return out
