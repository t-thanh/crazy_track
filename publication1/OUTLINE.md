# Paper 1 — Outline, claim map, and figure plan

**Working title.** *Benchmarking Trajectory-Tracking Controllers for a Nano-Quadrotor
under Disturbances and Realistic Sensing: Convergence, Failure Modes, and the Cost of
Single-Seed Reporting*

**Venue / format.** SPIE Proceedings, `\documentclass[nocompress]{spie}`.
Target length 10–12 pages including references.

**Framing (decided).** Benchmark + failure-mode taxonomy. Secondary threads that must
survive into the abstract and conclusion: (i) the deployment-cell convergence result,
(ii) the statistical-qualification argument (variance phenomena, seed luck, transients).

**Scope honesty (decided).** Simulation-only, stated explicitly in the abstract, again
in Sec. 3.1, and quantified in the limitations subsection.

**Naming (decided).** Descriptive names for the learned policies, with a mapping table
to the repository version tags in Sec. 4.6:

| paper name | repo tag | one-line definition |
|---|---|---|
| DATT-Base | v2 | randomized-difficulty refs, no L1 channel, no force DR |
| DATT-L1 | v3 | + per-episode force perturbations + L1 estimate in the observation (43-dim) |
| DATT-Noisy | v4 | DATT-L1 trained on Lighthouse-noisy observations (43-dim) |
| DATT-Asym | v5 | + asymmetric actor–critic (privileged critic) + noise-level DR (56-dim) |
| DATT-Stack | v6a | + 4-frame stacked actor observation (185-dim); reported as a negative result |

Classical stacks keep their conventional names: PID+ff, ADRC(ESO), MPPI+L1, MPC,
Offset-free MPC, PID+xadapt, ADRC+xadapt.

---

## 1. ABSTRACT (written — `abstract.tex`)

~250 words. Platform + reference family + common interface; the eight stacks;
five disturbance/sensing conditions; seed protocol; then the three headline results
(no dominance / ~0.06 m three-way convergence, three-class failure taxonomy,
mean-only tables mislead); closing scope caveat.

## 2. INTRODUCTION (`introduction.tex`)

### 2.1 The challenge
- Trajectory tracking on nano-quadrotors is where model error, actuation limits,
  external forces and state-estimation quality all bind at once. TWR 1.88 and 43 g of
  mass leave little control authority margin; a 10 g payload is 23 % of weight, and a
  2.5 m/s² wind is ~25 % of hover thrust in the lateral channel.
- The literature reports controllers on different platforms, references, metrics and
  sensing stacks. Cross-paper numbers are therefore not comparable, and — more
  damaging — *failure modes* are rarely reported at all: papers report the cell where
  the proposed method wins.
- Two under-reported effects motivate this study and recur throughout it:
  (a) **variance**: several stacks have acceptable *mean* error and unacceptable
  *tail* behaviour under a bad sensor-bias draw; (b) **transients**: benchmark
  references that start at nonzero velocity generate launch excursions that a fixed
  warm-up window does not remove, and which are easily misattributed to steady-state
  noise sensitivity.

### 2.2 Related work
Four threads, each ending in what we take from it and what remains open.
1. *Benchmarks and replication.* Learning-to-Fly-in-Seconds (Fig. 5 / Table III
   Lissajous protocol, real-world PID / geometric / nonlinear / INDI / RL pool)
   — we adopt the reference family and metric verbatim. DATT (simulated and real
   figure-eights, infeasible-trajectory tier). Open: no common disturbance and
   sensing matrix, no seed statistics.
2. *Classical disturbance rejection.* ADRC / extended state observers; L1 adaptive
   control; offset-free / disturbance-augmented MPC; INDI. Open: the bandwidth-vs-noise
   trade-off is stated qualitatively far more often than it is measured.
3. *Sampling-based and optimization-based tracking.* MPPI with correlated exploration;
   nonlinear MPC on system-identified closed-loop attitude models; solver-failure and
   real-time behaviour. Open: internal-model validity outside the identification
   envelope.
4. *Learned tracking policies.* DATT-style feedforward-window policies with L1
   augmentation; asymmetric actor–critic / privileged-critic training; domain
   randomization over sensor noise; learned adaptive low-level rate controllers
   trained across airframes (xadapt). Open: what the learned stacks actually buy once
   the classical stacks are tuned *in the same conditions*.

