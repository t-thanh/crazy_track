# Paper 2 — Acrobatic trajectory tracking (CTBR policy, Crazyflie 2.1 brushless)

**Scope (user-clarified 2026-07-23): tracking ACROBATIC TRAJECTORIES in
general** — where paper 1 benchmarks controllers on the flat figure-8,
paper 2 is the acrobatic regime: the **vertical figure-8** (normal / fast /
acro tiers), the **acro tier at/beyond the platform feasibility limit**
(T=2.2 s demands more lateral/vertical acceleration than TWR 1.88 provides),
and **attitude-referenced maneuvers (360-degree flips)** as the extreme case
where attitude can no longer be derived from position. One learned
body-rate (CTBR) policy should cover the whole spectrum.

Unifying thesis candidate: acrobatic tracking fails when references are
dynamically infeasible — laterally (acro-tier fig-8: graceful degradation),
vertically (vertical acro fig-8: demands negative thrust), or in attitude
(hover-pinned flips: position/attitude conflict). The fix is
feasibility-aware reference treatment: planned feasible maneuver primitives
(flips, done) and possibly feasibility-projected fig-8 references (open
design question — currently we measure graceful degradation instead).

**Status: acro3 (ballistic flip reference) validated at 3 seeds; 10M
extensions in progress; full acro-trajectory-suite benchmark of the acro3
policies queued.**

## Scope and story arc
1. **datt_acro v1** (`2026-07-22_18-58-56`): CTBR policy, refs to the TWR
   limit. Wins both acro-tier trajectories (0.322 horizontal / 0.349
   vertical at T=2.2 s), degrades gracefully where attitude-mode stacks
   diverge; first Lighthouse rows 0.063/0.109/0.147 (lowest fast-tier
   variance in the pool). This is the paper's "envelope robustness" result.
2. **acro2.0-2.2 (negative results, all documented)**: flips via RL
   discovery against a hover-pinned position reference.
   - 2.0: reward mis-specification — hovering was reward-optimal (0-deg
     flips).
   - 2.1: attitude-domination reward hack -> 2/4 variants flip, floor hits.
   - 2.2: altitude margin + variant cycling -> roll± complete (seed 0), but
     the **3-seed test (2026-07-23) exposed the recipe as a per-seed
     lottery**: 3/12 (seed,variant) cells complete; one seed does pitch-
     while refusing rolls. Not pitch-specific — structural.
   - Two further structural flaws found post-hoc: the reference attitude
     profile was rate-infeasible at the short end (24.7 rad/s demanded vs
     15 rad/s limit), and the level-flight reward bonus leaked into
     aggressive non-flip episodes.
3. **Design pivot (the paper's central argument)**: plan-then-track.
   Reviewed Deep Drone Acrobatics (RSS20) and the ZJU-FAST-Lab planners
   (Aerobatic-Planner / am_traj / GCOPTER): flat-output optimizers are
   singular at a flip's zero-thrust core; DDA's constant-speed loops need
   TWR ~2.2 (cf21B: 1.88). The minimal correct instance for a TWR-limited
   in-place flip is the closed-form **ballistic primitive**:
   boost -> zero-thrust arc + rotation -> brake (Lupashin-style), with
   position and attitude references consistent at every instant.
4. **acro3 (current)**: `BallisticFlipTrajectory` (feasibility guaranteed by
   tests: thrust in [0, 0.95*TWR*g], never below start altitude, rate <=
   0.75*RATE_MAX) + balanced maneuver reward (domination hack retired).
   3 training seeds from day one.

## Acro3 5M-step results (2026-07-23 evening): formulation VALIDATED
- **6/12 cells complete (+2 near-misses at 272-306°) vs acro2.2's 3/12**;
  10/12 cells attempt large rotations (hover local optimum eliminated).
- **Pitch asymmetry gone**: pitch flips complete on 2/3 seeds; pitch+
  completed for the first time in the project (s1: +323°).
- s1 completes ALL FOUR variants (first-ever full coverage); s2's completed
  flips already beat the precision targets (ref_dev 0.44, recovery
  0.05-0.07, no floor contact); s0 lags (over-rotates rolls, refuses pitch
  while tracking the arc) — execution-precision failures, not refusals.
- Models: s0 `2026-07-23_17-46-18`, s1 `17-46-23`, s2 `18-48-13`.

## 15M results + acro suite (2026-07-23 late): two tensions identified
- Flips @15M: s1 4/4 (358-381 deg, near-exact), s2 3/4 at the best
  precision yet (dev 0.26-0.74, recovery 0.06-0.10), s0 WORSE with budget
  (bad optimum; budget hypothesis refuted for that seed). 7-8/12 vs 3/12
  (acro2.2).
- Acro suite @15M vs flip-free datt_acro v1: **flip capability costs
  general tracking 1.3-2x** on most cells (full table in report
  2026-07-23). One 46-dim policy splits capacity between maneuvers and
  tracking.
- **DECISION POINT (awaiting user): A. maneuver-conditioned obs (one-hot,
  recommended) / B. lower flip-episode ratio / C. specialist policies /
  D. rotation-completion reward term.** Models: s0@15M
  `2026-07-23_19-40-03`, s1@15M `19-40-06`, s2@15M `21-35-52`.

## Queued after acro3
- Recovery precision < 0.3 m; maneuver-conditioned obs (variant one-hot).
- Fallback if acro3 still seed-fragile: DAgger from a quaternion CTBR-MPC
  expert (DDA recipe; our so_rpy Euler MPC cannot serve — singular at
  +-90 deg pitch).
- Hardware-transfer caveat to address in writing: sim force_torque mode
  gives torque authority at zero collective; real flips need a small
  collective floor during the rotation (~2 cm displacement effect,
  analysis in report 2026-07-23).

## Key models / runs
- datt_acro v1: `2026-07-22_18-58-56`; acro-tier benchmark runs 19-24-47+.
- acro2.2 seeds: s0 `2026-07-22_21-41-06`, s1 `2026-07-23_08-50-19`,
  s2 `2026-07-23_08-43-55`; flip evals `2026-07-23_09-{45,50}-*_flip-eval`.
- acro3 seeds: training in progress (2026-07-23 evening) — see
  `results/*_datt-train` metadata with `acro3: true`.

## Analysis trail
- `reports/2026-07-22_lighthouse-sensor-mppi-tuning.md` (datt_acro v1,
  acro2.0-2.2 sections).
- `reports/2026-07-23_multi-seed-training-and-lighthouse-refresh.md`
  (DDA review, acro2.2 3-seed verdict, ballistic design + acro3 kickoff).
- Report naming convention from 2026-07-23 on: `reports/*_p2-*.md`.
