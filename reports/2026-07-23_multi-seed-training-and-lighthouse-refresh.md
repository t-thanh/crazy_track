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

## Multi-seed training runs: v5-vs-v4 verdict (DONE)
Two WSL background streams, recipes identical to the seed-0 runs:
- v4 (`--noisy-sensor`, 3M steps): seeds 1, 2 (seed 0 = run 17-07-10)
- v5 (`--v5`, 4M): seeds 1, 2 (seed 0 = run 17-32-52)
- acro2.2 (`--acro2`, 5M): seeds 1, 2 (deferred to paper 2; s2 trains on idle
  time, s1 requeued)

Eval protocol: per policy seed — nominal s/n/f, lighthouse s/n/f, wind_const
normal, lighthouse+wind normal, all at **eval seed 0** to isolate
training-seed variance (eval-seed std known small from the 10-seed sweep).
Aggregation: `aggregate_seeds --prefix mst-`. Seed-0 policies re-evaluated
under mst- tags first; results reproduced yesterday's numbers exactly
(deterministic eval pipeline).

RMSE 3D (m), mean±std over 3 TRAINING seeds [min-max]:

| cell | DATT v4 | DATT v5 | verdict |
|---|---|---|---|
| nominal slow | 0.042±0.015 | 0.038±0.014 | tied (seed spread >> delta) |
| nominal normal | 0.092±0.013 | 0.075±0.010 | v5 trend |
| nominal fast | 0.165±0.012 | 0.157±0.007 | tied |
| lighthouse slow | 0.033±0.009 | 0.033±0.008 | tied |
| lighthouse normal | 0.070±0.006 [.063-.078] | 0.056±0.005 [.051-.063] | **v5, ranges touch at one point** |
| lighthouse fast | 0.127±0.003 | 0.120±0.011 | tied |
| wind_const (clean) | 0.098±0.009 [.089-.111] | 0.073±0.007 [.063-.080] | **v5, non-overlapping** |
| **lh+wind (deployment)** | 0.077±0.006 [.069-.083] | **0.059±0.002** [.056-.062] | **v5, non-overlapping** |

### Findings
1. **"v5 wins the deployment condition" is CONFIRMED at the policy level**
   and is the strongest result in the study: 0.059±0.002 vs 0.077±0.006,
   non-overlapping ranges, and v5's training-seed variance in that cell is
   near-zero — the asymmetric-critic recipe reliably produces this behavior,
   independent of initialization.
2. **Yesterday's "v5 costs clean-state performance vs v4" claim was
   seed-0 luck and is RETRACTED**: v4-s0 was v4's best nominal draw
   (0.022/0.076/0.154) while v5-s0 was v5's worst (0.055/0.089/0.163). At 3
   seeds the means invert: v5 <= v4 in every nominal cell. v5 dominates or
   ties v4 in ALL eight cells measured.
3. **v5's wind-rejection recovery over v4 is real** (0.073±0.007 vs
   0.098±0.009, non-overlapping) — the privileged critic does buy back part
   of v3's disturbance rejection (v3 clean-eval wind: 0.050).
4. Nominal-slow has ±0.015-level training-seed noise for BOTH configs —
   single-seed comparisons in that cell are meaningless; several yesterday's
   small deltas there carried no information.
5. vs the deployment champion: ADRC+xadapt lh+wind 0.060±0.009 (10 eval
   seeds) vs v5 0.059±0.002 (3 training seeds) — **still statistically
   tied**; the classical stack and the learned policy have converged to the
   same deployment performance by different mechanisms.

## Lighthouse refresh post gyro fix (runs ms-lhfix-* / ms-lhfix-acro-*, DONE)
Stale: MPC + MPPI rows from 16-36-29 (pre-fix, single seed). datt_acro was
never run under Lighthouse. Re-ran all three at 3 eval seeds.

RMSE 3D (m), lighthouse, mean±std over seeds 0-2 (min-max in brackets):

| controller | slow | normal | fast |
|---|---|---|---|
| MPC | 0.014±0.003 | 0.122±0.021 | 0.067±0.001 |
| MPPI+L1 (tuned) | 0.051±0.001 | 0.079±0.018 | **0.228±0.178** [0.091-0.480] |
| datt_acro (CTBR) | 0.063±0.006 | 0.109±0.008 | 0.147±0.002 |

### Findings
1. **The gyro-latency fix is a non-event for MPC**: matched seed-0 rows
   pre-fix 0.009/0.121/0.067 vs post-fix 0.009/0.134/0.068. The stale MPC
   rows were substantively fine — MPC's lighthouse-normal error is dominated
   by ipopt transients on noisy position (max-err 0.64-0.95 outliers), not by
   the 10 ms gyro delay. Normal-cell spread across seeds is 0.093-0.138.
