# Phases — TA-QPSO

Rule: no phase starts until the previous gate passes. Feature freeze after Phase 6.

## Phase 0 — Idea submission
- Tasks: finalise idea PPT from Proposal v3; one map screenshot of routes in the Delhi zone; confirm portal deadline.
- Deliverable: submitted idea.
- Gate: team review done; every claim matches PRD non-goals.

## Phase 1 — Setup (2–3 days)
- Tasks: repo skeleton (architecture.md tree), pyproject, ruff/mypy/pytest, pre-commit, Docker, configs, Makefile.
- Deliverable: `make test` and `make run-api` work on an empty app.
- Gate: CI green.

## Phase 2 — Static core (week 1–2)
- Tasks: instance + solution models; static evaluate; keys; Split; VND with candidate lists; seeds; QPSO optimizer; runner (anytime); CVRPLIB loader; MTZ MILP.
- Deliverable: TA-QPSO solves CVRPLIB A/B and X n ≤ 200 with static times.
- Gate: 100% feasible; Split matches brute force; gap to MILP measured for n ≤ 15; keys bounds test passes.

## Phase 3 — Traffic layer (week 2–3)
- Tasks: OSMnx Delhi graph builder; road-class speed profiles + calibration notes; IGP edge propagation; pair paths + inverted index; τ tables; FIFO check; TD evaluate/Split/VND; ground-truth simulator; Poryos2026 loader + checker hook.
- Deliverable: TD solver on Delhi and Poryos instances.
- Gate: FIFO passes on all pairs; simulator agrees with Poryos checker; optimiser-table vs simulator gap measured.

## Phase 4 — Baselines and experiments E1–E3 (week 3–4)
- Tasks: PSO, random-key GA, random restart optimizers; PyVRP adapter; experiment configs; stats (Wilcoxon, Holm, A12); plots.
- Deliverable: result tables, convergence curves, ablation (no VND, random restart + VND, QPSO + VND, + write-back).
- Gate: E1–E3 reproducible from one command; all solvers scored by the same simulator.

## Phase 5 — Dynamic and shortest path (week 4–5)
- Tasks: TD-Dijkstra; incident model; affected-pair re-pathing; vehicle states + next-stop commitment; fallback B0; warm-start QPSO; fleet-aware Split; stability penalty μ; baselines B1–B3; E4.
- Deliverable: incident scenarios with latency and quality results.
- Gate: fallback < 1 s; streamed improvements; E4 tables done.

## Phase 6 — API and scaling (week 5)
- Tasks: FastAPI endpoints, job manager, WebSocket streaming, Numba warm-up; E5 scaling runs (50–500).
- Deliverable: OpenAPI schema; scaling chart.
- Gate: end-to-end API demo via curl; **feature freeze**.

## Phase 7 — Dashboard and demo (week 5–6)
- Tasks: Plan, Incident, Benchmark, Path pages per design.md; scenario loader; offline fallback video.
- Deliverable: 3-minute live demo script rehearsed.
- Gate: demo runs twice in a row with no errors, offline.

## Phase 8 — Stretch (only if time remains, in order)
1. Time windows (Poryos TDVRPTW)
2. n = 500 full experiment set
3. Live traffic mode (HERE/TomTom)
4. Emissions (COPERT)
5. KAYROS reference runs

## Phase 9 — Documentation (parallel from Phase 4, closed at the end)
- Formulation, algorithm, experiments, limitations, reproduction guide; reference list verified.
- Gate: a teammate reproduces one table from README alone.

## Ownership template
| Area | Owner |
|---|---|
| Solver core (Phase 2) | |
| Traffic + simulator (Phase 3) | |
| Experiments + stats (Phase 4) | |
| Dynamic + paths (Phase 5) | |
| API + frontend (Phases 6–7) | |