# 2026-07-23 — Multi-seed training, Lighthouse refresh, noise-robust offset-free MPC

## Purpose
Close the remaining handover items: (1) multi-seed *training* runs to qualify
the last policy-level claims (v5-vs-v4 deltas; pitch-flip failure = seed
variance or structural?), (2) refresh the Lighthouse rows that predate the
gyro-latency sensor fix (MPC, MPPI, datt_acro), (3) make offset-free MPC's
ESO input noise-robust (Lighthouse-normal was 0.178±0.076).

## Design review: Deep Drone Acrobatics (Kaufmann et al., RSS 2020) vs our acro pipeline

Reviewed at user request (repo uzh-rpg/deep_drone_acrobatics + RSS20 paper),
question: applicable here? and should maneuver motion planning happen before
the trajectory reaches the controller?

**Their architecture** — three cleanly separated stages:
1. **Offline maneuver planning** in differential-flatness space: the core of
   each maneuver (Power Loop, Barrel Roll, Matty Flip) is a circular motion
   primitive with tangential velocity constrained to ||v|| > 1.1*sqrt(r*g) so
   the required thrust never crosses zero (orientation stays well-defined at
   the loop top); entry/exit are order-7 polynomials, time-optimized under
   speed/thrust/body-rate limits; the result is converted to a full
   state-space reference sampled at 50 Hz. **The reference is dynamically
   feasible by construction.**
2. **Privileged expert**: an MPC on a simplified *quaternion* point-mass model
   (no Euler singularities, no rate dynamics) tracks that reference from
   ground-truth state, outputting collective thrust + body rates (CTBR).
3. **Student policy**: async multi-modal net (feature tracks + IMU history +
   reference in), CTBR out, trained with DAgger to imitate the expert,
   entirely in simulation; zero-shot transfer via sensory abstraction.

**Answer to the architecture question: yes.** Planning-then-tracking is the
standard decomposition in the acrobatics literature (their refs include
Lupashin et al.'s flip machines): the *planner* owns dynamic feasibility
(thrust/rate limits, the free-fall constraint), the *controller/policy* owns
robust tracking. DDA's learned policy never plans — it tracks a reference
computed before flight.

**What this exposes in crazy_track:** our `FlipTrajectory` position reference
stays pinned at the hover point during the flip — intentionally infeasible
(mid-flip the thrust vector points sideways/down; measured altitude loss
1.5-2.2 m). The policy is asked to satisfy two contradictory references at
once, which is why acro2.x needed the "attitude term dominates during the
maneuver window" reward hack, and it plausibly contributes to the 0.5-1 m
recovery error and the pitch-flip learning failure. DDA has no such conflict:
position and attitude references are consistent by construction.

**Implementable here, ranked:**
1. *Feasible flip references* (moderate effort, high value). Platform caveat,
   checked: a DDA-style constant-speed loop needs bottom-of-loop thrust
   >= (1 + v^2/(r*g)) * m*g ~= 2.2 m*g at their margin (eps=1.1) — cf21B TWR
   is 1.88, so their loops are out of envelope. The TWR-limited variant is
   the **ballistic flip** (Lupashin-style): entry thrust boost -> near-zero-
   thrust ballistic arc with constant body rate -> braking recovery, encoded
   as a *consistent* position+attitude reference. Then the position and
   attitude rewards agree and the maneuver-window reward hack can be retired.
2. *Privileged MPC expert + DAgger* (higher effort). Our so_rpy Euler MPC
   cannot be the expert (singular at ±90 deg pitch, hover-fitted); it would
   need DDA's quaternion CTBR model in CasADi. Only worth it if feasible
   references + PPO still fail on pitch.
3. *Sensory abstraction* — not relevant (no camera model; the asymmetric
   actor-critic in v5 already covers privileged learning in RL form).

**Gate:** the 3-seed acro2.2 runs (this session) decide whether pitch-flip
failure is seed variance. If structural -> ballistic feasible reference is
the acro phase 3 design.

## Infrastructure: RunLogger collision fix
Launching two training streams in the same second collided on the
second-resolution run-dir timestamp (`FileExistsError`, stream A died).
`runlog.py` now retries with `-b/-c/-d` suffixes. Windows-side tests pass
(9/9). The aggregator's tag parsing is suffix-safe.

## Multi-seed training runs (in progress)
Two WSL background streams, recipes identical to the seed-0 runs:
- v4 (`--noisy-sensor`, 3M steps): seeds 1, 2 (seed 0 = run 17-07-10)
- v5 (`--v5`, 4M): seeds 1, 2 (seed 0 = run 17-32-52)
- acro2.2 (`--acro2`, 5M): seeds 1, 2 (seed 0 = run 21-41-06)

Eval protocol (after training): per policy seed — nominal s/n/f, lighthouse
s/n/f, wind_const normal, lighthouse+wind normal, all at eval seed 0 to
isolate training-seed variance (eval-seed std known small from the 10-seed
sweep: ±0.007 for v5 lighthouse-fast); flips via flip_eval. Aggregation via
`aggregate_seeds --prefix mst-`.

## Lighthouse refresh post gyro fix (runs ms-lhfix-*, in progress)
Stale: MPC + MPPI rows from 16-36-29 (pre-fix, single seed). datt_acro was
never run under Lighthouse. Re-running all three, 3 eval seeds.

## Offset-free MPC: noise-robust ESO (in progress)
`MPCController` gained `eso_w`; CLI accepts `mpc_offsetfree_w<N>`. Rationale:
unlike ADRC, this ESO is not in a high-gain feedback path — it only biases
the MPC prediction model — so its bandwidth can sit far below the tracking
bandwidth. Quasi-static wind converges even at w=3 (~1/w s); the Lighthouse
velocity noise that jitters the w=7 estimate is attenuated ~(3/7)^2 in the
sigma channel. Sweep: w in {3,5,7} x {nominal s/n/f, wind_const, lighthouse
normal+fast x 3 seeds}.
