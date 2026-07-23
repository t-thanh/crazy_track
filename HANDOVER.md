# Session handover — 2026-07-23

For the next agent/session picking up this project. Read this + `README.md`
first; deep context is in `reports/*.md` (chronological) and per-run
`results/*/metadata.yaml` (every run has a date-time, reason, git hash).

## What this project is — TWO PAPERS (user-stated 2026-07-23)
Trajectory-tracking benchmark on the Crazyflie 2.1 brushless (`cf21B_500`) in
the crazyflow simulator, replicating Fig-5/Table-III of "Learning to Fly in
Seconds" (arXiv:2311.13081), extended with disturbances, a Lighthouse (LH2)
sensor model (arXiv:2104.11523), acrobatics, and multi-seed statistics.
Remote: https://github.com/t-thanh/crazy_track (push after every commit).
- **Paper 1 — controller benchmark on fig-8 scenarios. PRIORITY; nearly
  camera-ready on the results side** (all statistical qualifications done).
- **Paper 2 — acrobatic maneuver controller (CTBR / flips). Starts after
  paper 1.** Design direction reviewed and documented (see below).

## Environment (CRITICAL — read before running anything)
- Windows 11 host; **all sim work runs in WSL2 `Ubuntu-24.04`** (default
  distro, user `tient`), venv at `~/venvs/crazy_track`.
- Run pattern (PowerShell quoting + CRLF both bite; scripts live in the
  session scratchpad and are piped through `tr -d '\r'`):
  `wsl -d Ubuntu-24.04 -- bash -c "tr -d '\r' < /mnt/c/<script>.sh | bash"`
- Repo path from WSL: `/mnt/c/Users/tient/Documents/GitHub/crazy_track`.
  `/etc/wsl.conf` has `[automount] options="metadata"` (required).
- xadapt controllers need `~/xadapt_ctrl` (cloned) + `onnx onnxruntime` in
  the venv (installed). `SCIPY_ARRAY_API=1` is set by `crazy_track/__init__`.
- Background training: launch via `run_in_background` PowerShell wsl calls
  with `set -o pipefail`. Two parallel training streams (n_envs=16 each) fit
  on the 14-core box; RunLogger now suffixes -b/-c/-d on same-second
  collisions (fixed 2026-07-23 after it killed a stream).
- Windows-side pure-numpy tests: `.venv-win`, `python -m pytest tests/`.

## Paper-1 state: all statistical qualifications CLOSED (2026-07-23)
- 8 controller stacks benchmarked; key single-cell champions:
  - **Offset-free MPC + soft-start ESO: nominal records 0.004/0.036/0.052**
    (slow/normal/fast). Its scary lighthouse cell (0.178±0.076) was
    root-caused as a *launch transient* artifact (steady-state 0.046±0.008);
    soft-start (DISTP ramp over 1.5 s) fixed the ESO's share; the residual
    is generic MPC-on-noisy-state launch behavior (plain MPC is equally bad
    on bad seeds — its old 0.122 was a lucky 3-seed sample).
  - **Deployment (lh+wind): DATT v5 0.059±0.002 (3 TRAINING seeds) vs
    ADRC+xadapt 0.060±0.009 (10 eval seeds) — statistically tied.**
  - v5-vs-v4 at 3 training seeds: v5 dominates or ties in all 8 cells;
    deployment + wind cells non-overlapping. The old "v5 costs clean-state
    performance" claim was RETRACTED (seed-0 luck, see report 2026-07-23).
  - DATT v3 best under gust (0.061±0.002, 10 eval seeds) — unchanged.
  - Lighthouse refresh post gyro fix: MPC rows re-validated (fix was a
    non-event); tuned-MPPI lighthouse-fast exposed as high-variance
    (0.091-0.480 — clean-sensing fast champion does not survive LH);
    first datt_acro LH rows (0.063/0.109/0.147, lowest fast-tier variance).
- Multi-seed protocol: eval seeds via `--seed` on the benchmark CLI
  (sensor bias + gust + MPPI sampling); TRAINING seeds via
  `ppo_train --seed`, evaluated at fixed eval seed 0, aggregated with
  `aggregate_seeds --prefix mst-`.
