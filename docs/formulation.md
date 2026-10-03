# Formulation and algorithm

## Problem
Single depot 0, customers 1..n with demand d_i ≤ Q, homogeneous fleet (optionally at most K
vehicles), service time s_i. Travel time on a leg depends on the departure time, τ_ij(t), and is
FIFO: t + τ_ij(t) is non-decreasing. All vehicles leave the depot at the same time.

Objective `J = w_T·T/T_ref + w_D·D/D_ref + w_C·C/C_ref`: T total driving time (primary), D distance,
C congestion exposure; references come from the nearest-neighbour solution of the same instance.
Presets (`configs/default.yaml`): fastest (1,0,0), balanced (1,0.25,0.25), low_congestion (1,0.1,0.6).

## Travel-time model
Edge speed is stepwise constant per 15-minute slot (IGP). Distance is consumed slot by slot, which is
FIFO by construction. Pair tables τ_ij(slot start) come from propagating the stored free-flow
fastest path; arbitrary times are linearly interpolated. `fifo_check` verifies every pair and fails
the build on violation. The ground-truth simulator (`sim/simulator.py`) re-walks routes edge by edge.

## TA-QPSO loop (per particle, per iteration)
1. keys x∈[0,1]^n → stable argsort → giant tour
2. Split (Bellman/Prins DP) → capacity-feasible routes by construction (exact under TD because every
   route departs the depot at the same time)
3. VND: relocate, swap, 2-opt, 2-opt*, or-opt; granular lists (k=15); first improvement; suffix
   re-evaluation; a move is accepted only if capacity holds and J strictly decreases
4. write-back: reassign the particle's own sorted key values so decode = improved tour exactly
5. update pbest / gbest / mbest
6. QPSO: `P = φ·pbest + (1−φ)·gbest`, `x ← P ± α|mbest − x|·ln(1/u)`, u floored at 1e-12,
   α linear in elapsed budget (tuned: 0.05 → 0.01, swarm of 6; `configs/tuned.yaml`),
   reflect+clip into [0,1]
7. 30 stalled iterations → re-randomise the worst 30% of particles

PSO, random-key GA and random restart replace only step 6.

### Step size
With the first-round α = 1.0 → 0.5 an updated particle kept only 1–5% of its pbest tour's edges
(a random tour keeps 0.4–2%), so VND rebuilt every particle from scratch and QPSO behaved like
random restart. A step of α = 0.05 → 0.01 keeps the particle near its attractor; it won the tuning
grid (`configs/experiments/tuning.yaml`). Two other options were tested in the same grid and lost,
and stay off by default: `qpso.attractor: particle` (one φ per particle) with `qpso.space: rank`
(update normalised ranks), and the VND gate `vnd.gate_tolerance` (light VND for every particle,
full VND only within the tolerance of its pbest), which every optimizer could choose and none did.

## Dynamic re-planning
Incident → per-edge slot multipliers → affected pairs via inverted index → re-path (TD-Dijkstra)
→ recompute those τ rows. Vehicle states at t_e; fallback B0 keeps each remaining sequence (legs
detour automatically); warm re-optimisation uses a fleet-aware Split (each vehicle starts at its own
node/time/remaining capacity) and a swarm seeded 50% from the incumbent.

## Time windows (Phase 8, F16)
Customer i has [ready_i, due_i]. A route is feasible if every arrival-after-waiting is ≤ due_i.
Waiting that a later depot departure can absorb is free: with W the total waiting along the route
and F = min_k(W_k + due_k − s_k) the forward slack (W_k = waiting up to and including customer k,
s_k = service start), delaying the departure by d ≤ min(W, F) removes d of waiting and keeps every due
time (Savelsbergh), so the route time is driving + service + (W − min(W, F)). Split extends a route
only while no due time is violated (a later customer can only arrive later, so the DP break is
exact); VND re-prices the whole route and rejects any move that violates a window. The departure
shift is not fed back into the time-dependent travel times (see limitations.md).

## Emissions (Phase 8, F18)
Edge mean speed v = length / IGP time; emission = EF(v)·length with the COPERT/EMEP form
EF(v) = (a + c·v + e·v²)/(1 + b·v + d·v²) g/km, v clamped to [v_min, v_max]. Coefficients are
illustrative until the published ones are filled in `configs/emissions.yaml`. Reported, not optimised.

## Live traffic (Phase 8, F17)
TomTom Flow Segment Data on a 6×6 grid over the zone → median current/free-flow speed ratio per
road class (FRC → our class) → overlaid on the calibrated profile: ratio held for 4 slots (1 h) then
relaxed linearly to the profile over 8 slots, so IGP and FIFO are unchanged. Label: "Live traffic".