### 2.3 Our approach
- One platform, one simulator, one reference family, one control interface level,
  one metric — vary only the controller and the condition.
- Eight stacks spanning: no estimator (PID), lumped-disturbance observer (ADRC),
  sampling MPC + L1 (MPPI+L1), optimization MPC with and without a disturbance state,
  learned low-level adaptation under classical outer loops (xadapt stacks), and
  learned end-to-end tracking policies (DATT family).
- A disturbance/sensing matrix: constant wind, gust (sinusoid + Ornstein–Uhlenbeck),
  in-ground-effect thrust gain, added payload, a literature-grounded Lighthouse
  measurement model, and their combination.
- A seed protocol that separates *evaluation* randomness (sensor bias, gust
  realization, sampling noise: 10 seeds) from *training* randomness (policy
  initialization: 3 seeds), so that policy-level and controller-level claims carry
  different, appropriate error bars.

### 2.4 Contributions (bulleted in the paper)
1. A controlled eight-stack benchmark under a shared disturbance and sensing matrix on
   a single nano-quadrotor platform, with every cell reported as mean ± std over
   seeds and every claim tied to a reproducible run manifest.
2. The **deployment-cell convergence result**: under Lighthouse sensing plus wind,
   an offset-free MPC, a privileged-critic learned policy, and an ESO over a learned
   adaptive rate loop are statistically indistinguishable at ≈0.06 m — three unrelated
   mechanisms hitting the same wall, which we argue is estimator-limited.
3. A **three-class failure taxonomy** (missing model structure / estimator
   bandwidth-vs-noise / information bottleneck in memoryless policies) that accounts
   for every failure observed in the pool, with a per-controller limit analysis.
4. Two **methodological findings with retraction value**: a launch transient
   masquerading as noise fragility (root-caused, fixed by ESO soft-start, and shown to
   be generic to the MPC family), and a single-seed conclusion that inverts at three
   training seeds.
5. Two documented **negative results** — innovation-scheduled adaptive ESO bandwidth,
   and frame stacking for noise-level inference — reported with the mechanism that
   explains each.

## 3. METHODOLOGY (`methodology.tex`)

### 3.1 Platform and simulation
- crazyflow, `cf21B_500` (Crazyflie 2.1 brushless, 500 mAh): m = 43.38 g,
  J = diag(25, 28, 49)·10⁻⁶ kg m², per-motor thrust 0.0214–0.2 N → collective
  0.0855–0.8 N, TWR 1.88.
- Ground truth: `first_principles` rigid-body dynamics with a firmware-replica
  Mellinger attitude loop at 500 Hz. Internal model for MPC/MPPI: the
  system-identified second-order closed-loop attitude model `so_rpy` (CasADi symbolic
  export) — a deliberate, documented model mismatch.
- Explicitly *absent* from the ground truth: aerodynamic drag, motor asymmetry,
  battery sag, estimator lag (unless the sensor model is enabled). Consequence:
  absolute errors are optimistic by roughly 5–10× versus published hardware numbers;
  the study is a *relative* comparison. Anchors that do line up are listed
  (ordering vs the DATT simulation table, the fast-lobe overshoot signature, the
  out-of-distribution failure of an under-trained policy).

### 3.2 Reference family and metrics
- p(t) = [A cos ωt, B sin 2ωt, z], A = 1 m, B = 0.5 m, z = 1 m, ω = 2π/T,
  two cycles; T ∈ {15.0, 5.5, 3.5} s (slow / normal / fast) plus a T = 2.2 s acro tier
  used only for the graceful-degradation discussion; vertical (x–z) variant.
- Metrics: RMSE₃D, RMSE_xy, max error, all excluding a 1 s warm-up
  (per-sample-magnitude RMS, not per-axis).
- The drone starts at rest at p(0) while the reference starts at |v| = 1.14 m/s
  (normal tier) — the transient this creates is analysed in Sec. 5.4, not hidden.

### 3.3 Control interface and fairness protocol
- All attitude-mode stacks command [roll, pitch, yaw, collective thrust] at 100 Hz;
  yaw is held at zero. The xadapt stacks run at 500 Hz into `rotor_vel` because that is
  the rate their pretrained low-level was trained at, with the outer loop decimated to
  100 Hz — the fairness argument and its caveat are stated here.
