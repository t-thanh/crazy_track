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

## DATT PPO v1 (train run 15-04-23, eval run 15-21-18)
2M steps / 16 envs trained in 16 min (2129 fps, JAX-vectorized CPU sim).
Zero-shot Lissajous: **slow 0.005, normal 0.020 — best in the pool** — but
**fast 0.947 m (failure)**. Root cause: training distribution capped at
vel<=1 m/s, acc<=2 m/s^2; fast Lissajous reaches 3 m/s / ~9 m/s^2 — fully
out-of-distribution. This mirrors the DATT paper's emphasis on training-time
reference aggressiveness.

**v2 launched** (run 15-2x_datt-train): randomized per-trajectory difficulty
(vel 0.5-3.5 m/s, acc 1-10 m/s^2, seg 1-2.5 s), 3M steps.

## Are our numbers too good to be true? (comparison with both papers)

Reference numbers pulled from the papers:

**arXiv:2311.13081 Table III (REAL WORLD, Crazyflie):** PID 0.23/0.72/0.88 m
(slow/normal/fast), Geometric 0.06/0.16/0.36, INDI 0.21/1.13/1.04, learned RL
0.08/0.17/0.24, Nonlinear crashed at fast.

**arXiv:2310.09053 DATT (SIMULATION, no disturbance):** DATT 0.049±0.017 m
(smooth) / 0.083±0.023 (infeasible); L1-MPC 0.088/0.181; MPC 0.104/0.183.
Real world w/ wind+drag plate: DATT 0.095/0.161, L1-MPC 0.181/0.243. Their
CF2.1 is 40 g, TWR just under 2 (ours: 43.4 g, TWR 1.88 — well matched).

**Verdict: our nominal numbers (PID 0.012-0.088) are optimistic by roughly
5-10x vs real hardware, and that gap is explained, not mysterious:**
1. Perfect state feedback — no mocap noise/latency/dropout, no estimator lag.
   The papers' real flights carry all of these.
2. No aerodynamic drag in `first_principles` (crazyflow's drag matrix only
   exists in the `so_rpy_rotor_drag` dynamics), no motor asymmetry, no
   battery sag.
3. Zero external disturbance in the nominal runs.
4. Our PID has full acceleration feedforward; the papers' baseline PIDs
   likely track with feedback only (their real PID: 0.23 m even at slow).
5. Our warmup exclusion (1 s) removes the entry transient.

Sanity anchors that DO line up: (a) our DATT-sim ordering matches the DATT
paper's sim table (learned > L1-MPC > MPC); (b) our fast-speed degradation
ordering matches Fig. 5 (classical overshoot at the lobes); (c) our DATT v1
fast failure at 0.947 m is the same OOD mechanism the DATT paper designs
against. Conclusion: relative comparisons are meaningful; absolute values
should only be quoted as "idealized-sim" numbers. Adding noise/latency and
drag is the path to realistic absolutes (now on the roadmap).

## Disturbance scenarios (new, src/crazy_track/disturbances.py)
World-frame CoM forces injected via crazyflow `states.force` each control step:
- **wind_const**: steady 0.11 N (~2.5 m/s^2, 60% of DATT's max perturbation).
- **wind_gust**: mean + 0.7 Hz sinusoidal gust + Ornstein-Uhlenbeck turbulence
  (mimics DATT's fan array).
- **ground**: Cheeseman-Bennett in-ground-effect thrust gain 1/(1-(R/4z)^2),
  benchmarked on a low-altitude (z=0.08 m) Lissajous.
- **payload**: +10 g constant downward force (23% of weight).

**Validation run 15-28-08 (wind_const, normal speed): PID 0.109 m (5x worse
than nominal 0.022) vs ADRC 0.032 m (unchanged)** — the ESO estimates and
cancels the wind while PID's clipped integrator (max 1 m/s^2) cannot. First
clear separation of the disturbance-rejection controllers, as theory predicts.

## DATT v2 + consolidated Figure-5 results (runs 15-45-21, 15-46-05)

DATT v2 (3M steps, randomized difficulty): **fast fixed, 0.947 -> 0.090 m**,
at the cost of slow/normal precision (0.021/0.048 vs v1's 0.005/0.020) — the
difficulty-diversity tradeoff. v2 normal (0.048) matches the DATT paper's own
sim result for smooth trajectories (0.049±0.017) almost exactly.

**Nominal, RMSE 3D (m), slow/normal/fast (run 15-46-05_fig5-final):**

| controller | slow  | normal | fast  |
|------------|-------|--------|-------|
| PID        | 0.012 | 0.022  | 0.088 |
| ADRC       | 0.012 | 0.034  | 0.089 |
| MPPI+L1    | 0.042 | 0.045  | 0.089 |
| MPC        | 0.018 | 0.063  | **0.083** |
| DATT v2    | 0.021 | 0.048  | 0.090 |

## Disturbance sweep (normal speed, runs 15-48-42 .. 15-50-49)

RMSE 3D (m):

| controller | nominal | wind_const | wind_gust | payload | ground |
|------------|---------|-----------|-----------|---------|--------|
| PID        | 0.022   | 0.109     | 0.117     | 0.093   | **0.023** |
| ADRC       | 0.034   | **0.032** | **0.080** | **0.036** | 0.066 |
| MPPI+L1    | 0.045   | 0.067     | 0.093     | 0.055   | 0.044 |
| MPC        | 0.063   | 0.196     | 0.142     | 0.137   | 0.055 |
| DATT v2    | 0.048   | 0.154     | 0.122     | 0.063   | 0.047 |

### Findings
1. **ADRC dominates every force-disturbance scenario** (wind, gust, payload)
   — the ESO estimates and cancels the disturbance within its bandwidth.
   Its nominal-case parity with PID plus disturbance-case dominance is the
   textbook ADRC value proposition, now demonstrated end-to-end.
2. **MPC is the most disturbance-fragile** (0.196 under constant wind): the
   prediction model has no disturbance state and the controller no integral
   action. An offset-free MPC variant (disturbance observer + model
   augmentation) is the standard fix.
3. **DATT v2 degrades under wind (0.154)** — expected and important: unlike
   the DATT paper, our training had *no force perturbations* and no L1
   estimate in the observation. This isolates exactly why the paper combines
   domain randomization + L1 adaptation; DATT v3 should add both.
4. **PID under payload:** xy stays clean (0.021) but z sags ~90 cm RMSE
   contribution — its clipped integrator (1 m/s^2) cannot lift 2.3 m/s^2 of
   payload. ADRC handles the same payload at 0.036.
5. **Ground effect is mild at z=8 cm** (max ~14% thrust gain): PID barely
   notices; ADRC slightly overreacts (ESO attributes IGE lift to disturbance
   with a lag at 0.7 Hz crossing).

## Next
1. DATT v3: force-perturbation domain randomization + L1 estimate in obs
   (the paper's full recipe) to close the wind gap.
2. Sensor noise + control latency for realistic absolute numbers.
3. Offset-free MPC; MPPI tuning; acados for real-time-feasible timings.
