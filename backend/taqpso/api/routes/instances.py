from __future__ import annotations

import uuid

import numpy as np
from fastapi import APIRouter, HTTPException

from taqpso.api import state
from taqpso.api.schemas import CustomerIn, InstanceCreate, InstanceDetail, ScenarioInfo
from taqpso.bench.make_scenarios import build_scenario, save_scenario
from taqpso.core.instance import InstanceError

router = APIRouter()


def _info(name: str) -> ScenarioInfo:
    inst = state.scenario(name).inst
    return ScenarioInfo(
        name=name, n_customers=inst.n, n_vehicles=inst.K, capacity=inst.Q, depart_s=inst.depart_s
    )


@router.get("/scenarios", response_model=list[ScenarioInfo])
def list_scenarios() -> list[ScenarioInfo]:
    return [_info(n) for n in state.scenario_names()]


@router.get("/scenarios/{name}", response_model=InstanceDetail)
def scenario_detail(name: str) -> InstanceDetail:
    try:
        sc = state.scenario(name)
    except KeyError:
        raise HTTPException(404, f"Unknown scenario {name}") from None
    inst = sc.inst
    xy = inst.coords
    cust = [
        CustomerIn(lon=float(xy[i, 0]), lat=float(xy[i, 1]), demand=int(inst.demand[i]))
        for i in range(1, inst.n + 1)
    ]
    g = sc.net.graph
    bbox = (
        float(g.node_xy[:, 0].min()),
        float(g.node_xy[:, 1].min()),
        float(g.node_xy[:, 0].max()),
        float(g.node_xy[:, 1].max()),
    )
    base = _info(name)
    return InstanceDetail(
        **base.model_dump(), depot=(float(xy[0, 0]), float(xy[0, 1])), customers=cust, bbox=bbox
    )


@router.post("/instances", response_model=ScenarioInfo)
def create_instance(req: InstanceCreate) -> ScenarioInfo:
    name = req.name or f"custom_{uuid.uuid4().hex[:8]}"
    if name in state.scenario_names():
        raise HTTPException(409, f"Scenario {name} already exists")
    cust = np.array([[c.lon, c.lat] for c in req.customers])
    dem = np.array([c.demand for c in req.customers], dtype=np.int32)
    try:
        sc = build_scenario(
            name,
            np.array([req.depot_lon, req.depot_lat]),
            cust,
            dem,
            req.capacity,
            req.n_vehicles,
            req.depart_s,
        )
    except InstanceError as e:
        raise HTTPException(422, str(e)) from None
    save_scenario(sc)
    state.scenario.cache_clear()
    return _info(name)