- Shared allocation block (`acc2attitude`): thrust projected on the current body-z,
  desired attitude from the desired thrust direction, roll/pitch clipped at 1 rad.

### 3.4 Controller pool — formulation and tuning
One paragraph + equation block per stack, each ending with *how it was tuned and what
the tuning cost*:
1. **PID + acceleration feedforward.** kp = 16, kd = 8, ki = 2 (ω = 4 rad/s,
   ζ = 1), integral clipped at 0.5 m·s. Honest baseline; the clipped integrator is
   the mechanism behind its payload/wind failure.
2. **ADRC.** Reduced-order velocity ESO driven by the commanded acceleration,
   ℓ₁ = 2ω_o, ℓ₂ = ω_o², σ clipped at ±3 m/s², no integrator. Tuning history is a
   *result*: a full-order position ESO at ω = 25 diverged; ω = 10 sat on the
   attitude-loop lag frequency; the bandwidth sweep (Sec. 5.5) sets ω = 7.
3. **MPPI + L1.** so_rpy rollouts, H = 25 at dt = 0.02 s (0.5 s), N = 512, λ = 0.02,
   AR(1) exploration noise β = 0.7, Σ = diag(0.08, 0.08, 0.02 rad, 0.04 N); L1
   estimate (a_s = −5, 4 Hz) injected as a constant disturbance across the horizon.
   Tuning sweep table (four configs) — temporally correlated noise is the main win.
4. **MPC.** CasADi/ipopt multiple shooting, H = 20 at dt = 0.04 s, position +
   velocity-reference + input + input-rate costs, box constraints, warm start,
   max 60 iterations, tol 1e-4, previous-iterate fallback on solver failure.
5. **Offset-free MPC.** Same NLP with a constant disturbance-acceleration state fed by
   a velocity ESO (ω = 7), plus the **soft-start** ramp d_plan(t) = σ·min(1, t/1.5)
   introduced in this work.
6. **PID + xadapt / 7. ADRC + xadapt.** Pretrained adaptive low-level rate controller
   (never trained on this airframe) at 500 Hz; attitude-P to CTBR, kp_att = 8,
   rate clip 10 rad/s; only calibration is the max motor speed (hover sweep) plus an
   outer integrator (ki = 6) — or, in the ADRC variant, the ESO absorbing the same
   thrust-calibration offset.
8. **DATT family.** Observation = position error, velocity, quaternion, a 10-step
   0.6 s relative reference window, and the L1 estimate (43-dim); actions map to
   ±0.7 rad roll/pitch and collective thrust.

### 3.5 Policy training
- PPO (SB3), 16 envs, n_steps 256, batch 1024, lr 3e-4, γ = 0.98, MLP [64, 64],
  3–4 M steps; 50 Hz policy rate; 6 s episodes; reward exp(−2‖e‖) − 0.02‖a₀:₂‖ with
  −5 crash penalty at z < 0.05 m or ‖e‖ > 2 m.
- Training references: C²-chained quintics, per-episode difficulty
  v ~ U(0.5, 3.5) m/s, a ~ U(1, 10) m/s², segment U(1.0, 2.5) s. Zero-shot evaluation
  on the Lissajous — the policies never see the benchmark trajectory.
- Domain randomization: per-episode constant force ±3.5 m/s² (vertical halved);
  initial position ±5 cm; for DATT-Noisy/-Asym the batched Lighthouse model in the loop
  (20 ms latency at 50 Hz), and for DATT-Asym a per-episode noise scale U(0, 1.5).
- Asymmetric actor–critic: the critic additionally sees true position error, true
  velocity, true attitude and the true perturbation acceleration (13 privileged dims),
  zero-padded and ignored at evaluation.
- **Note for the paper:** `configs/datt.yaml` is stale and unused; all effective
  parameters are the code values above. Do not cite the YAML.

### 3.6 Disturbance and sensing conditions
- `wind_const` 0.11 N (≈2.5 m/s², 60 % of the DATT perturbation ceiling);
  `wind_gust` mean 0.08 N + 0.08 N sinusoid at 0.7 Hz + OU turbulence (σ = 0.04,
  τ = 0.5 s); `ground` Cheeseman–Bennett thrust gain 1/(1 − (R/4z)²) evaluated on a
  z = 0.08 m trajectory; `payload` 10 g (23 % of weight).
