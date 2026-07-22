# Session handover — 2026-07-22

For the next agent/session picking up this project. Read this + `README.md`
first; deep context is in `reports/*.md` (chronological) and per-run
`results/*/metadata.yaml` (every run has a date-time, reason, git hash).

## What this project is
Trajectory-tracking benchmark on the Crazyflie 2.1 brushless (`cf21B_500`) in
the crazyflow simulator, replicating Fig-5/Table-III of "Learning to Fly in
Seconds" (arXiv:2311.13081), extended with disturbances, a Lighthouse (LH2)
sensor model (arXiv:2104.11523), acrobatics, and multi-seed statistics.
Remote: https://github.com/t-thanh/crazy_track (push after every commit).

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
  with `set -o pipefail` (a tail pipe once masked a failure — see reports).
- Windows-side pure-numpy tests: `.venv-win`, `python -m pytest tests/`.

## Current state (all 19 tasks closed)
- 8 controller stacks benchmarked: PID, ADRC(w=7), MPPI+L1(tuned), MPC,
  offset-free MPC, PID+xadapt, ADRC+xadapt, DATT v2-v6a + acro/flips.
- Champions: offset-free MPC = nominal records (slow 0.006 / fast 0.053);
  ADRC+xadapt vs DATT v5 statistically TIED at deployment (lh+wind ~0.06);
  DATT v3 best under gust (0.061±0.002, confirmed at 10 seeds).
- Flips (acro2.2, model `results/2026-07-22_21-41-06_datt-train/`): roll±
  complete with altitude margin; **pitch flips unlearned** (open).
- Key models: v3 `16-35-10`, v5 `17-32-52`, acro `18-58-56`, acro2.2
  `21-41-06` (all `datt_ppo_final.zip` under `results/<run>_datt-train/`).

## Known gotchas (hard-won; do not rediscover)
1. `sensors.py`: gyro must BYPASS the Lighthouse latency buffer (onboard
   IMU). Pre-fix lighthouse rows for MPC/MPPI/datt_acro are stale (see next).
2. Controller sim modes cannot mix in one benchmark run: attitude vs
   force_torque (datt_acro) vs rotor_vel (xadapt*). xadapt runs at 500 Hz
   with outer-loop decimation 5.
3. DATT model versions are auto-detected from obs dim (43/46/56/185).
4. Flip reward: attitude term must DOMINATE during the maneuver window or
   PPO rationally refuses to flip (acro2.0 lesson).
5. Multi-seed: eval randomness = sensor bias + gust + MPPI sampling
  (`--seed` on the benchmark CLI); nominal PID/ADRC/MPC runs are deterministic.

## Open items (priority order)
1. **Multi-seed TRAINING runs** (3+ seeds per DATT config): the only
   unqualified claims left are policy-level (v5-vs-v4 deltas, and whether
   pitch-flip failure is seed variance or structural). Use
   `training/ppo_train.py --seed N`; ~15-50 min/run on this CPU.
2. **Re-run stale lighthouse rows** (MPC, MPPI, datt_acro) post gyro fix.
3. **Offset-free MPC noise-robust ESO input** (lighthouse normal is
   0.178±0.076 — ESO ingests position-ZOH noise; try w=3-5 under sensing
   or LPF the innovation).
4. Adaptive-ESO v2 (reference-aware residual whitening) — documented
   negative result, optional.
5. Acro phase 3: pitch flips (multi-seed first), recovery precision <0.3 m,
   maneuver-conditioned obs (variant one-hot).
6. Optional realism: drag model (`so_rpy_rotor_drag`), battery sag, motor
   asymmetry; xadapt norm_RMS.npz warning (uses default csv stats).

## How to run (from WSL venv, repo root)
- Benchmark: `python -m crazy_track.eval.lissajous_benchmark --controllers
  pid adrc ... --reason "..."` (+ `--disturbance`, `--sensor lighthouse`,
  `--vertical`, `--seed`, `--speeds slow normal fast acro`).
- Flips: `python -m crazy_track.eval.flip_eval --model <zip> --reason "..."`.
- Training: `python -m crazy_track.training.ppo_train --reason "..."`
  (flags: --noisy-sensor, --v5, --v6, --ctbr, --acro2; see README).
- Seed stats: `python -m crazy_track.eval.aggregate_seeds --prefix ms-`.
- ALWAYS pass a meaningful `--reason`; commit results + report updates and
  `git push origin main` after each work unit.
