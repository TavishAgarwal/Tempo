# 3-minute demo script

Prep (once, online): `make data`, `make run-api`, `make run-ui`; open the app once so map tiles of the
zone are cached by the service worker (`frontend/public/sw.js`); keep a screen recording as the
fallback if the live run fails. Scenario: `delhi_demo` (100 customers, 8 vehicles, departure 17:30).

| Time | Do | Say |
|---|---|---|
| 0:00 | About page, 10 s | Quantum-inspired = classical sampling rule on a CPU; speeds are a calibrated synthetic profile. |
| 0:15 | Plan: Fastest, 10 s budget, **Solve** | Routes on real roads stream in; KPIs in min/km/%; congestion layer by time of day. |
| 0:50 | Drag the time-of-day slider to 10:00 | Same plan re-scored: congestion exposure drops. |
| 1:10 | Incident page: **Draw blockage** over a busy arterial (I key), severity Blocked, start 18:00, 1 h; **Simulate incident** | Vehicles freeze with ETAs; "Safe plan" appears in well under a second (dashed). |
| 1:40 | Wait for "Re-optimised in X s" | Improved plan streams in; diff panel shows customers moved; ghost toggle shows the old plan. |
| 2:15 | Benchmark page → QPSO vs classical, Traffic value | Honest results: local search carries quality; QPSO beats PSO and random restart at n ≥ 50 and ties GA up to n = 100, while GA (n ≥ 200) and PyVRP (n ≥ 100) beat it; TD planning gains are small (≈0.5% at 17:30) with the flat TomTom-calibrated profile. |
| 2:45 | Path page: click two points, 18:00 | Time-dependent fastest path vs free-flow path. |

Optional on the Plan page: tick **Live traffic (TomTom)** (needs `TOMTOM_API_KEY`; the label says "Live traffic" and the
snapshot time is shown). The KPI strip also shows an illustrative CO2 estimate (label says so).

Offline run: stop the network after the cache warm-up; API and UI are local, tiles come from the cache
(the map degrades to a banner "Map tiles unavailable offline", routes still draw).
Gate: `make demo-offline` runs the whole flow twice in a row against an API that refuses every
non-loopback connection (passed on 2026-10-02: two runs, no errors, safe plan in 0.05 s).
`node frontend/record_demo.mjs` re-records the flow as a fallback video (`results/demo_fallback.mp4`) and a
Phase 0 map screenshot (`results/demo_plan.png`). A human rehearsal of the spoken 3-minute script is still to be done.