- **Lighthouse measurement model** (grounded in the Bitcraze LH2 characterization
  dataset): position ZOH at 34 ± 18 Hz, 0.7 mm jitter, per-episode quasi-static bias
  σ = 1.5 cm/axis (≈2.6 cm 3D), velocity 3 cm/s, attitude 0.5°, gyro 0.02 rad/s,
  one control step (10 ms) of latency on the optical chain only — the gyro bypasses
  the delay (onboard IMU). The gyro-latency bug and its 0.78 → 0.05 m effect on the
  500 Hz rate loop is reported as a methodological caveat.

### 3.7 Statistical protocol
- Evaluation seeds (10) drive sensor bias, gust realization and MPPI sampling;
  training seeds (3) drive policy initialization, with the evaluation seed fixed so the
  two sources do not mix.
- Every table reports mean ± std [min–max] where the spread matters; population std.
- Run provenance: every run directory carries date, a mandatory free-text reason, the
  git commit and the config; the claim→run manifest is reproduced in an appendix table.

## 4. RESULTS (`results.tex`)

### 4.1 Nominal replication (3 speeds)
Table + Fig. 2/4. Offset-free MPC records 0.004 / 0.036 / 0.052; ADRC+xadapt best at
normal (0.018); PID+xadapt and MPPI contest fast (0.067 / 0.068 — a 0.001 difference
inside a ±0.014 spread, called as noise). The Fig. 5 qualitative signature (clean slow,
corner cutting at normal, lobe overshoot at fast) is reproduced.

### 4.2 Force disturbances (wind, gust, payload, ground)
Table + Fig. 5 heatmap. ADRC wins constant wind (0.025 vs PID 0.109);
DATT-L1 is pool-best under gusts (0.061 ± 0.002); ADRC+xadapt makes the payload
invisible (0.018 = its own nominal); PID wins ground effect because the thrust-gain
disturbance is nearly collinear with its feedforward. Plain MPC is the most fragile
(0.196) — no disturbance state, no integral action.

### 4.3 Realistic sensing (Lighthouse) and the deployment cell
Table + Fig. 6. Three-way tie at 0.057 ± 0.014 / 0.059 ± 0.002 / 0.060 ± 0.009;
DATT-Noisy at 0.077 ± 0.006; plain MPC at 0.199 ± 0.017. Argument for
*estimator-limited*: three architectures with disjoint mechanisms converge, and the
gap to their own clean-sensing numbers is larger than the gap between them.

### 4.4 Variance is a first-class result
Fig. 7. MPPI's fast-tier crown does not survive Lighthouse (0.228 ± 0.178,
range 0.091–0.480); DATT-L1's Lighthouse-fast failure is a variance phenomenon
(0.323 ± 0.106) while DATT-Asym is a variance collapse (0.126 ± 0.007). Explicit
statement: mean-only tables would have inverted two of these conclusions.

### 4.5 Launch transients versus steady-state noise
Fig. 8 + the three-step investigation: bandwidth sweep → time-series root cause
(0.7–1.5 m excursion at t = 0.5–1.6 s; steady-state RMSE 0.046 ± 0.008) → soft-start
fix (new nominal records; 0.178 → 0.141 full-window) → discriminating test showing
plain MPC spikes identically on the same seeds, i.e. the residual is generic to the
family, not to the disturbance observer.

### 4.6 Learned-policy ablation and the seed retraction
Fig. 10 + the three-training-seed table. DATT-Asym dominates or ties DATT-Noisy in all
eight measured cells; the earlier single-seed "asymmetric training costs clean-state
performance" reading is retracted with the mechanism (best draw vs worst draw).
DATT-Stack is statistically equivalent to DATT-Asym — a negative result with a stated
reason (four-fold input with unchanged capacity; an 80 ms window spans only 2–3
position updates).

### 4.7 Estimator design studies (two negative results)
ADRC bandwidth sweep across six conditions (Fig. 9): no fixed ω wins both noise/static
and gusts; ω = 7 chosen as the balanced default. Innovation-scheduled adaptive ω wins
its target gust cells (0.071 vs 0.080) and degrades all calm cells (0.060 vs 0.023),
because the statistic cannot separate external disturbance from the observer's own
attitude-lag residual. L1 as a post-filter or as a replacement for the ESO is measured
and is second-best in both roles.

