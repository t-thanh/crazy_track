# Paper 2 — Acrobatic maneuver controller (CTBR flips on feasible references)

Learned body-rate (CTBR) acrobatics for the Crazyflie 2.1 brushless:
acro-tier tracking + 360-degree flip maneuvers with planned, dynamically
feasible references. **Status: started 2026-07-23; acro3 (ballistic
reference) 3-seed training in progress.**

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

## Current experiment (in progress)
- acro3 seeds 0/1/2, 5M steps (`--acro3`), eval via
  `python -m crazy_track.eval.flip_eval --model <zip> --ballistic`.
- **Zero-shot baseline to beat** (acro2.2-s0 on the ballistic ref,
  run `2026-07-23_17-46-20_flip-eval-ballistic`): rolls rotate but track
  the arc at 2.3-3.9 m deviation with floor hits; pitch refuses. Success
  criterion: complete rotations on >= 3/4 variants per seed, max_ref_dev
  well under 0.5 m, min_z >= hover z, across all 3 seeds.

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
