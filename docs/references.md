# References

**Status: citation details written from memory by the assistant; a teammate must verify each entry
(authors, year, venue) before submission (phases.md Phase 9 gate).** Data sources marked "supplied"
were reported by the team and are not independently re-checked.

## Methods
- Ichoua, S., Gendreau, M., Potvin, J.-Y. (2003). Vehicle dispatching with time-dependent travel
  times. European Journal of Operational Research. (IGP stepwise speeds, FIFO by construction)
- Prins, C. (2004). A simple and effective evolutionary algorithm for the vehicle routing problem.
  Computers & Operations Research. (giant-tour Split)
- Sun, J., Feng, B., Xu, W. (2004). Particle swarm optimization with particles having quantum
  behavior. IEEE CEC. (QPSO update rule)
- Bean, J. C. (1994). Genetic algorithms and random keys for sequencing and optimization. ORSA
  Journal on Computing. (random keys)
- Savelsbergh, M. W. P. (1992). The vehicle routing problem with time windows: minimizing route
  duration. ORSA Journal on Computing. (forward slack, departure shifting)
- Vargha, A., Delaney, H. D. (2000). A critique and improvement of the CL common language effect
  size statistics. Journal of Educational and Behavioral Statistics. (A12)
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of
  Statistics. (Holm correction)

## Software and benchmarks
- Uchoa, E. et al. (2017). New benchmark instances for the capacitated vehicle routing problem.
  European Journal of Operational Research. (CVRPLIB X set; A/B/E/F/P sets from CVRPLIB)
- Wouda, N. A., Lan, L., Kool, W. (2024). PyVRP: a high-performance VRP solver package. INFORMS
  Journal on Computing.
- MAMUT-routing / Poryos2026 benchmark and `mamut-routing-lib` 0.12.0 (ODbL-1.0); snapshot tag
  `snapshot-2026-09-23-70ca946`.
- KAYROS 1.6.0 (MIT), used only as an external reference on Poryos instances.
- OpenStreetMap contributors (ODbL), OSMnx for graph extraction.

## Traffic data (supplied by the team; readings to be re-checked)
- TomTom Traffic Index 2025, New Delhi: rush-hour mean 20.8 km/h; morning 23.1 km/h (congestion
  71.7%), evening 18.9 km/h (107.4%); highways (FRC0) 48.1 km/h, 5.3% of trips. Hourly-table
  readings were read off the rendered page; City vs Metro selection not recorded.
- Centre for Science and Environment (2017), Google Maps study of 13 Delhi arterials (via Down To
  Earth / CSE): 25–30 km/h about 75% of the time; Lutyens' Delhi peak 44 vs off-peak 52 km/h.
- RITES report quoted by CSE: peak 27.7 vs off-peak 30.8 km/h.
- TomTom Traffic Flow Segment Data API (live snapshot, 2026-10-02 15:37 IST).
- Emissions: COPERT / EMEP-EEA air pollutant emission inventory guidebook functional form only; no
  published coefficients are used yet.
