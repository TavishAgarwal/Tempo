from __future__ import annotations

import numpy as np
import pytest

from taqpso.core.instance import Instance, InstanceError, TravelTables
from taqpso.core.solution import InfeasibleSolution, Solution
from tests.conftest import make_instance


def test_validator_catches_problems():
    inst = make_instance(6, 1, Q=1000)
    Solution([[1, 2, 3], [4, 5, 6]]).validate(inst)
    with pytest.raises(InfeasibleSolution):
        Solution([[1, 2, 3], [4, 5]]).validate(inst)  # missing 6
    with pytest.raises(InfeasibleSolution):
        Solution([[1, 2, 3], [3, 4, 5, 6]]).validate(inst)  # duplicate
    small = make_instance(6, 1, Q=9)
    assert small.demand[1:].sum() > 9
    with pytest.raises(InfeasibleSolution, match="exceeds capacity"):
        Solution([[1, 2, 3, 4, 5, 6]]).validate(small)
    k = make_instance(6, 1, Q=1000, K=1)
    with pytest.raises(InfeasibleSolution):
        Solution([[1, 2, 3], [4, 5, 6]]).validate(k)


def test_demand_over_capacity_error_message():
    d = np.zeros((3, 3), dtype=np.float32)
    with pytest.raises(InstanceError, match="Demand exceeds capacity at customer 2"):
        Instance("x", np.zeros((3, 2)), np.array([0, 1, 9]), 5, TravelTables.static(d))
