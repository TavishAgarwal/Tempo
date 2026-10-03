/**
 * Every model figure the landing page quotes lives here, once.
 * Source for each block is the saved result table (docs/results-summary.md, generated from
 * results/runs/*.json). Plan and incident figures are NOT here: they are read at runtime from
 * public/landing-data.json (scripts/export_landing_data.py), so re-running the export updates them.
 */
export const M = {
  graph: { junctions: 1090, segments: 2421 }, // data/processed/graph.npz
  // results/e1/table.csv
  e1: { milpGapPct: 0, milpInstances: 3, bksMatched: 4, bksTotal: 5, xn101GapPct: 2.55 },
  // results/e2 + e2_large (2026-10-03, tuned): QPSO vs classical at equal wall-clock budget
  e2: {
    beatsPsoRandomFromN: 50, // Holm p <= 0.009 vs PSO and random restart at n = 50 .. 500
    tiesGaUpToN: 100, // n = 100: GA -0.7%, Holm p = 0.3; GA better at n >= 200
    vsFirstRoundPct: [2.1, 5.8] as [number, number], // first-round QPSO worse by, n = 100 .. 200
    vndRaisesJPct: [8, 33] as [number, number], // removing VND, n=30 .. n=100
    n500: { qpso: 0.797, ga: 0.776, pyvrp: 0.699 },
  },
  // results/e3/table.csv: static vs time-dependent planning at 17:30, realised under the simulator
  e3: { reductionPct: [0.36, 0.52] as [number, number], holmP: [0.088, 0.197] as [number, number] },
  // results/e4 (zone scenario, 20 seeds) and e4/latency.csv
  e4: {
    safePlanMaxS: 0.076,
    movedAfterMu: 6,
    jBeforeMu: 0.4517,
    jAfterMu: 0.4488,
    pyvrpWorsePct: 16.5,
    staticResolvePct: -5.93,
    warmPct: -5.28,
  },
  // results/e5/table.csv, n = 500
  e5: { tablesMb: 194, rssMb: 416 },
  poryos: { matchedBks: 11, instances: 18 },
} as const;
