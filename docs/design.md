# Design — TA-QPSO Dashboard

## 1. Principles
- Map first: routes and traffic are the story; panels support it.
- Show change: before/after is the core interaction.
- Honest and plain: no quantum imagery; labels say what numbers mean.
- Calm, technical look: light neutral UI, colour reserved for routes, congestion and status.

## 2. Layout (desktop ≥ 1280 px)
```
┌──────────────────────────────────────────────────────────────────────┐
│ Top bar: logo · Plan | Incident | Benchmark | Path | About · scenario │
├───────────────┬──────────────────────────────────────┬───────────────┤
│ Left panel    │                MAP                   │ Right panel   │
│ 320 px        │  routes · congestion · incidents     │ 360 px        │
│ inputs/preset │                                      │ KPIs, routes, │
│ time slider   │                                      │ convergence   │
├───────────────┴──────────────────────────────────────┴───────────────┤
│ Bottom strip (collapsible): solver log / status / timeline           │
└──────────────────────────────────────────────────────────────────────┘
```
- Tablet (768–1279): right panel becomes a bottom sheet.
- Mobile (< 768): map full screen, panels as tabs in a bottom sheet (view-only).

## 3. Screens

### 3.1 Plan
- Left: scenario select; customers (upload CSV or click-to-add); depot; vehicles K (optional) and capacity Q; departure time; preset (Fastest / Balanced / Low-congestion); solver select (TA-QPSO default; PSO, GA, Random, PyVRP); budget slider (10–120 s); seed; **Solve** button.
- Map: depot (square), customers (circles sized by demand), routes as coloured polylines on real roads, arrow chevrons every ~300 m.
- Right: KPI strip (Travel time, Distance, Congestion exposure, Vehicles, Load use %); route list (colour chip, stops, load/Q, time); live convergence chart (best cost vs seconds).
- Time-of-day slider (06:00–22:00, 15-min steps) re-scores the current plan and updates congestion layer.

### 3.2 Incident
- Tools: "Draw blockage" (click edges or draw polygon), severity (Blocked 0.1 / Heavy 0.4 / Custom), start time, duration.
- **Simulate incident** button (primary, red outline).
- Sequence shown:
  1. Incident area turns hatched red; vehicles freeze on map with ETA badges.
  2. Fallback plan appears within 1 s (dashed routes), badge "Safe plan".
  3. Improved routes stream in (solid), badge "Optimising… 3.2 s".
  4. Final: badge "Re-optimised in X s".
- Diff panel: before vs after KPIs with deltas; list of customers moved between vehicles; changed-stop count; μ slider (Stability ↔ Quality).
- Toggle: compare with baseline (B0 nav-app detour / B3 PyVRP snapshot) as ghost routes.

### 3.3 Benchmark
- Tabs: Correctness (gap to optima), QPSO vs classical (convergence bands, boxplots, p-values, A12), Traffic value (TD vs static), Incident recovery, Scaling.
- Each chart has a one-line takeaway above it and "Download CSV/PNG".
- Table rows: instance, n, method, median, best, gap %, time-to-target.

### 3.4 Path
- Click origin and destination; choose departure time; show fastest TD path, travel time, and the free-flow path for comparison. Optional k alternatives.

### 3.5 About / Algorithm
- The 7-step loop diagram (keys → sort → Split → VND → write-back → bests → QPSO update) with the QPSO step highlighted.
- Model summary, data sources, licences, limitations.

## 4. Visual tokens
| Token | Light | Dark |
|---|---|---|
| bg | #F7F7F5 | #121417 |
| surface | #FFFFFF | #1B1E22 |
| border | #E3E3DE | #2C3036 |
| text | #1C1F23 | #E8EAED |
| text-muted | #5F6670 | #9AA1AA |
| primary (actions) | #2563EB | #60A5FA |
| success | #15803D | #4ADE80 |
| warning | #B45309 | #FBBF24 |
| danger (incident) | #B91C1C | #F87171 |

- Route palette (colour-blind safe, Okabe–Ito order): #0072B2, #E69F00, #009E73, #CC79A7, #56B4E9, #D55E00, #F0E442, #000000; repeat with dashed pattern after 8.
- Congestion ramp by speed ratio (current / free-flow): ≥ 0.8 #2E7D32, 0.6–0.8 #F9A825, 0.4–0.6 #EF6C00, < 0.4 #C62828; road line width by class.
- Typography: Inter (UI), JetBrains Mono (numbers in tables/log). Sizes 12 / 14 / 16 / 20 / 28.
- Spacing scale 4 px; radius 8 px; shadows only on floating panels.
- Map tiles: CARTO Positron (light), Dark Matter (dark); OSM attribution always visible.

## 5. Components
- KpiCard: label, value, unit, delta (green down = better for time/distance).
- RouteChip: colour dot, vehicle id, load bar.
- StatusBadge: Idle / Solving / Safe plan / Optimising / Done / Error.
- ConvergenceChart: x = seconds, y = best J; one line per solver; shaded 95% band in Benchmark.
- DiffPanel: two columns (Before / After), delta column, moved-customers list.
- Toast: job finished, incident applied, errors.

## 6. States
- Empty: "Load a scenario or add customers to start."
- Loading graph: skeleton map + "Preparing road network (first run ~10 s)".
- Solving: Solve button becomes Stop; convergence chart live.
- Error: inline message with cause (e.g., "Demand exceeds capacity at customer 17").
- Offline: banner "Offline mode — using saved scenarios".

## 7. Copy rules
- "Quantum-inspired optimisation (runs on a normal CPU)" in About.
- Units always shown: min, km, %.
- "Congestion exposure = minutes driven on roads slower than 50% of free-flow speed."
- Speed source label: "Calibrated time-of-day profile (synthetic)" or "Live traffic".

## 8. Accessibility
- Contrast ≥ 4.5:1 for text; routes distinguishable by colour + dash + label on hover.
- Keyboard: Tab through panels; Enter = Solve; I = Incident tool; Esc cancels drawing.
- All charts have a data table toggle.

## 9. Demo scenario (pre-built)
- Delhi zone, 1 depot, 100 customers, 8 vehicles, departure 17:30 (evening peak).
- Incident: arterial segment blocked 18:00–19:00.
- Expected on screen: fallback < 1 s, improved plan streamed, before/after deltas, comparison with nav-app detour.