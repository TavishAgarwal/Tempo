from __future__ import annotations

from typing import Any

from taqpso.config import Config
from taqpso.solver.optimizers.base import Optimizer, Swarm
from taqpso.solver.optimizers.ga import GA
from taqpso.solver.optimizers.pso import PSO
from taqpso.solver.optimizers.qpso import QPSO
from taqpso.solver.optimizers.random_restart import RandomRestart

REGISTRY: dict[str, Any] = {"qpso": QPSO, "pso": PSO, "ga": GA, "random": RandomRestart}


def get_optimizer(name: str, cfg: Config) -> Optimizer:
    opt: Optimizer = REGISTRY[name](cfg)
    return opt


__all__ = ["REGISTRY", "Optimizer", "Swarm", "get_optimizer"]
