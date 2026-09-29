# Rules — TA-QPSO

## Claims and wording
- DO say "quantum-inspired classical optimisation". DON'T say quantum computer, qubits, quantum speedup, or "reduced complexity".
- DO label speed profiles "calibrated synthetic" unless live data is used.
- DON'T claim a Pareto front; say "presets".
- DON'T claim we beat PyVRP/KAYROS. Report every result, including losses.
- Every number shown in UI or slides must come from a saved run record (instance, config, seed, commit hash).

## Modelling
- DO use stepwise edge speeds (IGP). DON'T invent slot travel times directly.
- DO run the FIFO check in the build; a failure stops the pipeline.
- DO keep travel time as the primary objective. Normalise D and C by the nearest-neighbour reference.
- DON'T use v/c or BPR volumes; we model speeds, not flows.
- DON'T use Uber Movement (discontinued) or EMFAC-HK (wrong region).
- DO enforce capacity by construction in Split; never repair infeasible solutions afterwards.

## Solver
- DO keep keys in [0,1] (reflect + clip); floor u at 1e-12. No `exp()` in the decoder.
- DON'T use PyVRP (or any external solver) inside TA-QPSO. Baseline only.
- DO make QPSO, PSO, GA and random restart differ ONLY in the optimizer step. Same seeds, decoder, VND, budget, tuning grid.
- DO write back VND results into keys.
- DO keep the solver anytime: best-so-far must be available at any moment.
- DON'T use a QPSO shortest-path module; shortest path = TD-Dijkstra only.

## Fair benchmarking
- Same machine, single thread, wall-clock budget, 20 seeds (30 for n ≤ 100).
- Score every solver with `sim/simulator.py`; on Poryos also with the official checker.
- Use Wilcoxon signed-rank + Holm correction + A12. No t-tests on non-normal data.
- Never tune on test instances. Tuning set ≠ evaluation set.

## Code
- Python 3.11, type hints everywhere, ruff + mypy clean, pre-commit on.
- Hot paths (IGP, evaluate, Split, VND moves) in Numba `@njit` on NumPy arrays. DON'T use Python dicts, objects or NetworkX in hot loops.
- DON'T use global random state. Pass `np.random.Generator` explicitly.
- Config via YAML + pydantic; no magic numbers in code.
- Pure functions in `core/`, `solver/`, `traffic/`; I/O only in `bench/`, `store/`, `api/`.
- One solve = one process, one thread. No hidden parallelism inside a run.
- Log with `logging`, not `print`. Store run records as JSON.
- Secrets (traffic API keys) only via environment variables; never committed.

## Testing (must pass before merge)
- FIFO on all pairs; Split vs brute force (n ≤ 8); VND never worsens or breaks feasibility; TD-Dijkstra = static Dijkstra at free flow; simulator vs Poryos checker; MILP on known optima; keys bounds/NaN test.
- Every bug fix adds a test.

## Frontend
- React + TS strict mode; Zustand for state; Tailwind with design tokens only.
- DON'T put quantum imagery (atoms, Bloch spheres, glowing particles).
- DON'T block the UI during solves; use WebSocket updates.
- DO handle offline: pre-built scenarios, cached tiles where possible.

## Data and licensing
- Attribute OpenStreetMap (ODbL) on the map and in docs; Poryos2026 is ODbL, KAYROS MIT.
- Raw and processed data are gitignored; provide `make data` scripts instead.

## Git
- Branch per feature; PR with passing CI; conventional commits.
- Tag the commit used for every reported result.