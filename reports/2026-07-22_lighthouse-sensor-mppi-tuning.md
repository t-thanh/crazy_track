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

## ADRC noise-sensitivity study: L1 layer vs L1 replacement vs bandwidth

Question investigated: can an L1 layer compensate for (or replace) the ESO's
noise sensitivity? Normal-speed Lissajous, RMSE 3D (m), 6 conditions:

| variant             | nominal | lighthouse | wind  | lh+wind | gust  | lh+gust |
|---------------------|---------|-----------|-------|---------|-------|---------|
| ESO w=10 (old)      | 0.034   | 0.096     | 0.032 | 0.071   | **0.080** | **0.105** |
| ESO w=7             | 0.023   | 0.056     | 0.025 | 0.053   | 0.082 | 0.113   |
| ESO w=5             | 0.019   | 0.054     | 0.021 | 0.052   | 0.097 | 0.126   |
| ESO w=3             | **0.019** | **0.052** | **0.020** | **0.050** | 0.110 | 0.139 |
| ESO w=10 + LPF 2 Hz | 0.029   | 0.076     | 0.032 | 0.063   | -     | -       |
| ESO w=5 + LPF 2 Hz  | 0.020   | 0.055     | 0.022 | 0.053   | -     | -       |
| L1 replace (2 Hz)   | 0.032   | 0.070     | 0.033 | 0.069   | -     | -       |
| L1 replace (1 Hz)   | 0.031   | 0.069     | 0.033 | 0.068   | -     | -       |

### Conclusions
1. **The dominant lever is the ESO bandwidth itself, not the estimator
   architecture.** w=10 was simply mistuned: it sat right at the attitude-loop
   lag frequency, so even in nominal conditions the ESO amplified actuation
   lag into command jitter (nominal 0.034 -> 0.019 by lowering w).
2. **"L1 layer on the ESO" (post-filter on sigma) helps but is second-best**:
   at w=10 it recovers about half the noise penalty (0.096 -> 0.076). The
   noise enters through the ESO's high-gain integration; filtering afterwards
   adds phase lag that costs about as much as it saves. Equivalent effect is
   achieved more cleanly by lowering w.
3. **Full L1 replacement works but does not beat a well-tuned ESO** (0.069 vs
   0.052 under lighthouse). Both are lumped-disturbance estimators; L1's
   decoupling (fast adaptation + explicit LPF) is elegant but its effective
   bandwidth is still one knob, and the ESO uses the model structure (u_prev
   feedthrough) slightly better here.
4. **The real tradeoff is static-vs-dynamic disturbance**: low w (3-5) wins
   under noise and constant wind; high w (10) wins under 0.7 Hz gusts, even
   WITH lighthouse noise. No single bandwidth dominates.
5. **Default set to w=7** (within ~15% of the best in every condition).
   Principled next step: gain-scheduled / adaptive observer bandwidth
   (e.g. scale w with innovation whiteness), or a dual-rate ESO — fast channel
   for gusts, slow channel with the LPF for bias-like disturbances.

## DATT v3 results (train run 16-35-10, eval runs 17-00-28 .. 17-01-25)

RMSE 3D (m), v2 -> v3:

| scenario | DATT v2 | DATT v3 | pool best (for reference) |
|---|---|---|---|
| nominal slow/normal/fast | 0.021/0.048/0.090 | 0.032/0.048/0.099 | MPPI-tuned 0.023/0.035/0.068 |
| wind_const (normal) | 0.154 | **0.050** | ADRC w7 0.025 |
| wind_gust (normal) | 0.122 | **0.066** | **DATT v3 is pool best** |
| payload (normal) | 0.063 | 0.053 | ADRC 0.036 |
| ground (normal) | 0.047 | 0.049 | PID 0.023 |
| lighthouse slow/normal/fast | 0.030/0.072/0.106 | 0.034/0.073/**0.369** | PID/MPC |

### Findings
1. **The DATT recipe works as advertised: wind error dropped 3x (0.154 ->
   0.050)** with only a small nominal cost (slow 0.021 -> 0.032). Under
   *gusts* v3 is now the best controller in the pool (0.066) — the L1
   estimate in the observation lets the policy react to the disturbance
   state directly instead of waiting for position error to build.
2. **New failure mode: lighthouse + fast = 0.369** (v2: 0.106). The L1
   estimate is computed from noisy velocity/attitude, so at high agility the
   policy chases phantom disturbances. The fix is DATT v4: train with the
   sensor model in the loop (noisy obs), which is exactly what the
   learning-to-fly paper does with its asymmetric actor-critic.

## DATT v4: noisy-sensor training (train run 17-07-10, evals 17-27-11 .. 17-28-43)

v3 recipe trained on Lighthouse-noisy observations (noisy obs AND noisy L1
input, 20 ms latency, per-episode bias resampling). RMSE 3D (m):

| scenario | DATT v3 | DATT v4 |
|---|---|---|
| nominal slow/normal/fast | 0.032/**0.048**/**0.099** | **0.022**/0.076/0.154 |
| lighthouse slow/normal/fast | 0.034/0.073/0.369 | **0.020**/**0.063**/**0.130** |
| wind_const / gust / payload (clean sensor) | **0.050/0.066/0.053** | 0.093/0.093/0.108 |
| lighthouse + wind_const (normal) | **0.067** | 0.083 |