### 4.8 Failure taxonomy and recommendations
Fig. 11 + a per-controller limits table (the eight bullet analyses), then the
condition-indexed recommendation table: which stack to choose given sensing quality,
disturbance character, agility demand, and compute budget (offset-free MPC costs
20–70 s wall per episode; learned policies are a single forward pass).

## 5. CONCLUSION (`conclusion.tex`)
No dominance; condition-indexed recommendations; the convergence result and its
estimator-limited reading; the taxonomy as a design lens (each champion is the stack
that pushed one taxonomy class up a level without inheriting another); the
methodological argument for seed statistics and transient auditing; limitations
(idealized simulation: no drag, battery sag, motor asymmetry; no hardware flights;
single airframe; yaw held fixed); future work (recurrent policies for noise-level
inference, state pre-filtering ahead of the optimizer, reference-aware residual
whitening for adaptive-bandwidth observers, hardware validation).

---

## Figure and table plan

| # | type | content | data source | tool |
|---|---|---|---|---|
| F1 | diagram | Benchmark architecture: crazyflow ground truth, sensor model, disturbance injection, the three control interfaces, the eight stacks | schematic | TikZ |
| F2 | 3-panel plot | Figure-5 replication: reference vs tracked XY at slow / normal / fast for PID, offset-free MPC, DATT-Asym | `results/*_fig5-final/*.npz` | matplotlib → PDF |
| F3 | 2-panel plot | Lighthouse model: true vs measured x over 2 s (ZOH staircase + bias offset), and the update-interval histogram | regenerate from `sensors.py` | matplotlib |
| F4 | grouped bars | Nominal RMSE₃D by stack × speed (log y) | root README table / `summary.csv` | matplotlib |
| F5 | heatmap | Stack × condition RMSE₃D matrix (nominal, wind, gust, payload, ground, LH, LH+wind), log colour, values annotated | reports 07-22 / 07-23 | matplotlib |
| F6 | dot + error bar | Deployment cell ranking with seed spread; tie band shaded | `ms-mpcof-lhwind-s*`, `mst-v5-lhwind-s*`, `ms-lhwind-xa-s*` | matplotlib |
| F7 | strip/scatter | Per-seed RMSE for the variance phenomena: MPPI LH-fast, DATT-L1 LH-fast, DATT-Asym LH-fast | `ms-lhfix-s*`, `ms-lh-s*` | matplotlib |
| F8 | time series | Position error vs time, offset-free MPC pre/post soft-start and plain MPC on a bad seed; warm-up and steady-state windows shaded | `mpcof-*`, `mpc-plain-lh-s{4,8}` npz | matplotlib |
| F9 | line plot | ADRC RMSE vs ESO bandwidth ω ∈ {3,5,7,10} for six conditions; crossing point annotated | report 07-22 table | matplotlib |
| F10 | grouped bars | DATT ablation ladder across scenarios, with training-seed error bars | `mst-v{4,5}-*-s{0,1,2}` | matplotlib |
| F11 | diagram | Failure taxonomy: three classes, stacks mapped to the class they resolve and the class they inherit | schematic | TikZ |
| T1 | table | Controller pool: interface, rate, internal model, estimator, tuned parameters | code | — |
| T2 | table | Nominal 3-speed RMSE | as F4 | — |
| T3 | table | Disturbance matrix | as F5 | — |
| T4 | table | Lighthouse and deployment cells with seed statistics | aggregators | — |
| T5 | table | Per-controller limits and failure class | discussion | — |
| T6 | table | Claim → evidence → run manifest (appendix) | `papers/paper1-benchmark/README.md` | — |

**Figure production note.** F2, F3, F7, F8 need the raw `.npz` series and must be
generated in WSL against the run directories; F4, F5, F6, F9, F10 can be built from the
tabulated numbers already in `reports/`. All figures go to `publication1/figures/` as
PDF (vector) at a 3.3 in single-column / 6.8 in double-column width, 8 pt labels.

## Writing order
1. Abstract (done) → 2. Methodology (most factual, least contested) →
3. Results → 4. Introduction and related work (written last so the contributions match
what the results actually support) → 5. Conclusion → 6. Figures → 7. Full number audit
against `reports/`.
