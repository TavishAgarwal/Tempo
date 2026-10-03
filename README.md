# Tempo — traffic-aware vehicle routing

The solver is TA-QPSO (Traffic-Aware Quantum-Inspired routing).

SIH 2026 · PS 26137. Quantum-inspired classical optimisation (a QPSO sampling rule) on a normal CPU.
No quantum hardware, no speedup claim. Docs live in `docs/` (PRD, architecture, rules, phases,
design, implementation plan, `status.md` for what is verified and what is not).

## Quick start

```bash
make setup        # python 3.11 venv (pinned deps) + frontend deps (needs uv, node >= 20)
make data         # OSM Delhi graph, profiles, tables, scenarios, CVRPLIB (internet; data/ is gitignored)
make test         # fast test suite
make run-api      # http://localhost:8000/docs
make run-ui       # http://localhost:5173
```

## Reproduce one table (E1, ~5 min)

```bash
make setup data
make exp-e1                         # writes results/e1/table.csv from results/runs/*.json
cd backend && .venv/bin/python -m experiments.summarize   # renders docs/results-summary.md
```
Everything else: `make exp-all` (E1–E5, hours; see `docs/reproduction.md` for tuning and the order).

## Optional data and keys

| Feature | What to do |
|---|---|
| Poryos2026 benchmark + official checker | `uv pip install --python backend/.venv/bin/python "mamut-routing-lib[cli]"` then `backend/.venv/bin/mamut-routing --benchmarks-dir data/raw remote --tag snapshot-2026-09-23-70ca946 fetch --benchmark-name Poryos2026`; then `python -m experiments.poryos_check` (from `backend/`) |
| KAYROS reference (Poryos only) | `uv pip install --python backend/.venv/bin/python kayros` (needs CMake and Boost: `brew install boost`) |
| Live traffic (TomTom) | put `TOMTOM_API_KEY=...` in `.env` (gitignored), `make live-snapshot`; the Plan page then shows a "Live traffic" toggle |
| Offline demo gate | `make demo-offline` runs the 3-minute demo flow twice with a guard that refuses every non-loopback connection |

Map tiles come from OpenStreetMap (ODbL, attribution on the map); tiles are cached by a service
worker after one online visit. API demo: `scripts/demo_curl.sh`.

Docs: `docs/status.md`, `docs/results-summary.md` (generated), `docs/demo-script.md`,
`docs/formulation.md`, `docs/calibration-notes.md`, `docs/limitations.md`, `docs/reproduction.md`.
