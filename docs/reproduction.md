# Reproduction guide

```
make setup          # python 3.11 venv (pinned deps), frontend deps
make data           # OSM graph (needs internet), profiles, Delhi scenarios, CVRPLIB files
make test
make exp-e1         # static correctness: gap to MILP (n<=15) and CVRPLIB BKS
cd backend && PYTHONPATH=. .venv/bin/python -m experiments.tune     # freezes configs/tuned.yaml (resumable)
make exp-e2 exp-e3 exp-e4 exp-e5
cd backend && .venv/bin/python -m experiments.summarize             # docs/results-summary.md
```
Every run writes a JSON record to `results/runs/` (instance hash, resolved config, seed, solver,
budget, commit, machine, metrics, convergence trace). Tables/plots in `results/eX/` are derived
only from those records. Experiments use single-threaded worker processes (NUMBA/OMP/BLAS = 1);
runs execute in parallel processes on one machine, so wall-clock timings carry some contention noise
(do not run other heavy jobs while an experiment runs: compiling or testing in parallel inflates
the latency columns). Tag the commit of every reported result (`git tag results-eX-YYYYMMDD`).

Tuning uses `delhi_tune1/2/3` (n = 40, 40, 150; disjoint from E2) and scores each grid point by the
mean over these instances of its median gap to the best tuning run on that instance.
`python -m experiments.tune --select-only` re-picks from the saved records without running jobs.
The E2 driver applies `configs/tuned.yaml` per optimizer (before 2026-10-03 it did not, so E1–E5
results from earlier runs used `configs/default.yaml`).

Retuning is required whenever the speed profile changes (`configs/delhi_zone.yaml` `profile:`),
because scenarios, tables and tuned parameters all depend on it: `make data` (profiles +
scenarios), then `experiments.tune`, then `make exp-all`.

## Poryos2026 (optional, ~330 MB)

```
uv pip install --python backend/.venv/bin/python "mamut-routing-lib[cli]"
TAG=snapshot-2026-09-23-70ca946
backend/.venv/bin/mamut-routing --benchmarks-dir data/raw remote --tag $TAG fetch --benchmark-name Poryos2026
backend/.venv/bin/mamut-routing --benchmarks-dir data/raw remote --tag $TAG verify --benchmark-name Poryos2026
cd backend && .venv/bin/python -m experiments.poryos_check          # checker agreement + gap to BKS (TDVRP)
.venv/bin/python -m experiments.poryos_ref TDVRPTW 10 3              # TA-QPSO vs KAYROS, official checker
```
Use `--benchmark-name` alone (adding `--problem-type` filters the collection out). Cities in the
snapshot: Hong Kong, Lyon, Paris, San Francisco, Tokyo (no Delhi). The Sep 23 snapshot predates the
td-fold/2 re-pricing of the TD best-known solutions (mamut-routing-lib >= 0.12.0 ships the checker
contract); re-fetch with a newer tag when one is published.

## Live traffic (optional)
`TOMTOM_API_KEY` in `.env` (gitignored), then `make live-snapshot`. The API reads the same file.

## Offline demo gate
`make demo-offline` starts the API with a socket guard (`scripts/offline_guard`) that refuses every
non-loopback connection, then runs `scripts/demo_check.py` twice (solve, stream, emissions, rescore,
incident with fallback < 1 s, path, results). `node frontend/record_demo.mjs` records the UI flow as
a fallback video (needs Google Chrome; output in `results/demo_video/`).
