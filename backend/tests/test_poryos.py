from __future__ import annotations

import json

import pytest

from taqpso.bench.poryos import load_poryos, official_cost
from taqpso.config import DATA_DIR
from taqpso.core.evaluate import route_times
from taqpso.core.solution import Solution

ROOT = DATA_DIR / "raw" / "Poryos2026" / "TDVRP"
FILES = sorted(ROOT.glob("*/n=10/*/*/*.vrp.json"))[:6] if ROOT.exists() else []


@pytest.mark.skipif(not FILES, reason="Poryos2026 not downloaded")
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.parent.name)
def test_table_evaluation_matches_official_checker(path):
    inst, loaded = load_poryos(path)
    bks_path = path.with_name(path.name.replace(".vrp.json", ".bks.Duration.json"))
    bks = json.loads(bks_path.read_text())
    sol = Solution([list(r) for r in bks["routes"]])
    off = official_cost(loaded, sol)
    mine = sum(route_times(inst, r)[-1] - inst.depart_s for r in sol.routes)
    assert off == pytest.approx(bks["cost"], rel=1e-9)
    assert mine == pytest.approx(off, rel=1e-4)