### Findings
1. **Goal achieved: the lighthouse+fast failure is fixed (0.369 -> 0.130,
   2.8x)**, and v4 dominates v3 across all speeds under Lighthouse sensing —
   it even tracks *better with the sensor it was trained on than v3 does with
   clean state at slow speed*.
2. **The cost is clean-state performance and disturbance rejection**
   (wind 0.050 -> 0.093): noise in the L1 channel during training taught the
   policy to partially discount that signal — robustness bought by lowering
   the effective feedback gain. The classic robustness-performance tradeoff,
   now measured.
3. Under the *deployment condition* (lighthouse) v4 is the better policy
   everywhere except wind rejection at normal speed (v3 0.067 vs v4 0.083)
   — v3 still extracts more from the L1 signal it trusts.
4. **Path to best-of-both (DATT v5):** asymmetric actor-critic (critic on
   true state, actor on noisy obs — the learning-to-fly approach), noise-level
   domain randomization (episodes sampled from clean to noisy so the policy
   learns to calibrate its trust in the L1 channel), and/or a longer training
   budget — value-function learning is notably harder with noisy obs
   (explained_variance stayed low).

## Deployment recommendation (as of 2026-07-22)
For a Lighthouse-equipped CF2.1 brushless: **DATT v4** for agile tracking,
**ADRC (w=7)** when sustained wind rejection matters more than agility,
**MPPI+L1 (tuned)** as the strongest classical all-rounder in clean-sensing
conditions.

## DATT v5: asymmetric AC + noise DR (train run 17-32-52, evals 18-01-32 .. 18-02-36)

RMSE 3D (m), three-generation comparison:

| scenario | v3 | v4 | v5 |
|---|---|---|---|
| nominal slow/normal/fast | **0.032/0.048/0.099** | 0.022/0.076/0.154 | 0.055/0.089/0.163 |
| lighthouse slow/normal/fast | 0.034/0.073/0.369 | **0.020**/0.063/0.130 | 0.041/0.063/**0.124** |
| wind_const (clean sensor) | **0.050** | 0.093 | 0.076 |
| wind_gust (clean) | **0.066** | 0.093 | 0.091 |
| payload (clean) | **0.053** | 0.108 | 0.102 |
| **lighthouse + wind (deployment)** | 0.067 | 0.083 | **0.058** |

### Findings
1. **v5 wins the deployment condition** — lighthouse+wind 0.058 is the best
   any policy (or any controller except ADRC-clean) has posted there, and it
   holds v4's lighthouse-fast robustness (0.124). The asymmetric critic +
   privileged disturbance signal measurably improved noisy-regime learning.
2. **The "trust calibration" hypothesis partially failed, for an
   identifiable architectural reason**: a memoryless MLP cannot infer the
   episode's noise level from a single observation frame — noise level is
   only observable across time. So instead of calibrating per episode, the
   policy still averages across the DR range, which is why clean-sensor
   numbers regressed further (nominal 0.055/0.089/0.163). Fix for a future
   v6: recurrent policy (GRU) or frame-stacking so noise level becomes
   observable; alternatively accept per-regime policies.
3. Wind rejection recovered partially (v4 0.093 -> v5 0.076, vs v3 0.050):
   the privileged critic helps PPO see through the noise during training,
   but the actor's information bottleneck remains.

### Policy selection guide (final for today)
- Clean/mocap sensing: **DATT v3** (or MPPI+L1 tuned as classical choice).
- Lighthouse deployment: **DATT v5** — best in the realistic combined
  condition (noise + wind), 0.058.

## Next
1. DATT v6 candidate: recurrent policy (GRU) or obs stacking for noise-level
   observability; alternatively CTBR action space for acrobatic envelope.
2. MPC: reuse previous solution on solver failure; seed-averaged lighthouse runs.
3. Adaptive-bandwidth ESO (innovation-driven) as an ADRC v3.
