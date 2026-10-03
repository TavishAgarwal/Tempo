# Calibration notes — time-of-day speed profiles

**Label everywhere:** "Calibrated time-of-day profile (synthetic)".

## What the profile is
`taqpso/graph/profiles.py` builds, per road class, 96 speed factors (15-minute slots). Edge speed in
slot k is `freeflow_speed x factor[class][k]` (stepwise constant, IGP). Parameters live in
`configs/delhi_zone.yaml` (`profile:` block).

The network-wide ratio is a 24-value weekday table (`hourly_ratio`, 1.0 = fastest hour), constant
within each clock hour (TomTom's own bins). Per road class: `factor = 1 - sensitivity x (1 - ratio)`.

Source and method (read on 2026-10-02 from the TomTom Traffic Index 2025 New Delhi page, hourly
"travel time for 10 km" grid, Mon/Tue columns, "Show values"): ratio(h) = 14 min 45 s / travel time
of hour h, where 14 min 45 s is the fastest cell (Monday 03:00). Readings (min:s per 10 km, Mon / Tue):

| hour | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| time | 16:10/16:30 | 15:30/15:50 | 15:00/15:20 | 14:30/15:00 | 15:10/15:30 | 16:10/16:30 | 16:20/16:50 | 18:30/18:40 | 21:40/21:50 | 25:00/25:30 | 25:00/25:50 | 25:10/26:30 |
| ratio | 0.90 | 0.94 | 0.97 | 1.00 | 0.96 | 0.90 | 0.89 | 0.79 | 0.68 | 0.58 | 0.58 | 0.57 |

| hour | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| time | 25:10/26:50 | 25:20/27:00 | 25:00/26:40 | 25:00/26:50 | 26:00/27:50 | 29:20/31:10 | 30:20/32:10 | 27:30/29:20 | 23:10/24:40 | 20:00/21:00 | 18:50/19:10 | 17:40/18:00 |
| ratio | 0.57 | 0.56 | 0.57 | 0.57 | 0.55 | 0.49 | 0.47 | 0.52 | 0.62 | 0.72 | 0.78 | 0.83 |

(Cells were read from a screenshot; individual values may be off by about ten seconds.)
Page headline figures confirmed on the same visit: average rush-hour speed 20.8 km/h; morning rush
25 min 58 s per 10 km, congestion 71.7%, 23.1 km/h; evening rush 31 min 45 s, 107.4%, 18.9 km/h;
highways 48.1 km/h, 5.3% of trips; worst day Wed 15 Oct, 192% at 18:00, 3.3 km in 15 min; annual
average 24 min per 10 km, congestion 60.2%.

Shape: a flat daytime plateau at 0.55-0.58 from 09:00 to 16:00, an evening dip to 0.47 at 18:00, a
recovery to 0.83 by 23:00 and a morning ramp 0.79 (07:00) to 0.58 (09:00). This replaces the
earlier bump-shaped placeholders (0.8 / 0.5 / 0.35) and an interim bump fit (0.58 / 0.55 / 0.46).

Not captured: whether the grid was on the "City" or "Metro" selection (the page default highlights
"City"; record the toggle state when re-checking). Weekend columns are ignored (weekday profile).

Cross-checks (not used to fit):
- CSE 2017 (Google Maps, 13 arterials, 8:00-20:00): speed 25-30 km/h for about 75% of the time, peak and
  off-peak barely different, evening worse than morning. Lutyens' Delhi (50 m arterials): peak 44,
  off-peak 52 km/h (ratio about 0.85). RITES via CSE: 27.7 vs 30.8 km/h (about 0.90).
  Consistent with a flat profile; the TomTom ratio is lower because its reference is overnight speed,
  not the daytime off-peak speed.
- Live TomTom Flow Segment Data snapshot of the Central Delhi bbox (36 points, 2026-10-02 15:37 IST,
  Friday): median current/free-flow ratio per class 0.63 (trunk) to 0.89 (tertiary). TomTom's segment
  free-flow is a per-segment reference, so it is not directly comparable with the Index ratio. Stored in
  `data/processed/tomtom_snapshot.json` (gitignored); regenerate with `make live-snapshot`.

## Honest status of the calibration
- The network-wide shape now follows the TomTom hourly grid (see above).
- The class sensitivities (arterials 1.0, residential 0.5, motorway 0.6) are still **assumptions**:
  TomTom gave only network-wide and highway figures. Road-class sensitivity is open.
- Not covered: Delhi Traffic Police / PWD reports (none found), Google Maps rush-hour vs free-flow for
  sample routes (needs a manual pull of 5-10 routes), INRIX, CRRI.
- Profiles stay labelled "Calibrated time-of-day profile (synthetic)". Do not use Uber Movement or EMFAC-HK.

## Known simplifications
- Speeds only; no flows, no v/c ratios, no BPR (rules.md).
- One profile per road class, not per edge; incidents are applied per edge as slot-level
  multipliers on the profile (overlap-weighted), so FIFO is preserved.
- Free-flow speed from OSM `maxspeed` where present (about 2% of edges in the Central Delhi extract),
  otherwise the road-class default in `delhi_zone.yaml`; the fill rate is logged by the graph build.
- Time beyond 24 h wraps modulo 24 h (daily profile).