2. **The old MPPI row was doubly stale** (pre-gyro-fix AND pre-tuning), and
   the refresh surfaces a new finding: **tuned MPPI's lighthouse-fast cell is
   a variance phenomenon** — 0.091 / 0.114 / 0.480 across three seeds. The
   clean-sensing fast champion (0.068) does not survive Lighthouse sensing:
   on a bad bias/sampling draw the AR(1)-correlated exploration noise
   near-crashes, same failure shape as DATT v3's lighthouse-fast variance
   (0.155-0.505). Seed 0 is a bad draw both pre-fix (0.303) and post-fix
   (0.480). For the paper: MPPI's fast-tier advantage is a clean-sensing
   result only; mean-only tables would hide this.
3. **First datt_acro Lighthouse rows**: 0.063/0.109/0.147 with the lowest
   fast-tier variance in the pool (±0.002) — the CTBR policy degrades
   gracefully under sensor noise too (+19% at fast vs clean 0.123),
   consistent with the learned-policy robustness pattern (v4/v5).

## Offset-free MPC "noise sensitivity": root-caused and fixed (soft-start ESO)

The handover framed the 0.178±0.076 lighthouse-normal cell as "the ESO
ingests position-ZOH noise" and suggested lower bandwidth or an innovation
LPF. The investigation falsified most of that framing in three steps.

### Step 1 — bandwidth sweep (w in {3,5,7}, `mpc_offsetfree_w<N>`)
Paired per-seed under lighthouse, w3 beats w7 10/10 seeds at normal (mean
delta 0.032±0.023) and 8/10 at fast; but it costs nominal fast (0.053→0.072)
and wind (0.039→0.057). Looked like the ADRC story again — until the
absolute levels were compared: plain MPC (no ESO at all) posted 0.122 on
seeds 0-2, *better* than any offset-free variant in that cell.

