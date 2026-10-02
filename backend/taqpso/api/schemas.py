"""Pydantic v2 request/response models (OpenAPI source of truth for the frontend types)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Solver = Literal["qpso", "pso", "ga", "random", "pyvrp"]
Preset = Literal["fastest", "balanced", "low_congestion"]
JobState = Literal["idle", "solving", "safe_plan", "optimising", "done", "error", "stopped"]


class ScenarioInfo(BaseModel):
    name: str
    n_customers: int
    n_vehicles: int | None
    capacity: int
    depart_s: float
    speed_source: str = "Calibrated time-of-day profile (synthetic)"


class CustomerIn(BaseModel):
    lon: float
    lat: float
    demand: int = Field(ge=1)


class InstanceCreate(BaseModel):
    # becomes a file name under data/scenarios, so no path separators or dots
    name: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")
    depot_lon: float
    depot_lat: float
    customers: list[CustomerIn] = Field(min_length=1, max_length=300)
    capacity: int = Field(ge=1)
    n_vehicles: int | None = Field(default=None, ge=1)
    depart_s: float = 17.5 * 3600.0


class InstanceDetail(ScenarioInfo):
    depot: tuple[float, float]
    customers: list[CustomerIn]
    bbox: tuple[float, float, float, float]  # west, south, east, north


class SolveRequest(BaseModel):
    instance_id: str
    solver: Solver = "qpso"
    preset: Preset = "fastest"
    budget_s: float = Field(default=10.0, ge=1.0, le=300.0)
    seed: int = 0
    depart_s: float | None = None
    live: bool = False  # overlay the latest TomTom snapshot on the profile (needs TOMTOM_API_KEY)


class MetricsOut(BaseModel):
    T: float
    D: float
    C: float
    J: float
    K: int
    route_T: list[float] = []
    route_load: list[int] = []


class SolutionOut(BaseModel):
    routes: list[list[int]]
    depart: float
    metrics: MetricsOut
    solver: str
    seed: int
    budget: float
    geometry: list[list[list[float]]] = []  # per route: polyline [lon, lat]


class JobStatus(BaseModel):
    job_id: str
    kind: Literal["solve", "incident"]
    state: JobState
    elapsed_s: float
    message: str | None = None
    solution: SolutionOut | None = None
    run_id: str | None = None


class IncidentRequest(BaseModel):
    job_id: str
    edges: list[int] | None = None
    polygon: list[tuple[float, float]] | None = None  # (lon, lat) ring
    factor: float = Field(default=0.1, gt=0.0, le=1.0)
    t_start: float
    t_end: float
    budget_s: float = Field(default=10.0, ge=1.0, le=120.0)
    mu: float = Field(default=0.0, ge=0.0)
    seed: int = 0


class IncidentCreated(BaseModel):
    job_id: str
    affected_edges: int


class RescoreOut(BaseModel):
    depart_s: float
    metrics: MetricsOut


class PathOut(BaseModel):
    travel_s: float
    distance_m: float
    free_flow_travel_s: float
    geometry: list[list[float]]
    free_flow_geometry: list[list[float]]
    depart_s: float


class CongestionEdge(BaseModel):
    a: tuple[float, float]
    b: tuple[float, float]
    ratio: float
    road_class: int


class CongestionOut(BaseModel):
    slot: int
    label: str
    edges: list[CongestionEdge]


class ResultTable(BaseModel):
    experiment: str
    title: str
    rows: list[dict[str, float | str | None]]
    files: list[str]


class LiveOut(BaseModel):
    available: bool
    label: str
    fetched_at: str | None = None
    age_s: float | None = None
    ratios: dict[str, float] = {}
    message: str | None = None


class EmissionsOut(BaseModel):
    kg: float
    label: str
