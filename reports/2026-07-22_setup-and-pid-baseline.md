# 2026-07-22 — Setup, benchmark definition, PID baseline

## Purpose of this note
First project report: pin down the benchmark being replicated, document the
simulation stack decisions, and record the first controller (PID) results.

## Benchmark definition (corrected understanding)
arXiv:2311.13081 is **"Learning to Fly in Seconds"** (Eschmann, Albani,
Loianno / NYU ARPL) — not the DATT paper (that is arXiv:2310.09053). Figure 5 +
Table III of the paper benchmark trajectory tracking on a figure-eight
Lissajous:

    p(t) = [A cos(2*pi*t/T), B sin(4*pi*t/T), z],  A = 1 m, B = 0.5 m

at three cycle times: **slow T=15s, normal T=5.5s, fast T=3.5s** (fast reaches
~3 m/s, 0.9g). Metrics: RMSE `e` (3D) and `e_xy` (horizontal). Their controller
pool: PID, Geometric, Nonlinear, INDI, and their learned RL policy.

**Our replication:** same trajectory/metrics, in crazyflow (CPU, WSL2), with
the pool: PID, ADRC, MPPI+L1, MPC (lsy-style), DATT-PPO. The DATT policy design
(feedforward reference window + L1 adaptation, from arXiv:2310.09053 /
KevinHuang8/DATT) is trained on random chained polynomials and evaluated
zero-shot on the Lissajous.

## Simulation stack decisions
- **Drone: `cf21B_500`** = Crazyflie 2.1 **brushless**, 500 mAh battery (the
  target platform, confirmed in crazyflow's `drones/params.toml`):
  mass 43.38 g, J = diag(25, 28, 49)e-6 kg m^2, motor thrust 0.0214–0.2 N
  → max collective 0.8 N, **thrust-to-weight ≈ 1.88**.
- **Dynamics: `first_principles`** (rigid body + firmware-replica Mellinger
  attitude loop at 500 Hz) as benchmark ground truth. crazyflow also provides
  `so_rpy` — a system-identified 2nd-order closed-loop attitude model **with
  CasADi symbolic export** (`crazyflow.dynamics.so_rpy.symbolic_dynamics`),
  which we will use as the *internal model* for MPC/MPPI (this mirrors
  lsy_drone_racing's MPC formulation).
- **Control interface:** `[roll, pitch, yaw, collective_thrust_N]` at 100 Hz
  (crazyflow attitude mode; ≥100 Hz recommended). All controllers in the pool
  use this interface — a fair comparison at the same control level.
- Episode: 2 Lissajous cycles; RMSE excludes a 1 s warmup (drone starts at
  rest but the reference starts with nonzero velocity — the paper's real
  flights enter the trajectory in motion).

## PID baseline results (run 2026-07-22_14-55-23_lissajous)
Cascaded position PID + velocity/acceleration feedforward → Mellinger-style
(thrust, attitude) conversion. Gains kp=16, kd=8, ki=2 (acceleration units),
untuned first guess.

| speed  | T (s) | RMSE 3D (m) | RMSE xy (m) | max err (m) |
|--------|-------|-------------|-------------|-------------|
| slow   | 15.0  | 0.012       | 0.012       | 0.018       |
| normal | 5.5   | 0.022       | 0.021       | 0.033       |
| fast   | 3.5   | 0.088       | 0.086       | 0.147       |

Qualitative XY plots reproduce the paper's Figure-5 pattern: near-perfect at
slow, corner-cutting at normal, systematic lobe overshoot at fast (the drone
swings wide where centripetal acceleration peaks). This is the expected
feedback-lag signature that predictive (MPC/MPPI) and learned (DATT)
controllers should beat.

For context, the paper's real-world Table III RMSEs are in the 0.1–0.5 m
range — our sim numbers are optimistic (no state estimation noise, no motor
wear, perfect model), so cross-controller *relative* comparison is the
meaningful output, not absolute parity with the paper.

## Reproduction
```bash
python -m crazy_track.eval.lissajous_benchmark --controllers pid --reason "..."
```
Results: `results/2026-07-22_14-55-23_lissajous/` (metadata.yaml records
date-time, reason, git commit, config; npz per rollout; summary.csv).

## Classical pool results (runs 14-58-25, 15-00-11, 15-07-31)

RMSE 3D (m), 2 cycles, 1 s warmup excluded, cf21B_500 first_principles:

| controller | slow  | normal | fast  | notes |
|------------|-------|--------|-------|-------|
| PID        | 0.012 | 0.022  | 0.088 | kp=16 kd=8 ki=2, acc feedforward |
| ADRC       | 0.012 | 0.034  | 0.089 | reduced-order velocity ESO w=10, sigma clip 3 |
| MPPI+L1    | 0.042 | 0.045  | 0.089 | H=25 N=256 so_rpy model, temperature 0.05 |
| MPC        | 0.018 | 0.063  | 0.083 | CasADi/ipopt H=20 dt=0.04, vel-ref + dU costs |

### Findings
- **ADRC v1 diverged** (RMSE > 5 m): a full-order position ESO at w_obs=25
  attributed attitude-loop lag to disturbance; the cancellation term fed back
  its own lag and wound up. Fix: reduced-order ESO on measured velocity,
  w_obs=10, disturbance estimate saturated at 3 m/s^2. After the fix ADRC ==
  PID in nominal (disturbance-free) conditions, as theory predicts — its
  advantage should only appear once we add wind/mass offsets.
- **MPC v1 underperformed** (normal 0.135, fast 0.277): position-only cost +
  heavy input-rate penalty made it lag the reference. Adding a velocity
  reference term (w=0.05) and relaxing dU 0.5→0.1 fixed it: fast 0.083, the
  current pool best at that speed.
- **MPPI+L1** is competitive at fast but noisier at slow speeds (sampling
  noise floor ~4 cm). More samples / lower temperature / colored noise would
  likely help; not yet tuned.
- All classical controllers show the same fast-lobe overshoot signature as
  the paper's classical pool in Figure 5.

## Next
1. DATT-PPO: training launched (run 2026-07-22_15-04-23_datt-train, 2M steps,
   16 envs, random chained-poly refs). Eval zero-shot on Lissajous when done.
2. Disturbance scenarios (wind, payload) where ADRC/L1/DATT should separate
   from PID/MPC.
3. MPPI tuning; consider acados for real-time-feasible MPC timings.