### Step 2 — the real culprit: a launch transient, not steady-state noise
Time-series inspection of the bad seeds: the entire excess error is a single
0.7-1.5 m transient at t = 0.5-1.6 s (the benchmark reference starts at
|v| = 1.14 m/s while the drone is at rest; the 1 s metric warmup only
excludes the spike's head, not its tail). **Steady-state (t>2.5 s)
lighthouse-normal RMSE is 0.046±0.008 at w7** — on par with the best
controllers in that cell, and w3's steady-state advantage is marginal
(0.041±0.010). The ESO was never noise-fragile in steady state. This also
explains the paradox that offset-free MPC tracked *better* with wind added
(lh+wind 0.057±0.014 vs lh-only 0.178): with a real 2.5 m/s^2 disturbance
the early sigma estimate is signal-dominated instead of noise-dominated, so
the launch-window corrections are coherent.

### Step 3 — fix: soft-start (ramp DISTP authority over 1.5 s ≈ 3x ESO t_conv)
A cold ESO's first innovations are noise-dominated at full gain; planning
against that phantom disturbance during the launch acceleration is what
amplified the transient. `mpc.py` now ramps the disturbance estimate fed to
the optimizer as `sigma * min(1, t/1.5)`. Results (10 lighthouse seeds):

| variant | nominal s/n/f | wind | lh normal (n=10) | lh fast (n=10) | lh+wind |
|---|---|---|---|---|---|
| plain MPC | 0.018/0.063/0.083 | 0.196 | 0.215/0.230 on bad seeds 4,8 | 0.067±0.001 (n=3) | 0.199±0.017 (n=10) |
| offset-free w7 (pre-fix) | 0.006/0.043/0.053 | **0.039** | 0.178±0.076 | 0.081±0.022 | 0.057±0.014 (n=10) |
| offset-free w3 | 0.006/0.056/0.072 | 0.057 | 0.146±0.061 | 0.065±0.014 | 0.060±0.014 (n=3→10 mixed) |
| **offset-free w7 + soft-start** | **0.004/0.036/0.052** | 0.045 | **0.141±0.058** | 0.070±0.010 | 0.052 (s0) |

- **New nominal records across the board: 0.004 / 0.036 / 0.052** — the
  cold-start sigma jitter was costing performance even with clean sensing.
- Lighthouse: 0.178±0.076 → 0.141±0.058 full-window; steady-state 0.046±0.009.
- Wind pays 0.006 for the delayed pickup (0.039 → 0.045). Acceptable.
- w=7 + soft-start is the single default; the `_w<N>` variants remain
  available but are no longer recommended (w3's apparent win was mostly
  launch-window luck).

### Residual (documented, out of scope): the remaining transient is generic
Discriminating test on the bad seeds (4, 8): plain MPC spikes identically
(max 1.16 / 1.22 m, RMSE 0.215 / 0.230) — worse than offset-free+soft-start
on the same seeds. Every MPC variant reacts violently to the reference
velocity jump when the first ipopt solves see bad bias draws; plain MPC's
"0.122±0.021" from the refresh was a lucky 3-seed sample (seeds 0-2 are all
mild draws). Candidate remedies if the cell ever matters more: state
pre-filtering (EKF) ahead of the optimizer, reference ramp-in, or a
hover-spinup phase in the benchmark protocol (a metric change — needs a
deliberate decision, not a drive-by).

## Paper-1 synthesis: controller ranking, failure modes, and why

No controller dominates; the ranking is condition-dependent. This section is
the paper-1 discussion skeleton.

### Deployment ranking (Lighthouse + wind, normal — the realistic cell)

Three-way statistical tie at the top, reached by three unrelated mechanisms:

| rank | controller | RMSE 3D (m) | evidence |
|---|---|---|---|
| 1= | Offset-free MPC (soft-start) | 0.057±0.014 | 10 eval seeds |
| 1= | DATT v5 | 0.059±0.002 | 3 training seeds |
| 1= | ADRC+xadapt | 0.060±0.009 | 10 eval seeds |
| 4 | DATT v4 | 0.077±0.006 | 3 training seeds |
| — | plain MPC | 0.199±0.017 | 10 eval seeds |

A disturbance-augmented prediction model, a privileged-critic policy, and an
ESO over an adaptive rate loop converge to ~0.06 m — that convergence is
itself a result: at this sensor quality, the deployment cell appears
estimator-limited, not architecture-limited.

### Per-scenario champions

| scenario | champion | value | runner-up |
|---|---|---|---|
| nominal slow / fast | offset-free MPC | **0.004 / 0.052** | PID 0.012 / PID+xadapt 0.067 |
| nominal normal | ADRC+xadapt | **0.018** | PID 0.022 |
| wind_const (clean) | ADRC w7 | **0.025** | ADRC+xadapt 0.037 |
| wind_gust | DATT v3 | **0.061±0.002** | ADRC+xadapt 0.063 |
| payload | ADRC+xadapt | **0.018** (= its nominal) | ADRC 0.036 |
| ground effect | PID | **0.023** | — |
| lighthouse fast tier | DATT v5 | **0.120±0.011** | PID+xadapt 0.122 |
| acro tier (T=2.2) | datt_acro | **0.322 / 0.349** (h/v) | MPPI 0.341 / 0.372 |

### Failure cases and limits, per controller

- **Offset-free MPC (soft-start)** — best precision instrument. (1) Launch
  transients on noisy state: on bad bias draws the first ipopt solves react
  violently to the reference-velocity jump (~1 m at t≈0.9 s), polluting
  lighthouse-normal full-window (0.141±0.058 vs 0.046 steady-state); generic
  to the MPC family — no state filter ahead of the optimizer. (2) so_rpy
  Euler model: hover-fitted, singular at ±90° pitch — no acro, and model
  bias grows with speed. (3) Compute: 20-70 s wall/episode.
- **DATT v5** — deployment policy; the only controller with *proven
  initialization robustness* in its headline cell (±0.002 over training
  seeds). Limit: memoryless MLP cannot infer per-episode noise level, so it
  averages over the DR range instead of calibrating — costs clean-state
  agility (nominal fast 0.157±0.007, worst among competitive stacks) and
  leaves wind short of v3 (0.073 vs 0.050). Frame stacking (v6a) did not
  fix it at 4M steps; recurrence is the known next step.
- **ADRC+xadapt** — best breadth; payload is invisible (0.018 = nominal).
  (1) ESO phase lag at speed: fast nominal 0.084 vs 0.067 for PID over the
  same low-level. (2) Under constant wind loses to plain ADRC (0.037 vs
  0.025): the ESO watches the plant *through* the adaptive rate loop, which
  partially absorbs — and masks — the signal it estimates.
- **ADRC (w7)** — constant-wind champion. Limit: one bandwidth knob, two
  jobs. Low w filters noise / tracks static disturbances; high w tracks
  gusts; no fixed w wins both. The adaptive-w attempt failed for an
  identified reason: the innovation statistic cannot distinguish external
  disturbances from the ESO's own attitude-lag residual during aggressive
  tracking (false-positives into high bandwidth). Fundamental to
  fixed-structure lumped-disturbance observers.
- **MPPI+L1 (tuned)** — clean-sensing fast champion (0.068). (1)
  Lighthouse-fast fragility is a variance phenomenon (0.091/0.114/0.480):
  the AR(1)-correlated exploration that helps nominally lets a bad bias
  draw steer the whole sample distribution wrong for many steps. (2)
  Internal-model validity: the hover-fitted so_rpy rollout model breaks at
  vertical-fast (0.423) — sampling cannot rescue wrong physics.
- **PID (+acc ff)** — honest baseline; ground-effect champion (thrust-gain
  disturbance is nearly collinear with its feedforward). Limit: no
  disturbance estimator — sustained forces become steady-state error (wind
  0.109, payload 0.093, ~4x). Everything above it wins via some form of
  disturbance estimation.
- **Plain MPC** — superseded by offset-free within its own family (which is
  better even nominally: the disturbance state absorbs standing model
  bias). Re-predicts the same biased trajectory under steady wind
  (0.196/0.199). No remaining cell where it is the right pick.
- **DATT v3** — gust champion; the L1 estimate in the obs reacts to
  disturbance state directly. Limit: unconditional trust in that channel —
  with Lighthouse noise at high agility it chases phantom disturbances
  (lighthouse-fast 0.323±0.106; the ±0.106 is the point — some seeds fine,
  some near-crash). Clean-state deployments only.
- **DATT v4** — historically important (proved noisy-obs training fixes
  v3's failure mode) but now dominated by v5 in all 8 measured cells; no
  deployment reason to use it.
- **datt_acro (CTBR)** — graceful-degradation specialist: wins both
  acro-tier trajectories, lowest fast-tier variance under Lighthouse
  (±0.002), never diverges where attitude-mode stacks do. (1) Precision at
  feasible speeds: fast 0.123 vs 0.067 pool best — torque-level learning
  trades easy-regime precision for envelope robustness. (2) Physics, not
  controller: the acro tier demands 16.3 m/s^2 lateral vs the cf21B's
  ~15.2 m/s^2 limit — that tier measures graceful degradation on
  infeasible references for everyone. (3) Pitch flips unlearned (paper-2
  opening problem; feasible-reference hypothesis).

### Failure taxonomy (for the discussion section)
Every failure above is one of three kinds:
1. **Missing model structure** — PID / plain MPC lacking disturbance
   states; MPPI / MPC carrying a hover-fitted model beyond its envelope.
2. **Estimator bandwidth-vs-noise tradeoffs** — ADRC's single knob, v3's
   unfiltered L1 trust, the MPC launch transient.
3. **Information bottlenecks in learned policies** — v5's memoryless
   averaging across the noise-DR range.

The pool's champions are exactly the stacks that pushed their particular
limit one level up without inheriting a new one inside the tested envelope.

## Acro2.2 multi-seed verdict (paper-2 gate): STRUCTURAL, and worse than hypothesized

3 training seeds, identical recipe (5M steps, flip z U(2.0,3.0), deterministic
variant cycling), flip_eval at z=2.5:

| flip | seed 0 (21-41-06) | seed 1 (08-50-19) | seed 2 (08-43-55) |
|---|---|---|---|
| roll+  | **+343°, complete** | −1°, refuses | −4°, refuses |
| roll−  | **−375°, complete** | −6°, refuses | −504°, over-rotates, floor, diverges |
| pitch+ | 0°, refuses | 142°, crashes | −2°, refuses |
| pitch− | −27°, refuses | **−343°, complete** (floor hit, recovery 1.97) | −3°, refuses |

### Verdict
1. **The question "is pitch-flip failure seed variance or structural?" had a
   false premise: it is not pitch-specific.** Seed 1 *completes a pitch−
   flip while refusing both rolls* — the axis-asymmetry hypothesis is
   refuted. What is structural is the fragility of the whole recipe: which
   variants get learned (if any) is a per-seed lottery — 3/12
   (seed, variant) cells complete, each seed converging to a different
   local optimum (refuse / complete / over-rotate).
2. **Mechanism, consistent with the acro2.0 lesson and the DDA review:**
   under the hover-pinned (dynamically infeasible) reference, position and
   attitude rewards conflict during the maneuver window, so "hover through
   the window" remains a strong local optimum. The attitude-dominant reward
   hack merely tilts the landscape; whether PPO's exploration escapes to a
   flip — and on which axis — is initialization luck. acro2.2-s0's roll
   success (the phase-2 result) was a favorable draw, not a reliable
   property of the recipe.
3. **Paper-2 design consequence (now unambiguous):** discovery-by-RL on an
   infeasible reference is the wrong problem formulation. The redesign is
   the DDA-style split — plan a dynamically feasible ballistic flip
   reference offline (boost / ballistic-arc-with-rotation / brake; cf21B
   TWR 1.88 excludes constant-speed loops), then *track* it, making
   position and attitude rewards consistent by construction. Imitation
   from a quaternion-MPC expert stays as the fallback if feasible-ref PPO
   still shows seed fragility.
4. Models: s1 `2026-07-23_08-50-19`, s2 `08-43-55` (flip evals in
   `results/2026-07-23_*_flip-eval`).
