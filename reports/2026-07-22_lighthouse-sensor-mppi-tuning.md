# 2026-07-22 (later) — Lighthouse sensor model, MPPI tuning, DATT v3 launch

## Purpose
Move from idealized-sim numbers toward realistic absolutes using the actual
positioning system the lab targets (Bitcraze Lighthouse / SteamVR 2.0 base
stations); tune MPPI+L1; launch DATT v3 with the paper's full recipe.

## Lighthouse sensor model (src/crazy_track/sensors.py)
Grounded in the Bitcraze dataset paper, Taffanel et al., arXiv:2104.11523
(Table III + Fig. 6), LH2 case:

| quantity | paper value | model |
|---|---|---|
| position sample rate | 34 +/- 18 Hz (crossing beam) | jittered ZOH updates |
| precision/jitter | 0.3 mm (C.B.) / 0.7 mm (EKF) | 0.7 mm Gaussian |
| absolute accuracy | 2-4 cm mean vs mocap, 5 cm flight outliers | quasi-static bias, sigma 1.5 cm/axis |
| vel/attitude | onboard EKF w/ 1 kHz IMU | +N(0, 3 cm/s), +N(0, 0.5 deg), gyro 0.02 rad/s |
| latency | "additional latency of unknown source" | 1 control step (10 ms) |

## Results with Lighthouse sensor (run 16-36-29, RMSE 3D m, slow/normal/fast)

| controller | nominal | lighthouse |
|---|---|---|
| PID | 0.012/0.022/0.088 | 0.012/0.043/0.146 |
| ADRC | 0.012/0.034/0.089 | 0.081/0.096/0.172 |
| MPPI+L1 (untuned) | 0.042/0.045/0.089 | 0.057/0.060/0.303 |
| MPC | 0.018/0.063/0.083 | 0.009/0.121/0.067 |
| DATT v2 | 0.021/0.048/0.090 | 0.030/0.072/0.106 |

### Findings
1. **ADRC is the most sensor-noise-sensitive** (0.081 even at slow): the ESO
   differentiates the 34 Hz ZOH position steps and noisy velocity into a
   jittery disturbance estimate. Standard remedy: lower observer bandwidth
   under noise (w_obs 10 -> ~5) or feed the ESO the EKF-filtered signal only.
   This flips the earlier conclusion ordering: ADRC's disturbance advantage
   partly trades against noise robustness.
2. **DATT (learned) degrades most gracefully** (+~20% at fast) — consistent
   with the papers' argument that policies trained on randomized dynamics
   tolerate imperfect state.
3. **MPC normal shows a 0.77 m transient outlier** (single bad ipopt solve on
   noisy state) — worth adding solver-failure reuse of the previous input.
4. Absolute levels now approach the Fig-5 paper's real Table III (their RL:
   0.08/0.17/0.24) — remaining gap: no drag model, no battery sag, benign
   latency. The 3D-vs-xy split shows the sampled seed-0 bias draw was small
   (~1 cm); across-seed averaging is a TODO for publication-grade numbers.

## MPPI+L1 tuning (sweep, same session)

| config | slow | normal | fast |
|---|---|---|---|
| baseline: N=256, lambda=.05, white noise | 0.042 | 0.045 | 0.089 |
| **A: N=512, lambda=.02, AR(1) beta=.7, sigma*0.7** | **0.023** | **0.035** | **0.068** |
| B: N=512, lambda=.05, beta=.7 | 0.024 | 0.038 | 0.089 |
| C: N=256, lambda=.02, beta=.5, sigma*0.7 | 0.033 | 0.042 | 0.122 |

Config A is the new default (best at all speeds; fast 0.068 = overall pool
best nominal). Temporally correlated exploration noise is the main win —
white per-step noise averages itself out over the 0.5 s horizon.

## DATT v3 (training launched, run 16-35-10)
Full DATT recipe: v2 randomized-difficulty refs + per-episode constant force
perturbations (+-3.5 m/s^2 per axis, z halved for TWR 1.88) + L1 disturbance
estimate appended to the observation (43-dim). The eval controller runs its
own identical L1 estimator (controllers/l1.py, shared implementation).
Expectation: close the wind gap (v2: 0.154 under wind_const vs ADRC 0.032).

## Next
1. Eval DATT v3: nominal + disturbance sweep + lighthouse.
2. ADRC noise-robust retune (lower w_obs under lighthouse).
3. MPC: reuse previous solution on solver failure; seed-averaged lighthouse runs.
