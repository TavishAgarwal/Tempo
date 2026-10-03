# Architecture — Tempo

## 1. High-level flow

```
OSM extract ─► Graph builder ─► Speed profiles (15-min, per road class)
                                   │
Customers + depot ─► Instance ─────┤
                                   ▼
                     Pair paths (static Dijkstra) + inverted index edge→pairs
                                   ▼
                     TD tables τ_ij(t) (IGP propagation, 96 slots) + FIFO check
                                   ▼
        ┌──────────── Solver runner (same budget/seed for all) ────────────┐
        │ TA-QPSO | PSO | GA | Random restart | PyVRP | MILP | (KAYROS)    │
        └──────────────────────────────┬───────────────────────────────────┘
                                       ▼
                    Ground-truth simulator (edge-level IGP) → metrics
                                       ▼
                     Result store (JSON/CSV) → API → Dashboard / Experiments
```

## 2. Solver loop (per particle, per iteration)
1. Keys x ∈ [0,1]^n → sort → giant tour π
2. TD-Split DP → capacity-feasible routes (O(n·B); O(K·n·B) with fixed K)
3. VND (relocate, swap, 2-opt, 2-opt*, or-opt; candidate lists k = 15; suffix re-evaluation)
4. Write-back: improved order → keys
5. Update pbest / gbest / mbest
6. QPSO update: x_d ← P_d ± α|m_d − x_d| ln(1/u); u ≥ 1e-12; reflect into [0,1]; α 0.05 → 0.01 (tuned)
7. Stall 30 iterations → re-randomise worst 30%

Optimiser plug-in point: step 6 only. PSO, GA, random restart replace step 6 and keep 1–5.

## 3. Incident flow
```
POST /incidents ─► apply speed factors as new breakpoints
   ─► affected pairs (inverted index) ─► re-run Dijkstra from their origins ─► recompute τ rows
   ─► vehicle states at t_e: position on edge (elapsed time), commit next stop, ETA, remaining load
   ─► FALLBACK: old sequence + TD-Dijkstra detours → stream immediately
   ─► warm QPSO: 50% incumbent+noise, 50% random; fleet-aware Split (vehicles start at own states)
   ─► stream improvements over WebSocket until budget ends
```

## 4. Folder structure

```
ta-qpso/
├── README.md
├── Makefile                      # setup, build-graph, test, run-api, run-ui, exp-all
├── docker-compose.yml
├── configs/
│   ├── default.yaml              # budgets, swarm size, α schedule, k, presets
│   ├── delhi_zone.yaml           # bbox, network type, road-class defaults
│   └── experiments/              # e1.yaml … e5.yaml
├── data/                         # gitignored
│   ├── raw/                      # OSM extracts, Poryos2026 clone, CVRPLIB
│   ├── processed/                # graph.npz, profiles.json, pair tables (.npy)
│   └── scenarios/                # demo instances + incident scripts (JSON)
├── backend/
│   ├── pyproject.toml
│   ├── taqpso/
│   │   ├── config.py             # pydantic settings, YAML loader
│   │   ├── graph/
│   │   │   ├── builder.py        # OSMnx → CSR arrays (from, to, length, freeflow, class)
│   │   │   └── profiles.py       # per-class 15-min speed factors, calibration
│   │   ├── traffic/
│   │   │   ├── igp.py            # edge travel time under stepwise speeds (Numba)
│   │   │   ├── pair_tables.py    # paths, inverted index, τ_ij(t) tables, interpolation
│   │   │   ├── fifo_check.py     # τ(t+Δ) − τ(t) ≥ −Δ for all pairs
│   │   │   └── incidents.py      # incident model, breakpoints, affected pairs, re-pathing
│   │   ├── core/
│   │   │   ├── instance.py       # depot, customers, demands, Q, K, service times
│   │   │   ├── solution.py       # routes, giant tour conversion, validation
│   │   │   ├── evaluate.py       # TD route propagation (Numba)
│   │   │   └── objective.py      # T, D, C, normalisation, presets
│   │   ├── solver/
│   │   │   ├── keys.py           # sort, reflect, write-back
│   │   │   ├── split.py          # TD-Split (unlimited fleet)
│   │   │   ├── split_fleet.py    # fixed-K and vehicles-in-field variant
│   │   │   ├── vnd.py            # neighbourhoods, candidate lists
│   │   │   ├── seeds.py          # nearest neighbour, sweep
│   │   │   ├── optimizers/
│   │   │   │   ├── base.py       # Optimizer interface: init(), step(swarm) → swarm
│   │   │   │   ├── qpso.py
│   │   │   │   ├── pso.py
│   │   │   │   ├── ga.py         # random-key GA
│   │   │   │   └── random_restart.py
│   │   │   └── runner.py         # anytime loop, budget, seeds, callbacks/streaming
│   │   ├── dynamic/
│   │   │   ├── vehicle_state.py  # position on edge, next stop, ETA, load
│   │   │   ├── fallback.py       # keep sequence + detours (B0)
│   │   │   └── reopt.py          # warm start, stability penalty μ
│   │   ├── paths/
│   │   │   └── td_dijkstra.py    # earliest-arrival Dijkstra
│   │   ├── sim/
│   │   │   └── simulator.py      # ground-truth edge-level scoring of any solution
│   │   ├── baselines/
│   │   │   ├── pyvrp_adapter.py  # static matrix in, routes out
│   │   │   ├── milp.py           # MTZ CVRP (HiGHS / CP-SAT)
│   │   │   └── kayros_adapter.py # optional
│   │   ├── bench/
│   │   │   ├── cvrplib.py
│   │   │   └── poryos.py         # mamut-routing-lib loader + checker
│   │   ├── store/
│   │   │   └── results.py        # run records (JSON), CSV export
│   │   └── api/
│   │       ├── main.py           # FastAPI app
│   │       ├── schemas.py        # pydantic models
│   │       ├── jobs.py           # background job manager (process pool)
│   │       └── routes/           # instances.py, solve.py, incidents.py, paths.py, results.py
│   ├── experiments/
│   │   ├── e1_correctness.py … e5_scaling.py
│   │   ├── stats.py              # Wilcoxon, Holm, A12
│   │   └── plots.py              # convergence bands, boxplots, scaling
│   └── tests/
│       ├── test_fifo.py
│       ├── test_split.py         # vs brute force on tiny instances
│       ├── test_vnd.py           # moves never worsen; feasibility kept
│       ├── test_td_dijkstra.py   # equals static Dijkstra at free flow
│       ├── test_simulator.py     # agrees with Poryos checker
│       ├── test_qpso_bounds.py   # keys stay in [0,1], no NaN
│       └── test_milp.py          # known small optima
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx, App.tsx
│       ├── api/                  # client.ts, ws.ts, types.ts (generated from OpenAPI)
│       ├── state/                # store.ts (Zustand)
│       ├── pages/                # PlanPage, IncidentPage, BenchmarkPage, PathPage, AboutPage
│       ├── components/
│       │   ├── map/              # MapView, RouteLayer, CongestionLayer, IncidentLayer, VehicleMarker
│       │   ├── panels/           # SolveForm, KpiStrip, RouteList, DiffPanel, AlgorithmPanel
│       │   ├── charts/           # ConvergenceChart, BoxplotChart, ScalingChart
│       │   └── ui/               # Button, Select, Slider, Badge, Tabs, Toast
│       └── styles/               # tokens.css, tailwind.css
├── results/                      # gitignored run outputs, plots
└── docs/                         # PRD.md, architecture.md, rules.md, phases.md, design.md
```

