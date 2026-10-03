# Implementation Plan — Tempo

SIH 2026 · PS 26137 · Derived from `PRD.md`, `architecture.md`, `phases.md`, `rules.md`, `design.md`.

This plan turns the docs into concrete build steps. It does not change scope. Where the docs are silent, the choice made here is marked **[Decision]** and can be revisited; where the docs leave something open, it is marked **[Open]** and carried to §14.

Source-of-truth order if anything conflicts: `rules.md` > `PRD.md` > `architecture.md` > `design.md` > `phases.md` > this plan.

---

## 0. How to use this plan

- Work phase by phase. **No phase starts until the previous gate passes** (phases.md). **Feature freeze after Phase 6.**
- Each phase lists: goal, tasks (with target files from the architecture tree), tests, and the gate checklist.
- Every task cites the feature / requirement it serves (F#, FR#, G#, NFR) so coverage can be audited (§13).
- Every rule in `rules.md` is enforced either by a test, a lint/CI check, or a review checklist item (§12).

---

## 1. Conventions that apply to every phase

| Topic | Convention | Source |
|---|---|---|
| Language | Python 3.11, type hints everywhere, ruff + mypy clean | rules.md · Code |
| Hot paths | IGP, evaluate, Split, VND moves in Numba `@njit` on NumPy arrays; no dicts/objects/NetworkX inside | rules.md · Code |
| Randomness | No global RNG. Every function needing randomness takes `rng: np.random.Generator` | rules.md · Code |
| Config | YAML + pydantic (`taqpso/config.py`); no magic numbers in code — every constant (α schedule, k=15, stall=30, re-randomise 30%, u floor 1e-12, budgets, swarm size, preset weights, congestion threshold 0.5) lives in `configs/default.yaml` | rules.md · Code |
| Purity | `core/`, `solver/`, `traffic/` are pure (no file/network I/O). I/O only in `bench/`, `store/`, `api/` (plus `graph/builder.py` build step and `experiments/` scripts) | rules.md · Code |
| Threads | One solve = one process, one thread. Set `NUMBA_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1` in the job worker and benchmark runner | rules.md · Code, FR4 |
| Logging | `logging` only, no `print` (ruff rule `T20`) | rules.md · Code |
| Run records | Every run saves JSON: instance id/hash, full resolved config, seed, solver, budget, commit hash, machine info, metrics, convergence trace | rules.md · Claims, FR6 |
| Units | Internal: seconds, metres. UI: min, km, % | design.md · Copy |
| Git | Branch per feature, conventional commits, PR with green CI, tag the commit of every reported result | rules.md · Git |
| Secrets | Traffic API keys only via env vars; `.env` gitignored | rules.md · Code |

---

## 2. Phase 0 — Idea submission

**Goal:** submitted idea that matches PRD non-goals.

Tasks
1. Finalise idea PPT from Proposal v3.
2. Produce one map screenshot of routes in the Delhi zone (can be a static mock from an early OSMnx plot; label profiles "calibrated synthetic").
3. Confirm portal deadline.
4. Wording pass against `rules.md · Claims`: "quantum-inspired classical optimisation"; no quantum computer / qubits / speedup / reduced complexity; "presets" not Pareto front; no claim of beating PyVRP/KAYROS.

**Gate:** team review done; every claim checked against PRD §4 Non-goals and rules.md Claims.

---

## 3. Phase 1 — Setup (2–3 days)

**Goal:** `make test` and `make run-api` work on an empty app; CI green.

### 3.1 Tasks
1. `git init` (repo is not yet under git), `.gitignore` covering `data/`, `results/`, `.env`, `node_modules/`, `__pycache__/`, `.venv/`.
2. Create the full folder tree from architecture.md §4 with empty modules / `__init__.py` so imports resolve.
3. `backend/pyproject.toml` with **pinned** dependencies (NFR Reproducibility):
   - runtime: numpy, numba, scipy, pydantic v2, pydantic-settings, pyyaml, fastapi, uvicorn[standard], highspy (and/or ortools), pyvrp, pandas, matplotlib, osmnx (build extra only)
   - bench extra: mamut-routing-lib (Poryos2026), optional kayros
   - dev: pytest, pytest-timeout, hypothesis, ruff, mypy, pre-commit, httpx (API tests)
   - Use a lock file (`uv lock` or `pip-tools`) committed to git.
4. `ruff` config (incl. `T20` no-print, `NPY` rules), `mypy --strict` for `taqpso/` (Numba kernels can carry targeted ignores), `.pre-commit-config.yaml` (ruff, ruff-format, mypy, end-of-file, no large files).
5. `taqpso/config.py`: pydantic models + YAML loader with override merging (`default.yaml` ← experiment yaml ← CLI/API overrides). Resolved config is hashable and serialisable (needed for run records).
6. `configs/default.yaml` skeleton (see §3.2), `configs/delhi_zone.yaml` skeleton, `configs/experiments/e1.yaml … e5.yaml` placeholders.
7. `taqpso/api/main.py`: FastAPI app with `GET /health` only.
8. `Makefile` targets: `setup`, `data`, `build-graph`, `test`, `lint`, `run-api`, `run-ui`, `exp-all` (+ `exp-e1` … `exp-e5`). `make data` downloads/builds raw + processed data (data is never committed — rules.md Data).
9. `docker-compose.yml`: `api` (Python 3.11 slim, pinned deps) and `ui` (Node LTS, Vite build served statically); volume-mount `data/` and `results/`.
10. Frontend scaffold: Vite + React + TS strict, Tailwind, Zustand, react-leaflet, Recharts; `styles/tokens.css` with the design.md §4 tokens (light + dark) — Tailwind theme reads only these tokens.
11. CI (GitHub Actions): ruff, mypy, pytest (fast suite), frontend `tsc --noEmit` + lint + build.
12. `store/results.py` minimal: `RunRecord` pydantic model + `save_run()` that captures commit hash (`git rev-parse HEAD`, dirty flag) and machine info.

### 3.2 `configs/default.yaml` keys (initial)
```yaml
time:        { slot_minutes: 15, n_slots: 96 }
swarm:       { size: <tbd by tuning>, alpha_start: 1.0, alpha_end: 0.5 }
qpso:        { u_floor: 1.0e-12 }
stall:       { iterations: 30, reinit_fraction: 0.30 }
vnd:         { candidate_k: 15, neighbourhoods: [relocate, swap, two_opt, two_opt_star, or_opt] }
budget_s:    { plan_n100: 30, plan_n200: 60, reopt: 10 }
objective:
  congestion_ratio_threshold: 0.5
  presets:
    fastest:        { w_T: 1.0, w_D: 0.0, w_C: 0.0 }
    balanced:       { w_T: <tbd>, w_D: <tbd>, w_C: <tbd> }
    low_congestion: { w_T: <tbd>, w_D: <tbd>, w_C: <tbd> }
reopt:       { warm_fraction: 0.5, stability_mu: 0.0 }
incident:    { blocked_factor: 0.1, heavy_factor: 0.4 }
```
Preset weights **[Decision]**: T is always the dominant term (rules.md Modelling); exact values are chosen on the tuning set in Phase 4 and frozen.

### 3.3 Gate checklist
- [ ] `make test` passes (placeholder test).
- [ ] `make run-api` serves `/health` and `/docs`.
- [ ] `docker compose up` brings up API + UI shell.
- [ ] CI green on main.

---

## 4. Phase 2 — Static core (week 1–2)

**Goal:** TA-QPSO solves CVRPLIB A/B and X with n ≤ 200 using static travel times. (F3, F6-MILP, FR1, FR3, FR6)

The static case is implemented as the **TD machinery with a single constant slot** wherever possible, so Phase 3 extends rather than rewrites. Data layout is decided now: everything the kernels touch is a NumPy array.

### 4.1 Core models — `core/`
1. `instance.py` — `Instance`: depot index 0, customers 1..n, `demand: int32[n+1]`, `Q`, optional `K` (F15), `service_time: float32[n+1]`, `depart_s`, coordinates. Validation: every demand ≤ Q, else error "Demand exceeds capacity at customer i" (design.md §6 Error copy).
2. `solution.py` — `Solution`: list of routes (customer ids); `to_giant_tour()`, `from_giant_tour()`; `validate(inst)` checks FR1 (each customer exactly once, load ≤ Q, K respected if set). Validation runs on every solution returned by any solver.
3. `evaluate.py` — `@njit` route propagation: given a route and a travel-time table `tau[i,j,slot]` + interpolation, returns arrival times, route duration, distance, congestion minutes. Static mode = one slot.
4. `objective.py` — computes T (total travel time, primary), D (distance), C (congestion exposure = minutes driven on edges with speed ratio < 0.5), and `J = w_T·T/T_ref + w_D·D/D_ref + w_C·C/C_ref` where refs come from the **nearest-neighbour** solution of the same instance (rules.md Modelling). Presets from config (F4).

### 4.2 Solver — `solver/`
5. `keys.py` — `decode_order(keys) -> giant tour` (argsort, stable tie-break by index); `reflect_clip(x)` into [0,1] (reflect then clip for safety); `write_back(keys, sol)`: take the sorted multiset of the particle's existing key values and reassign them in the order of the improved giant tour, so the decoded order equals the VND result exactly. **No `exp()` anywhere in the decoder.**
6. `split.py` — Bellman/Prins Split for unlimited fleet, `@njit`, O(n·B) where B = max customers per route bounded by Q. Each route departs the depot at `depart`, so route cost is independent of other routes → the DP stays exact under TD (Phase 3). Capacity is enforced by construction (rules.md: never repair afterwards).
7. `split_fleet.py` — fixed-K variant, O(K·n·B) (F15). The "vehicles-in-field" variant is added in Phase 5.
8. `vnd.py` — neighbourhoods relocate, swap, 2-opt, 2-opt*, or-opt; granular candidate lists (k = 15 nearest by travel time at departure slot); first-improvement; **suffix re-evaluation** (only re-propagate from the changed position onward — required for TD). Every move is checked for capacity before acceptance; a move is accepted only if it strictly improves J. Precompute route prefix loads.
9. `seeds.py` — nearest neighbour and sweep constructions; also used for the NN reference in `objective.py` and as initial particles.
10. `optimizers/base.py` — `Optimizer` Protocol and `Swarm` dataclass exactly as architecture.md §5 (`init(n, rng, seeds) -> Swarm`, `step(swarm, progress, rng) -> keys (M×n)`).
11. `optimizers/qpso.py` — the **only** QPSO-specific code (architecture.md §2 step 6):
    - `mbest = mean(pbest)`; per dimension `φ ~ U(0,1)`, `P_d = φ·pbest_d + (1−φ)·gbest_d`
    - `x_d ← P_d ± α·|mbest_d − x_d|·ln(1/u)`, sign ±with prob ½, `u ~ U(0,1)` floored at 1e-12
    - `α = α_start + (α_end − α_start)·progress` (1.0 → 0.5 in the first round; tuned 0.05 → 0.01 in `configs/tuned.yaml`; linear in elapsed budget fraction)
    - `reflect_clip` into [0,1]; assert no NaN.
12. `runner.py` — the anytime loop (architecture.md §2 steps 1–7) shared by every key-based optimizer:
    1. decode keys → giant tour; 2. Split; 3. VND; 4. write-back; 5. update pbest/gbest (and mbest via optimizer); 6. `optimizer.step`; 7. stall detection: 30 iterations without gbest improvement → re-randomise worst 30% of particles.
    - Wall-clock budget (`time.perf_counter`), checked between particle evaluations so overshoot is bounded.
    - `best_so_far()` always available (FR3); callback `on_improvement(t, cost, solution, diversity)` used later for streaming.
    - Convergence trace (t, best J, best T) recorded for every improvement.
    - Seeded with an explicit `np.random.Generator(PCG64(seed))`.

### 4.3 Benchmarks and exact reference
13. `bench/cvrplib.py` — read CVRPLIB `.vrp`/`.sol` (A, B, X sets); rounded Euclidean distances as static travel times; known BKS for gap reporting.
14. `baselines/milp.py` — MTZ CVRP formulation (HiGHS via highspy; CP-SAT alternative) for n ≤ 15 (F6). Returns optimum or best bound + gap with a time limit. Used for gap-to-optimum.

### 4.4 Tests (must pass)
- `test_split.py` — Split equals brute-force optimal partition of a fixed giant tour for all random tours with n ≤ 8 (hypothesis), unlimited and fixed K.
- `test_vnd.py` — each neighbourhood never worsens J and never breaks feasibility (property tests on random instances).
- `test_qpso_bounds.py` — after many steps with extreme inputs (pbest = gbest, x at bounds, u→0), keys stay in [0,1] and contain no NaN/Inf.
- `test_milp.py` — MILP reproduces known optima on tiny instances (hand-made + small CVRPLIB-derived subsets).
- `test_solution.py` (extra) — validator catches duplicate/missing customers and overload.
- `test_keys.py` (extra) — `decode_order(write_back(keys, sol)) == sol.giant_tour`.
- Determinism test: same (instance, config, seed) with an iteration budget → identical result (FR6).

### 4.5 Gate checklist
- [ ] 100% feasible solutions on all CVRPLIB A/B and X (n ≤ 200) runs.
- [ ] Split matches brute force.
- [ ] Gap to MILP measured for n ≤ 15 (table saved as run records).
- [ ] Keys bounds test passes.

---

## 5. Phase 3 — Traffic layer (week 2–3)

**Goal:** TD solver on Delhi and Poryos2026 instances. (F1, F2, F5, F12, G1, FR2)

### 5.1 Road graph — `graph/builder.py` (F1)
1. Read `configs/delhi_zone.yaml` (bbox, `network_type="drive"`, default speeds per road class). **[Open]** zone choice — pick one compact zone with mixed arterial/residential roads and a depot candidate.
2. OSMnx download → largest strongly connected component → CSR arrays saved to `data/processed/graph.npz`: node coords, edge `from`, `to`, `length_m`, `freeflow_mps`, `road_class` (int enum). OSMnx is used **only here**.
3. Fill missing `maxspeed` from road-class defaults; record the fill rate.

### 5.2 Speed profiles — `graph/profiles.py`
4. Per road class, 96 factors (15-min slots) in `data/processed/profiles.json` (`{road_class: [96 factors]}`).
5. Calibration from published Delhi data (peak/off-peak speed ratios); write `docs/calibration-notes.md` with sources. Label everywhere as **"Calibrated time-of-day profile (synthetic)"**.
6. **Do not** use Uber Movement, EMFAC-HK, v/c ratios or BPR (rules.md Modelling). Speeds only.

### 5.3 IGP propagation — `traffic/igp.py` (Numba)
7. `edge_travel_time(length, freeflow, factors[96], t_enter)` — Ichoua–Gendreau–Potvin: speed is stepwise constant per slot; distance is consumed slot by slot across boundaries. This is FIFO by construction. Never invent slot travel times directly.
8. `path_travel_time(edge_ids, t0)` — chained edge propagation. Also returns distance and congestion seconds (time spent where speed/freeflow < 0.5).
9. Time beyond the 96-slot horizon: **[Decision]** wrap modulo 24 h (consistent with daily profiles); documented in `docs/`.

### 5.4 Pair tables — `traffic/pair_tables.py` (F2)
10. Map depot/customers to nearest graph nodes.
11. Pair paths = **free-flow fastest paths** via `scipy.sparse.csgraph.dijkstra` from each of the n+1 origins (PRD §11). Save `paths.pkl` (edge-id arrays).
12. Inverted index `edge_id → list of pairs (i,j)` in `inv_index.pkl` (used for incidents in Phase 5).
13. `tau.npy`: float32 `(n+1, n+1, 96)` = IGP path travel time for departure at each slot start. Also `dist` (n+1, n+1) and congestion table `(n+1, n+1, 96)`.
14. Interpolation for arbitrary t: linear between slot-start breakpoints (arrival function stays non-decreasing when samples are FIFO, so interpolation keeps FIFO).
15. Memory check: n = 200 ≈ 15 MB, n = 500 ≈ 96 MB (≤ 100 MB NFR).

### 5.5 FIFO check — `traffic/fifo_check.py` (FR2)
16. For every pair and every adjacent breakpoint: `τ(t+Δ) − τ(t) ≥ −Δ` (with float tolerance). Called inside the build pipeline; **a failure raises and stops the pipeline** (`make build-graph` / instance build exits non-zero).

### 5.6 TD solver
17. `core/evaluate.py` — TD propagation using the interpolated τ tables (service times added at customers).
18. `solver/split.py` — TD-Split: each route starts at `depart`, so route cost is computed by forward propagation along the giant-tour segment; DP remains exact.
19. `solver/vnd.py` — TD moves: suffix re-evaluation from the first changed position; candidate lists from τ at the departure slot.

### 5.7 Ground-truth simulator — `sim/simulator.py` (F5)
20. `simulate(sol, graph, speeds, incidents, depart) -> Metrics` (architecture.md §5): walks every route **edge by edge** with IGP on the actual graph (not the pair tables), applying incident factors. Returns T, D, C, J, K, per-route times/loads, feasibility.
21. All solvers — TA-QPSO, PSO, GA, random restart, PyVRP, MILP, KAYROS — are scored only by this function (FR4, rules.md Benchmarking).
22. Report the optimiser-table vs simulator gap (difference caused by table interpolation / path choice).

### 5.8 Poryos2026 — `bench/poryos.py` (F12, P1)
23. Loader via mamut-routing-lib (clone into `data/raw/`); convert to `Instance` + graph/speeds or travel-time functions as provided.
24. Hook the official checker; `test_simulator.py` asserts simulator == checker within tolerance on provided solutions.

### 5.9 Scenario generation
25. `data/scenarios/*.json`: Delhi demo instances (incl. design.md §9: 1 depot, 100 customers, 8 vehicles, 17:30 departure) and incident scripts. Built by a `make data` step with a fixed seed.

### 5.10 Tests
- `test_fifo.py` — FIFO on all pairs of every built instance; plus a unit test that IGP on a synthetic edge with a speed drop is FIFO.
- `test_simulator.py` — agrees with Poryos checker; agrees with τ-table evaluation at free-flow within tolerance.
- IGP unit tests: constant speed ⇒ length/speed; crossing one slot boundary hand-computed.

### 5.11 Gate checklist
- [ ] FIFO passes on all pairs (G1).
- [ ] Simulator agrees with Poryos checker.
- [ ] Optimiser-table vs simulator gap measured and recorded.
- [ ] TD solver runs on Delhi and Poryos instances, 100% feasible.

---

## 6. Phase 4 — Baselines and experiments E1–E3 (week 3–4)

**Goal:** reproducible result tables, convergence curves, ablation; all solvers scored by the same simulator. (F6, F11, G2, G3, FR4, FR7)

### 6.1 Optimizers — `solver/optimizers/` (differ ONLY in step 6)
1. `pso.py` — standard inertia-weight PSO on keys (velocity clamp, reflect into [0,1]).
2. `ga.py` — random-key GA (BRKGA-style: elite, biased uniform crossover, mutants) producing M new key vectors.
3. `random_restart.py` — new uniform random keys each step.
4. All use the same `runner.py`, seeds (NN + sweep), decoder, Split, VND, write-back, budget and the **same tuning grid size** (rules.md Solver). A test asserts each optimizer module only implements `init`/`step`.

### 6.2 External baselines — `baselines/`
5. `pyvrp_adapter.py` — static matrix (free-flow or departure-slot times) in, routes out; scored by the simulator. Never called from inside TA-QPSO.
6. MILP from Phase 2 for n ≤ 15.

### 6.3 Experiment infrastructure — `backend/experiments/`
7. A single driver reads `configs/experiments/eX.yaml` (instances, solvers, budgets, seeds), runs each (instance, solver, seed) in its own single-threaded process, scores with `simulate`, saves run records to `results/`.
8. Seeds: 20 per configuration, **30 for n ≤ 100** (rules.md Benchmarking).
9. Tuning: separate tuning set (disjoint instances) for swarm size, preset weights, GA/PSO params; same grid size for every optimizer; frozen params written to `default.yaml` before evaluation runs. **Never tune on test instances.**
10. `stats.py` — Wilcoxon signed-rank (paired by instance/seed), Holm correction, Vargha–Delaney A12. No t-tests.
11. `plots.py` — convergence median + 95% band, boxplots, scaling plots (PNG + SVG, FR7); CSV/JSON exports (FR7).

### 6.4 Experiments
| ID | Question | Content | Outputs |
|---|---|---|---|
| E1 Correctness | Is the solver correct and how far from optimal? | FIFO report, feasibility rate, gap to MILP (n ≤ 15) and to CVRPLIB BKS; simulator vs checker agreement | gap table |
| E2 QPSO vs classical | Does QPSO help? (G2) | QPSO vs PSO vs GA vs random restart at equal wall-clock budget, same seeds; PyVRP as reference. **Ablation:** no VND · random restart + VND · QPSO + VND · QPSO + VND + write-back | median, best, time-to-target, A12, Holm-p, convergence bands, boxplots |
| E3 Traffic value | Does TD planning help? (G3) | Plan with static (free-flow) vs TD tables; both scored by simulator under heavy traffic; departure times incl. 10:00 vs 18:00 (F14) | realised travel-time reduction table |

`make exp-e1`, `exp-e2`, `exp-e3` regenerate each from one command.

### 6.5 Gate checklist
- [ ] E1–E3 reproducible from one command each.
- [ ] All solvers scored by `sim/simulator.py` (and Poryos checker on Poryos).
- [ ] Ablation table complete; losses reported as well as wins.
- [ ] Results tagged with commit.

Phase 9 (documentation) starts in parallel from here.

---

## 7. Phase 5 — Dynamic and shortest path (week 4–5)

**Goal:** incident scenarios with latency and quality results. (F7, F8, F9, F13, G4, FR5)

### 7.1 TD shortest path — `paths/td_dijkstra.py` (F9)
1. Earliest-arrival Dijkstra on the CSR graph with IGP edge costs (valid because FIFO). `@njit` with array-based binary heap.
2. `td_shortest_path(graph, speeds, src, dst, t0) -> Path` (edges, arrival time, distance). No QPSO shortest path (rules.md Solver).
3. Optional k alternatives for the Path page (penalty method) — P1-level nicety.
4. `test_td_dijkstra.py` — equals static `scipy` Dijkstra at free flow.

### 7.2 Incident model — `traffic/incidents.py` (F7)
5. `Incident{edges | polygon, factor, t_start, t_end}`; polygon → edges by geometry intersection. Severity presets Blocked 0.1 / Heavy 0.4 / Custom (design.md).
6. Apply as extra speed breakpoints on affected edges (piecewise factor inside the window) — keeps IGP and FIFO.
7. Affected pairs via inverted index → re-run Dijkstra from their origins with incident-aware costs → recompute those τ rows (and FIFO-check them).

### 7.3 Vehicle state — `dynamic/vehicle_state.py`
8. At incident time `t_e` (simulated clock), per vehicle: current edge + elapsed time on it, **committed next stop** (destination of current leg — FR5: never diverted), ETA, remaining load, remaining customers.

### 7.4 Fallback B0 — `dynamic/fallback.py`
9. Keep each vehicle's remaining sequence; re-route legs that cross incident edges with TD-Dijkstra detours. Target **< 1 s** (G4); streamed immediately as "Safe plan".

### 7.5 Warm re-optimisation — `dynamic/reopt.py` + `solver/split_fleet.py`
10. Fleet-aware Split: vehicles start from their own (position, time, load) states; remaining customers are assigned across vehicles in the field (+ depot vehicles if K allows).
11. Warm-start swarm: 50% incumbent + noise, 50% random (config `warm_fraction`).
12. Stability penalty μ (F13): J + μ·(number of customers whose vehicle changed / changed stops); produce the quality-vs-stability curve.
13. Streaming via runner callbacks; first improvement target within 3 s; default budget 10 s (NFR).

### 7.6 Baselines B0–B3 and E4
14. B0 = nav-app detour (fallback). B3 = PyVRP snapshot (re-solve the remaining problem on a static snapshot). **[Open]** B1 and B2 are not defined in the docs; proposed: B1 = cold-start TA-QPSO (no warm start), B2 = warm-start QPSO without fleet-aware Split or with μ = 0. Confirm before E4 runs.
15. E4 Incident recovery: per scenario, fallback latency, time to first improvement, time to within 1% of best, final J vs B0–B3, customers moved, quality-vs-stability curve.

### 7.7 Gate checklist
- [ ] Fallback < 1 s on demo scenario (measured, recorded).
- [ ] Improvements streamed through callback.
- [ ] No vehicle diverted from its current leg's destination (test).
- [ ] E4 tables done.

---

## 8. Phase 6 — API and scaling (week 5)

**Goal:** end-to-end API demo via curl, OpenAPI schema, scaling chart. **Feature freeze at the gate.** (F10 backend, F11, G5, NFRs)

### 8.1 API — `api/`
1. `schemas.py` — pydantic v2 models for every request/response; solution JSON per architecture.md §7: `{routes, depart, metrics: {T, D, C, J, K}, solver, seed, budget}`.
2. `jobs.py` — `ProcessPoolExecutor` job manager; one solve per process, single-threaded; job states map to design StatusBadge (Idle / Solving / Safe plan / Optimising / Done / Error); stop/cancel; incumbent pushed to an async queue per job.
3. `routes/` endpoints (architecture.md §6):
   | Method | Path | File |
   |---|---|---|
   | GET | /scenarios | instances.py |
   | POST | /instances | instances.py |
   | POST | /solve | solve.py |
   | GET | /jobs/{id} | solve.py |
   | WS | /jobs/{id}/stream | solve.py — `{t, cost, routes, diversity}` |
   | POST | /incidents | incidents.py — returns new job_id; first message = fallback plan |
   | GET | /paths | paths.py |
   | GET | /congestion?slot | paths.py or instances.py — edge speed ratios |
   | GET | /results | results.py |
   Plus `POST /jobs/{id}/stop` **[Decision]** for the Stop button (design.md §6).
4. Re-scoring for the time-of-day slider: `POST /jobs/{id}/rescore?depart=` **[Decision]** — re-simulates the current plan at another departure (F14).
5. Numba warm-up at API startup (JIT all kernels on a tiny instance) so the demo has no first-call lag.
6. Every solution served comes from a saved run record (rules.md Claims).
7. Export OpenAPI; generate `frontend/src/api/types.ts` from it (`openapi-typescript`).
8. API tests with `httpx`/TestClient incl. WebSocket stream.

### 8.2 E5 Scaling
9. n = 50, 100, 200 (core), 500 (stretch, F19): runtime, memory (tables + process RSS), quality over time. `make exp-e5`; scaling chart.

### 8.3 Gate checklist
- [ ] End-to-end demo via curl: create instance → solve → stream → incident → fallback + improvements → path query.
- [ ] OpenAPI schema committed; frontend types generated.
- [ ] Scaling chart produced; n = 100 in 30 s and n = 200 in 60 s budgets met; memory ≤ 100 MB tables at n = 500 (if run).
- [ ] **Feature freeze.**

---

## 9. Phase 7 — Dashboard and demo (week 5–6)

**Goal:** dashboard per design.md; 3-minute demo runs twice in a row offline with no errors. (F10, F14, design.md all sections)

### 9.1 Shell
1. Layout per design.md §2: top bar (logo · Plan | Incident | Benchmark | Path | About · scenario), left panel 320 px, map, right panel 360 px, collapsible bottom strip (solver log / status / timeline). Tablet: right panel → bottom sheet. Mobile: full-screen map, tabbed bottom sheet, view-only.
2. Tokens from design.md §4 only (light/dark), Inter + JetBrains Mono (self-hosted for offline), 4 px spacing, 8 px radius, shadows only on floating panels.
3. `api/client.ts`, `api/ws.ts` (reconnect), `state/store.ts` (Zustand: scenario, instance, job, incumbent, before/after, UI state).
4. Map: react-leaflet with CARTO Positron / Dark Matter, OSM attribution always visible; tile caching for offline (service worker cache of the demo zone).

### 9.2 Components (design.md §5)
KpiCard, RouteChip, StatusBadge, ConvergenceChart, DiffPanel, Toast; map layers MapView, RouteLayer (Okabe–Ito palette, dashed after 8, chevrons every ~300 m), CongestionLayer (ramp ≥0.8 / 0.6–0.8 / 0.4–0.6 / <0.4, width by road class), IncidentLayer (hatched red), VehicleMarker (ETA badge).

### 9.3 Pages
- **Plan** (§3.1): scenario select, CSV upload / click-to-add customers, depot, K, Q, departure, preset, solver (TA-QPSO default; PSO, GA, Random, PyVRP), budget 10–120 s, seed, Solve↔Stop; KPI strip (Travel time, Distance, Congestion exposure, Vehicles, Load use %); route list; live convergence; time-of-day slider 06:00–22:00 in 15-min steps re-scores plan + updates congestion.
- **Incident** (§3.2): draw blockage (edges/polygon), severity, start, duration; Simulate incident (red outline). Sequence: hatched area + frozen vehicles with ETA → dashed fallback "Safe plan" within 1 s → solid streaming "Optimising… x s" → "Re-optimised in X s". DiffPanel with deltas, moved customers, changed-stop count, μ slider; ghost-route toggle for B0 / B3.
- **Benchmark** (§3.3): tabs Correctness, QPSO vs classical, Traffic value, Incident recovery, Scaling; one-line takeaway above each chart; Download CSV/PNG; table columns instance, n, method, median, best, gap %, time-to-target. Data comes only from saved run records via `/results`.
- **Path** (§3.4): click origin/destination, departure time, TD fastest path vs free-flow path, travel time; optional alternatives.
- **About** (§3.5): 7-step loop diagram with QPSO step highlighted (plain SVG, **no quantum imagery**), model summary, data sources, licences (OSM ODbL, Poryos2026 ODbL, KAYROS MIT), limitations; copy "Quantum-inspired optimisation (runs on a normal CPU)".

### 9.4 States, copy, accessibility
- States per design.md §6 (Empty, Loading graph skeleton, Solving, Error with cause, Offline banner).
- Copy per §7: units always shown; congestion exposure definition; speed source label.
- Accessibility per §8: contrast ≥ 4.5:1; routes distinguishable by colour + dash + hover label; keyboard Tab, Enter = Solve, I = Incident tool, Esc cancels drawing; data-table toggle on every chart.
- UI never blocks during solves (WebSocket only).

### 9.5 Demo
- Pre-built scenario (design.md §9): Delhi zone, 1 depot, 100 customers, 8 vehicles, 17:30; incident arterial blocked 18:00–19:00. Expected: fallback < 1 s, streamed improvement, before/after deltas, nav-app detour comparison.
- Offline: scenarios + precomputed tables bundled; tiles cached; fallback screen-recorded video.
- 3-minute demo script written and rehearsed.

### 9.6 Gate checklist
- [ ] Demo runs twice in a row, offline, with no errors.
- [ ] Every number on screen traces to a run record.

---

## 10. Phase 8 — Stretch (only if time remains, in this order)
1. Time windows (Poryos TDVRPTW) — F16: extend evaluate/Split with TW feasibility (by construction).
2. n = 500 full experiment set — F19.
3. Live traffic mode (HERE/TomTom free tier) — F17: keys via env vars; label "Live traffic".
4. Emissions (COPERT speed-based factors) — F18.
5. KAYROS anytime reference runs — F20, `baselines/kayros_adapter.py`.

## 11. Phase 9 — Documentation (parallel from Phase 4, closed at end)
- `docs/` additions: formulation, algorithm, experiments, limitations, calibration notes, reproduction guide; verified reference list.
- README: setup, `make data`, `make exp-*`, demo run.
- **Gate:** a teammate reproduces one table from the README alone.

---

## 12. Rules enforcement matrix

| Rule (rules.md) | Enforced by |
|---|---|
| FIFO check stops pipeline | `fifo_check` raises in build; `test_fifo.py`; CI |
| Capacity by construction, no repair | Split design; `Solution.validate` on every output; code review |
| Keys in [0,1], u ≥ 1e-12, no `exp()` in decoder | `test_qpso_bounds.py`; grep check in CI for `exp(` in `solver/keys.py`, `split*.py` |
| No external solver inside TA-QPSO | import-linter contract: `taqpso.solver` may not import `pyvrp`, `highspy`, `ortools`, `taqpso.baselines` |
| Optimizers differ only in step 6 | shared `runner.py`; test that optimizers expose only `init`/`step` |
| Write-back of VND results | `test_keys.py` round-trip; ablation toggles it explicitly |
| Anytime | runner test: `best_so_far()` callable at any iteration |
| No QPSO shortest path | only `paths/td_dijkstra.py` exists |
| Same simulator for all | experiment driver calls `simulate()` for every record |
| 20/30 seeds, Wilcoxon + Holm + A12, no t-tests | `stats.py`; experiment yaml validation |
| Tuning ≠ evaluation set | config validation asserts disjoint instance lists |
| Numba hot paths, no dicts/NetworkX | import-linter: `networkx`/`osmnx` only in `graph/builder.py`; review |
| No global RNG | ruff/grep check bans `np.random.seed`, `np.random.rand`, `random.` module in `taqpso/` |
| Config, no magic numbers | review checklist; constants in `default.yaml` |
| Pure modules | import-linter: `core/solver/traffic` cannot import `store/api/bench` or do I/O |
| One process, one thread | env vars set in worker + runner; timing tests on CI runner |
| logging not print | ruff `T20` |
| Run records with commit hash | `store/results.py`; UI/slides read only from records |
| Claims wording | PR template checklist; copy review before demo |
| No quantum imagery | design review |
| OSM attribution | always-on map attribution; About page |
| Data gitignored, `make data` | `.gitignore`; Makefile |
| Every bug fix adds a test | PR template |

---

## 13. Traceability — features to phases

| Feature | Pri | Phase | Main files | Test / evidence |
|---|---|---|---|---|
| F1 Road graph | P0 | 3 | graph/builder.py, profiles.py | graph.npz built by `make build-graph` |
| F2 TD tables + FIFO | P0 | 3 | traffic/igp.py, pair_tables.py, fifo_check.py | test_fifo.py |
| F3 TA-QPSO solver | P0 | 2–3 | solver/* | test_split, test_vnd, test_qpso_bounds |
| F4 Presets | P0 | 2 (weights 4) | core/objective.py | preset run records |
| F5 Simulator | P0 | 3 | sim/simulator.py | test_simulator.py |
| F6 Baselines PSO/GA/RR/PyVRP/MILP | P0 | 2 (MILP), 4 | optimizers/*, baselines/* | test_milp.py, E2 |
| F7 Incidents | P0 | 5 | traffic/incidents.py | E4 |
| F8 Dynamic re-opt | P0 | 5 | dynamic/* | fallback latency test, E4 |
| F9 TD-Dijkstra | P0 | 5 | paths/td_dijkstra.py | test_td_dijkstra.py |
| F10 Dashboard | P0 | 6–7 | api/*, frontend/* | demo gate |
| F11 Benchmark runner + stats | P0 | 4–6 | experiments/* | E1–E5 |
| F12 Poryos2026 | P1 | 3 | bench/poryos.py | test_simulator.py |
| F13 Stability μ | P1 | 5 | dynamic/reopt.py | quality-vs-stability curve |
| F14 Departure-time picker | P1 | 4 (E3), 6–7 | rescore endpoint, Plan slider | E3 |
| F15 Fixed fleet K | P1 | 2 | solver/split_fleet.py | test_split.py (fixed K) |
| F16 Time windows | P2 | 8 | evaluate, split | — |
| F17 Live traffic | P2 | 8 | traffic adapter | — |
| F18 Emissions | P2 | 8 | core/objective.py ext. | — |
| F19 n = 500 | P2 | 6 / 8 | experiments | E5 |
| F20 KAYROS | P2 | 8 | baselines/kayros_adapter.py | — |

Functional requirements: FR1 → Phase 2 validator; FR2 → Phase 3 FIFO; FR3 → Phase 2 runner; FR4 → Phase 4 driver + single-thread env; FR5 → Phase 5 vehicle state; FR6 → seeds + run records; FR7 → Phase 4 exports.

Goals: G1 → Phases 2–3; G2 → E2; G3 → E3; G4 → Phase 5 / E4; G5 → E5.

---

## 14. Open questions and decisions to confirm

| # | Item | Status / proposal |
|---|---|---|
| 1 | Fixed fleet K vs minimise vehicles | PRD default: optional K. Implement both (Split + split_fleet). |
| 2 | Which Delhi zone | **[Open]** decide before Phase 3 task 1. |
| 3 | Time windows before finale | Stretch (Phase 8 item 1) unless decided otherwise. |
| 4 | Baselines B1, B2 for E4 | **[Open]** proposal in §7.6. |
| 5 | Preset weights | Tuned on tuning set in Phase 4, T always dominant. |
| 6 | Swarm size, PSO/GA params | Tuned with equal grid size per optimizer in Phase 4. |
| 7 | Time beyond 24 h horizon | **[Decision]** wrap modulo 24 h. |
| 8 | Extra endpoints (`/jobs/{id}/stop`, `/jobs/{id}/rescore`) | **[Decision]** needed for Stop button and time-of-day slider. |
| 9 | Exact definitions of E1–E5 | Inferred from phases.md + design.md Benchmark tabs (§6.4, §7.6, §8.2). |

---

## 15. Risks

| Risk | Mitigation |
|---|---|
| Numba compile time hurts demo | Warm-up at API start; `cache=True` on kernels |
| QPSO shows no advantage | Expected possibility; report honestly (rules.md). Ablation still shows value of Split + VND + write-back |
| mamut-routing-lib / Poryos API differs from assumptions | Spike it at the start of Phase 3; checker agreement is a gate |
| OSM data gaps in maxspeed | Road-class defaults; report fill rate |
| Fallback > 1 s on large incidents | Inverted index limits re-pathing to affected pairs; TD-Dijkstra with early stop at destination |
| Offline demo failure | Bundled scenarios + cached tiles + recorded video |
| Timeline slip | Strict gates; P2 only in Phase 8; feature freeze after Phase 6 |
