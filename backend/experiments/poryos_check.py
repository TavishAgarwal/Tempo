"""Poryos2026 gate: official checker vs our table evaluation, and TA-QPSO gap to the stored BKS.

Needs data/raw/Poryos2026 (see docs/reproduction.md). Every solution is re-scored by the official
mamut-routing-lib TD checker (Duration objective), as required by rules.md.
"""

from __future__ import annotations

import json
import logging
import os

for _v in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from taqpso.bench.poryos import load_poryos, official_cost  # noqa: E402
from taqpso.config import DATA_DIR, load_config  # noqa: E402
from taqpso.core.evaluate import route_times  # noqa: E402
from taqpso.core.solution import Solution  # noqa: E402
from taqpso.solver.runner import solve  # noqa: E402
from taqpso.store.results import RunRecord, save_run  # noqa: E402

log = logging.getLogger("poryos")
ROOT = DATA_DIR / "raw" / "Poryos2026" / "TDVRP"
CITIES = ["paris", "san_francisco", "tokyo"]
SIZES = [10, 25, 50]
VARIANTS = ["bpr-heavy", "wave-heavy"]


def table_duration(inst, sol: Solution) -> float:  # type: ignore[no-untyped-def]
    return float(sum(route_times(inst, r)[-1] - inst.depart_s for r in sol.routes if r))


def main(budget_s: float = 10.0, seeds: int = 3) -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    rows = []
    for city in CITIES:
        for n in SIZES:
            for p in sorted(ROOT.glob(f"{city}/n={n}/*/*/*.vrp.json"))[:4]:
                if p.parent.name not in VARIANTS:
                    continue
                inst, loaded = load_poryos(p)
                bks_f = p.with_name(p.name.replace(".vrp.json", ".bks.Duration.json"))
                if not bks_f.exists():
                    continue
                bks = json.loads(bks_f.read_text())
                bsol = Solution([list(r) for r in bks["routes"]])
                off_bks = official_cost(loaded, bsol)
                tab_bks = table_duration(inst, bsol)
                best = None
                for seed in range(seeds):
                    r = solve(inst, cfg, "qpso", seed, budget_s=budget_s)
                    off = official_cost(loaded, r.solution)
                    best = off if best is None else min(best, off)
                    save_run(
                        RunRecord(
                            experiment="poryos",
                            instance_id=inst.name,
                            instance_hash=inst.hash(),
                            config=cfg.to_dict(),
                            config_hash=cfg.hash(),
                            solver="qpso",
                            seed=seed,
                            budget_s=budget_s,
                            metrics={
                                "official_cost": off,
                                "table_cost": table_duration(inst, r.solution),
                                "bks": float(bks["cost"]),
                                "gap_to_bks": (off - bks["cost"]) / bks["cost"],
                                "feasible": r.feasible,
                            },
                            trace=r.trace,
                        )
                    )
                row = {
                    "instance": inst.name,
                    "n": inst.n,
                    "bks": bks["cost"],
                    "checker_on_bks": off_bks,
                    "table_on_bks": tab_bks,
                    "table_vs_checker_rel": (tab_bks - off_bks) / off_bks,
                    "qpso_best": best,
                    "gap_pct": 100 * (best - bks["cost"]) / bks["cost"],
                }
                log.info("%s", row)
                rows.append(row)
    out = DATA_DIR.parent / "results" / "poryos_summary.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))
    log.info("wrote %s", out)


if __name__ == "__main__":
    main()
