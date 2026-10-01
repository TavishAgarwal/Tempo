from __future__ import annotations

import pytest

from taqpso.bench.make_scenarios import SCEN, SPECS, load_scenario
from taqpso.traffic.fifo_check import check_fifo


@pytest.mark.parametrize("name", list(SPECS))
def test_fifo_on_built_delhi_instances(name):
    if not (SCEN / f"{name}.json").exists():
        pytest.skip("run `make data` first")
    sc = load_scenario(name)
    check_fifo(sc.inst.tables)
