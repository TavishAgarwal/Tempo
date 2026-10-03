# Limitations

- **Quantum-inspired = classical.** QPSO is a sampling rule run on a normal CPU. No quantum hardware
  and no quantum speedup is claimed. We do not claim to beat PyVRP or KAYROS; every result,
  including losses, is reported from saved run records.
- **Synthetic traffic.** Speed profiles are calibrated-synthetic (see `calibration-notes.md`).
- **Single depot, homogeneous fleet, demands known at plan time.**
- **Time windows (Phase 8, F16)** are supported for static plans (Poryos TDVRPTW) by construction in
  Split and VND (a window violation is never accepted). Waiting that a later depot departure could
  absorb is treated as free (Savelsbergh forward slack), but the departure shift is not fed back into
  the time-dependent travel times, so the model slightly mis-prices TD routes; the official checker
  is the reference. Time windows are not combined with dynamic re-optimisation (in-field vehicles
  cannot shift their departure) and the Delhi edge-level simulator ignores them.
- **Pair paths are free-flow fastest paths**, re-pathed only for incidents. Optimiser tables
  interpolate linearly between 15-minute breakpoints; the gap to the edge-level simulator is
  measured (E1/Phase 3 notes), about 4–5% on the Delhi demo.
- **Dynamic re-planning assumptions.** Vehicles finish the edge they are on and reach their
  committed next stop (never diverted from it). Remaining capacity of an in-field vehicle is
  `Q − delivered` (parcels are assumed fungible/loaded to capacity); vehicles that have finished
  become depot vehicles again. The stability penalty μ enters the fitness, not the VND moves.
- **Congestion exposure** is minutes driven on edges whose speed ratio is below 0.5.
- **Tables memory.** τ at n=500 is ≈96 MB; the congestion table doubles that (not yet quantised).
- **Poryos2026**: loader and checker hook verified on the snapshot-2026-09-23-70ca946 files
  (checker reproduces the stored BKS exactly). The BKS in that snapshot predate the td-fold/2
  re-pricing; newer snapshots may change the stored costs slightly. Poryos has no Delhi instance.
  For Poryos the "simulator" is the table evaluation (no road graph in that format).
- **Live traffic (F17)** overlays a TomTom Flow Segment snapshot (36 sample points, per-road-class
  median ratio) on the calibrated profile for the next 1 h, relaxing back over 2 h. It is a
  coarse nowcast, not a forecast, and it needs the user's `TOMTOM_API_KEY`.
- **Emissions (F18)** use the COPERT/EMEP functional form with ILLUSTRATIVE coefficients
  (`configs/emissions.yaml`). Absolute figures must not be quoted until the published coefficients
  for the vehicle class are filled in. Emissions are reported, not optimised.
- **KAYROS** is run as an external reference through its public API on Poryos instances only; it is
  not part of TA-QPSO and no claim of beating it is made.