- Key models: v3 `16-35-10`, v4 s0/s1/s2 `17-07-10`/`2026-07-23_06-47-56`/
  `08-05-04`, v5 s0/s1/s2 `17-32-52`/`06-49-11`/`07-30-13`, acro `18-58-56`,
  acro2.2 s0 `21-41-06` (all `datt_ppo_final.zip` under results/).

## Paper-1 remaining (optional polish only)
1. Optional realism: drag model (`so_rpy_rotor_drag`), battery sag, motor
   asymmetry; xadapt norm_RMS.npz warning (uses default csv stats).
2. If the lighthouse-normal MPC cells ever matter: launch transient
   remedies (state pre-filter/EKF, reference ramp-in, or a hover-spinup
   metric change — the last needs a deliberate protocol decision).
3. Writing the actual paper text (results are table-ready in the reports).

## Paper 2 state and next steps
- **acro2.2 3-seed verdict (2026-07-23): the recipe is structurally
  seed-fragile, and it is NOT pitch-specific** — seed 1 completes pitch−
  while refusing both rolls; seed 2 refuses/over-rotates everything; only
  3/12 (seed, variant) cells complete. s0's roll success was a favorable
  draw. Root cause: hover-pinned infeasible reference makes position and
  attitude rewards conflict — "hover through the window" stays a strong
  local optimum and escape direction is initialization luck. Models:
  s1 `2026-07-23_08-50-19`, s2 `08-43-55`.
- **Design review done (report 2026-07-23): Deep Drone Acrobatics (RSS20)**,
  and the 3-seed result makes its conclusion the mandatory starting point:
  discovery-by-RL on an infeasible reference is the wrong formulation.
  **Paper-2 design: ballistic feasible flip reference** (Lupashin-style
  boost/ballistic-arc/brake as a consistent position+attitude reference —
  cf21B TWR 1.88 cannot fly DDA constant-speed loops, which need ~2.2),
  then track it; the maneuver-window reward hack should become unnecessary.
  DAgger from a quaternion MPC expert is the fallback if feasible-ref PPO
  still shows seed fragility.
- Then: recovery precision <0.3 m, maneuver-conditioned obs (variant
  one-hot).

## Known gotchas (hard-won; do not rediscover)
1. `sensors.py`: gyro must BYPASS the Lighthouse latency buffer (onboard
   IMU). (Re-validated: the pre-fix MPC/MPPI rows were fine anyway.)
2. Controller sim modes cannot mix in one benchmark run: attitude vs
   force_torque (datt_acro) vs rotor_vel (xadapt*). xadapt runs at 500 Hz
   with outer-loop decimation 5.
3. DATT model versions are auto-detected from obs dim (43/46/56/185).
4. Flip reward: attitude term must DOMINATE during the maneuver window or
   PPO rationally refuses to flip (acro2.0 lesson) — superseded for paper 2
   by the feasible-reference design, which removes the conflict entirely.
5. Benchmark references start at nonzero velocity with the drone at rest:
   launch transients pollute RMSE past the 1 s warmup for noise-sensitive
   optimizers. Check max-err timing before blaming steady-state noise
   (the offset-free MPC lesson, 2026-07-23).
6. Single-seed nominal-slow DATT comparisons are meaningless (±0.015
   training-seed noise on both v4 and v5).

## How to run (from WSL venv, repo root)
- Benchmark: `python -m crazy_track.eval.lissajous_benchmark --controllers
  pid adrc ... --reason "..."` (+ `--disturbance`, `--sensor lighthouse`,
  `--vertical`, `--seed`, `--speeds slow normal fast acro`).
  MPC variants: `mpc`, `mpc_offsetfree`, `mpc_offsetfree_w<N>` (ESO bw).
- Flips: `python -m crazy_track.eval.flip_eval --model <zip> --reason "..."`.
- Training: `python -m crazy_track.training.ppo_train --reason "..."`
  (flags: --noisy-sensor, --v5, --v6, --ctbr, --acro2, --seed; see README).
- Seed stats: `python -m crazy_track.eval.aggregate_seeds --prefix ms-`
  (eval seeds) / `--prefix mst-` (training seeds).
- ALWAYS pass a meaningful `--reason`; commit results + report updates and
  `git push origin main` after each work unit.
