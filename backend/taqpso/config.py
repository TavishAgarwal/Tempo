"""Pydantic config models + YAML loader with override merging."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "configs"
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class TimeCfg(_M):
    slot_minutes: int = 15
    n_slots: int = 96


class SwarmCfg(_M):
    size: int = 12
    alpha_start: float = 1.0
    alpha_end: float = 0.5


class QpsoCfg(_M):
    u_floor: float = 1.0e-12
    # local attractor P = phi*pbest + (1-phi)*gbest: one phi per key ("dimension", the textbook
    # rule) or one phi per particle ("particle"), which blends two tours instead of shuffling them
    attractor: Literal["dimension", "particle"] = "dimension"
    # update the raw keys ("key") or each vector's normalised ranks ("rank"), so that the step
    # size alpha is measured in tour positions whatever the spread of the written-back keys
    space: Literal["key", "rank"] = "key"


class PsoCfg(_M):
    inertia_start: float = 0.9
    inertia_end: float = 0.4
    c1: float = 1.5
    c2: float = 1.5
    vmax: float = 0.25


class GaCfg(_M):
    elite_fraction: float = 0.2
    mutant_fraction: float = 0.2
    inherit_prob: float = 0.7


class StallCfg(_M):
    iterations: int = 30
    reinit_fraction: float = 0.30


class VndCfg(_M):
    candidate_k: int = 15
    neighbourhoods: list[str] = Field(
        default_factory=lambda: ["relocate", "swap", "two_opt", "two_opt_star", "or_opt"]
    )
    max_passes: int = 50
    enabled: bool = True
    # gated VND: every particle gets a light pass; only those then within gate_tolerance of their
    # own pbest cost continue with the full VND. None = always full VND.
    gate_tolerance: float | None = None
    light_neighbourhoods: list[str] = Field(default_factory=lambda: ["relocate", "two_opt"])
    light_passes: int = 2


class BudgetCfg(_M):
    plan_n100: float = 30
    plan_n200: float = 60
    reopt: float = 10
    default: float = 10


class Weights(_M):
    w_T: float
    w_D: float
    w_C: float


class ObjectiveCfg(_M):
    congestion_ratio_threshold: float = 0.5
    presets: dict[str, Weights]
    preset: str = "fastest"
    c_ref_floor_fraction: float = 0.05
    excess_vehicle_penalty: float = 10.0


class ReoptCfg(_M):
    warm_fraction: float = 0.5
    warm_noise: float = 0.05
    stability_mu: float = 0.0


class IncidentCfg(_M):
    blocked_factor: float = 0.1
    heavy_factor: float = 0.4


class SimCfg(_M):
    horizon_wrap: bool = True


class FallbackCfg(_M):
    target_s: float = 1.0


class SeedsCfg(_M):
    default_n: int = 20
    small_n: int = 30
    small_n_threshold: int = 100


class Config(_M):
    time: TimeCfg = TimeCfg()
    swarm: SwarmCfg = SwarmCfg()
    qpso: QpsoCfg = QpsoCfg()
    pso: PsoCfg = PsoCfg()
    ga: GaCfg = GaCfg()
    stall: StallCfg = StallCfg()
    vnd: VndCfg = VndCfg()
    write_back: bool = True
    budget_s: BudgetCfg = BudgetCfg()
    objective: ObjectiveCfg
    reopt: ReoptCfg = ReoptCfg()
    incident: IncidentCfg = IncidentCfg()
    sim: SimCfg = SimCfg()
    fallback: FallbackCfg = FallbackCfg()
    seeds: SeedsCfg = SeedsCfg()

    def weights(self) -> Weights:
        return self.objective.presets[self.objective.preset]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


def deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return data or {}


def load_config(
    *overlays: Path | dict[str, Any] | None, default_path: Path | None = None
) -> Config:
    """default.yaml <- each overlay (experiment yaml path or override dict) in order."""
    merged = load_yaml(default_path or CONFIG_DIR / "default.yaml")
    for ov in overlays:
        if ov is None:
            continue
        merged = deep_merge(merged, load_yaml(ov) if isinstance(ov, Path) else ov)
    return Config.model_validate(merged)


def tuned_overrides(optimizer: str) -> dict[str, Any]:
    """Frozen per-optimizer parameters chosen on the tuning set (configs/tuned.yaml)."""
    p = CONFIG_DIR / "tuned.yaml"
    return dict(load_yaml(p).get(optimizer, {})) if p.exists() else {}


def load_emission_params() -> Any:
    """[a, b, c, d, e, v_min, v_max] for traffic.emissions (configs/emissions.yaml)."""
    import numpy as np

    y = load_yaml(CONFIG_DIR / "emissions.yaml")
    return np.array(
        [y["a"], y["b"], y["c"], y["d"], y["e"], y["v_min_kmph"], y["v_max_kmph"]], dtype=np.float64
    )