## 5. Key interfaces

```python
class Optimizer(Protocol):
    def init(self, n: int, rng: np.random.Generator, seeds: list[np.ndarray]) -> Swarm: ...
    def step(self, swarm: Swarm, progress: float, rng: np.random.Generator) -> np.ndarray:  # new keys (M×n)
        ...

def decode(keys, inst, tables, fleet_state=None) -> Solution          # sort + split
def improve(sol, inst, tables, cand) -> Solution                       # VND
def write_back(keys, sol) -> np.ndarray
def simulate(sol, graph, speeds, incidents, depart) -> Metrics         # ground truth
def td_shortest_path(graph, speeds, src, dst, t0) -> Path
```

## 6. API

| Method | Path | Purpose |
|---|---|---|
| GET | /scenarios | List demo scenarios |
| POST | /instances | Create instance (depot, customers, demands, Q, K, depart) |
| POST | /solve | Start job {instance_id, solver, preset, budget_s, seed} → job_id |
| GET | /jobs/{id} | Status + best solution + metrics |
| WS | /jobs/{id}/stream | Incumbent updates {t, cost, routes, diversity} |
| POST | /incidents | {job_id, edges or polygon, factor, t_start, t_end} → new job_id |
| GET | /paths | ?from&to&depart → TD shortest path |
| GET | /congestion | ?slot → edge speed ratios (for map layer) |
| GET | /results | Experiment tables/plots |

## 7. Data formats
- Graph: CSR arrays in `.npz` (node coords, edge from/to, length_m, freeflow_mps, road_class).
- Speed profiles: JSON {road_class: [96 factors]}.
- Pair tables: `tau.npy` float32 (n+1, n+1, 96), `paths.pkl` (edge-id arrays), `inv_index.pkl`.
- Solution: JSON {routes: [[customer ids]], depart, metrics: {T, D, C, J, K}, solver, seed, budget}.

## 8. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | KAYROS and mamut-routing-lib need ≥ 3.11 |
| Numerics | NumPy, Numba | Hot loops (IGP, evaluate, Split, VND) compiled |
| Graph | OSMnx (build only), scipy.sparse.csgraph | Fast Dijkstra; no NetworkX in hot paths |
| Exact | HiGHS (highspy) or OR-Tools CP-SAT | MTZ MILP |
| Baselines | PyVRP; optional KAYROS | Strong references |
| Benchmarks | mamut-routing-lib, CVRPLIB files | Poryos2026 + checker |
| API | FastAPI, Uvicorn, pydantic v2 | Typed, async, WebSocket |
| Jobs | concurrent.futures ProcessPool | One solve = one process, one thread |
| Experiments | pandas, scipy.stats, matplotlib | Stats + plots |
| Frontend | React + TypeScript + Vite | Fast dev |
| Map | Leaflet (react-leaflet), CARTO light/dark tiles | Free, offline-cacheable |
| Charts | Recharts | Live convergence |
| Styling/state | Tailwind CSS, Zustand | Small, simple |
| Quality | pytest, ruff, mypy, pre-commit | CI-checkable |
| Packaging | Docker, docker-compose | Reproducible demo |

## 9. Performance notes
- Routes hold ~12–16 stops; VND pass = O(n·k·L).
- τ tables: n = 200 ≈ 15 MB; n = 500 ≈ 96 MB.
- Warm up Numba (JIT) at API start so the demo has no first-call lag.