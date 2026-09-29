# PRD — TA-QPSO: Traffic-Aware Quantum-Inspired Vehicle Routing

SIH 2026 · PS 26137 (Egreen Quanta) · Software · Transportation & Logistics

## 1. Problem
Urban delivery fleets plan routes on static travel times, but city travel times change through the day and after incidents. Capacitated vehicle routing (CVRP) is NP-hard, so heuristics are used in practice. The PS asks for a quantum-inspired metaheuristic (QPSO family) on a weighted road graph that minimises travel time, distance and congestion, is benchmarked against classical and exact methods, and scales to smart-city logistics.

## 2. Product summary
A web platform that:
1. Plans capacity-feasible delivery routes on a real Delhi road graph using time-of-day travel times.
2. Re-plans in seconds when an incident (blockage or slowdown) is injected.
3. Compares the quantum-inspired optimiser (QPSO) fairly against classical PSO, GA, random restart, PyVRP and exact references.

"Quantum-inspired" = classical computation using the QPSO sampling rule. No quantum hardware, no quantum speedup is claimed.

## 3. Goals
| ID | Goal | Measure |
|---|---|---|
| G1 | Correct time-dependent (TD) routing | FIFO test passes on all pairs; 100% feasible routes |
| G2 | Fair answer to "does QPSO help?" | QPSO vs PSO vs GA vs random restart, identical pipeline, Wilcoxon + effect size |
| G3 | Show the value of traffic-aware planning | Realised travel time: TD planning vs static planning |
| G4 | Fast incident recovery | Fallback plan < 1 s; time to within 1% of best |
| G5 | Scale | n = 200 core, n = 500 stretch, runtime and memory reported |

## 4. Non-goals
- Beating PyVRP on static CVRP or KAYROS on TD benchmarks.
- Theoretical complexity reduction claims.
- Full Pareto-front optimisation.
- Production-grade live traffic integration (optional demo mode only).
- Driver mobile app, payments, order management.

## 5. Target users
| User | Need | Primary screen |
|---|---|---|
| Fleet dispatcher (last-mile, e-commerce, pharmacy, food distribution) | Daily route plan that respects rush hour; quick re-plan when roads close | Plan view, Incident view |
| Smart-city / traffic planner | See how congestion and incidents affect delivery fleets | Plan view with congestion layer |
| Evaluator / researcher (SIH jury, OR reviewers) | Verify formulation, fairness and results | Benchmark view, Algorithm panel |

## 6. User stories
- As a dispatcher, I load today's customers and depot and get routes for my vehicles in under a minute.
- As a dispatcher, I choose a priority preset: Fastest, Balanced, Low-congestion.
- As a dispatcher, I pick a departure time and see how the plan changes between 10:00 and 18:00.
- As a dispatcher, I mark a road as blocked and immediately get a safe plan, then a better one within seconds.
- As a dispatcher, I see which customers moved to another vehicle after a re-plan.
- As a planner, I see road congestion by time of day on the map.
- As a user, I query the fastest road path between two points at a chosen departure time.
- As an evaluator, I see convergence curves and result tables comparing QPSO with classical methods at equal budget.
- As an evaluator, I see the gap to proven optima on small instances.

## 7. Features
Priority: P0 = must ship, P1 = should ship, P2 = stretch.

| ID | Feature | Priority |
|---|---|---|
| F1 | Road graph builder: OSMnx Delhi zone, free-flow speeds, 15-min speed profiles per road class | P0 |
| F2 | TD travel-time tables between customers (IGP model, FIFO-safe) with FIFO unit test | P0 |
| F3 | TA-QPSO solver: random keys → TD-Split → VND → write-back → QPSO update | P0 |
| F4 | Objective presets: Fastest, Balanced, Low-congestion (normalised objective) | P0 |
| F5 | Ground-truth simulator scoring every solver identically | P0 |
| F6 | Baselines: PSO, random-key GA, random restart, PyVRP, MILP (MTZ, n ≤ 15) | P0 |
| F7 | Incident injection: edges + speed factor + time window; re-pathing of affected pairs | P0 |
| F8 | Dynamic re-optimisation: next-stop commitment, instant fallback, warm-started QPSO | P0 |
| F9 | Time-dependent Dijkstra shortest-path module | P0 |
| F10 | Dashboard: map, routes, KPIs, incident button, before/after, live convergence | P0 |
| F11 | Benchmark runner + statistics + plots (experiments E1–E5) | P0 |
| F12 | Poryos2026 TDVRP loader + official checker scoring | P1 |
| F13 | Stability penalty μ and quality-vs-stability curve | P1 |
| F14 | Departure-time picker and time-of-day comparison | P1 |
| F15 | Fixed fleet size K (otherwise unlimited) | P1 |
| F16 | Time windows (TDVRPTW) | P2 |
| F17 | Live traffic mode (HERE/TomTom free tier) | P2 |
| F18 | Emissions estimate (COPERT speed-based factors) | P2 |
| F19 | n = 500 scale runs | P2 |
| F20 | KAYROS anytime run as reference | P2 |

## 8. Functional requirements
- FR1: Every returned solution visits each customer exactly once and respects capacity Q.
- FR2: Travel times satisfy FIFO; build fails if the FIFO test fails.
- FR3: Solver is anytime: best-so-far is always retrievable and streamed.
- FR4: All solvers run under the same wall-clock budget and seeds and are scored by the same simulator.
- FR5: Incident handling never moves a vehicle off its current leg's destination.
- FR6: Every run is reproducible from (instance, config, seed).
- FR7: Results export as CSV/JSON; plots as PNG/SVG.

## 9. Non-functional requirements
| Area | Target |
|---|---|
| Plan, n = 100 | Good solution in 30 s budget (single thread) |
| Plan, n = 200 | 60 s budget |
| Incident fallback | < 1 s |
| Re-optimisation | First improvement streamed within 3 s; budget 10 s default |
| Memory | TD tables ≤ 100 MB at n = 500 |
| Reproducibility | Fixed seeds; pinned dependencies; Docker |
| Offline demo | Works without internet (cached tiles optional, pre-built scenarios) |

## 10. Success metrics (reported, not promised)
- Gap to MILP / proven optima on small instances.
- QPSO vs PSO/GA/random restart: median cost, time-to-target, A12 effect size, Holm-corrected p-values.
- Realised travel time reduction of TD planning vs static planning (heavy traffic).
- Re-optimisation latency vs baselines B0–B3.
- Runtime and memory vs n.

## 11. Assumptions
- Single depot, homogeneous fleet, demands known at plan time.
- Speed profiles are calibrated synthetic (labelled as such), from published Delhi data.
- Pair paths are free-flow fastest paths, re-pathed only for incidents.

## 12. Open questions
- Fixed fleet K vs minimise vehicles (current default: optional K).
- Which Delhi zone for the demo.
- Whether to include time windows before the finale.