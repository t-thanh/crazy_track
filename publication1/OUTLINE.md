# Paper 1 — Outline, claim map, and figure plan (rev. 2, conference scope)

**Title.** *Quadrotor Trajectory Tracking under Varying Payloads and Wind: Benchmarking
Reinforcement Learning against Classical, Robust, Predictive, and Adaptive Control*

**Venue / format.** SPIE Proceedings, `\documentclass[nocompress]{spie}`.
**Target length ~10 pages including references.** This is the binding constraint on
every decision below.

**What changed in rev. 2**
- Controller pool cut from eight stacks to **six — one representative per control
  paradigm**, chosen as the best member of its own family in our data.
- Training, tuning and benchmark plumbing are compressed to what a reader needs to
  reproduce and to trust the numbers. Sweeps and ablations survive only where they
  carry a *lesson*, not as tables.
- Results are selected for interest, not coverage; the analytical weight moves into a
  dedicated **Lessons learnt** section.
- A **hardware validation** subsection is added to the methodology (WindShaper
  fan-array wind tunnel + OptiTrack PrimeX 22 motion capture); the corresponding
  results subsection is a reserved placeholder, to be filled when the campaign runs.

---

## Controller pool (final, six stacks)

| paradigm | representative | why this member | headline evidence |
|---|---|---|---|
| Classical feedback | **PID + acceleration feedforward** | the honest baseline; also the ground-effect champion | nominal 0.012/0.022/0.088; ground 0.023 |
| Optimization-based | **Offset-free MPC** (so\_rpy model + velocity-ESO disturbance state + soft-start) | dominates plain MPC in *every* cell, including nominal | nominal records 0.004/0.036/0.052; wind 0.045 |
| Robust / disturbance observer | **ADRC** (reduced-order velocity ESO, $\omega_o=7$) | constant-wind champion of the whole pool | wind 0.025 vs PID 0.109 |
| Sampling-based | **MPPI + $\mathcal{L}_1$** (N=512, AR(1) noise) | clean-sensing fast-tier champion | fast 0.068 |
| Hybrid adaptive | **ADRC + xadapt** (ESO outer loop over a pretrained learned rate controller) | best breadth in the pool; payload becomes invisible | normal 0.018; payload 0.018; gust 0.063 |
| Reinforcement learning | **DATT-Asym** (asymmetric actor–critic + noise DR; repo tag v5) | best policy in the realistic deployment cell, with a variance collapse | LH+wind 0.059 ± 0.002 (3 training seeds) |

Non-representatives appear **only** where they carry a lesson, never as table rows:
- *plain MPC* — as the discriminating control that proves the launch transient is
  generic to the MPC family (Sec. 4.5);
- *DATT-L1 / DATT-Noisy (v3/v4)* — as the two rungs of the ablation ladder that produce
  the single-seed retraction and the robustness-costs-agility measurement (Sec. 4.6),
  reported in three sentences and one small table, not a full study;
- *DATT-Stack (v6a)*, *adaptive-bandwidth ADRC* — one sentence each as documented
  negative results with their mechanism.

**Naming.** Descriptive names in the text; the mapping to repository tags
(DATT-L1 = v3, DATT-Noisy = v4, DATT-Asym = v5, DATT-Stack = v6a) appears once, in a
footnote in Sec. 3.4.

---

## 1. ABSTRACT (written — `abstract.tex`)
~270 words. Motivation (micro-UAV field operation: wind, payload change, imperfect
onboard state estimation) → the six-paradigm benchmark on one platform/reference/
interface/metric → conditions and seed protocol → three headline results (no dominance;
≈0.06 m three-way convergence in the deployment cell; mean-only reporting misleads) →
lessons-learnt framing → hardware validation campaign announced, with a marked
placeholder sentence for its result.

## 2. INTRODUCTION (~1.25 pages)

### 2.1 Challenge
Micro-UAVs in field operation face sustained and unsteady wind, payload changes that are
a large fraction of their own weight (10 g on a 43 g airframe = 23 %), and onboard
positioning far poorer than laboratory motion capture. On a platform with
thrust-to-weight 1.88 there is little authority to spare. Controllers for this regime
are reported on different platforms, references, metrics and sensing stacks, so their
relative merits — and especially their *failure modes* — cannot be compared across
papers.

### 2.2 Related work (four compact paragraphs, ~10–14 citations total)
1. Benchmarks and replication protocols (Learning-to-Fly-in-Seconds Fig. 5 / Table III
   Lissajous; DATT) — we adopt the reference family and metric verbatim.
2. Disturbance rejection: ADRC / extended state observers, $\mathcal{L}_1$ adaptive
   control, INDI, offset-free MPC.
3. Predictive and sampling-based tracking: nonlinear MPC on identified closed-loop
   attitude models; MPPI with correlated exploration.
4. Learned tracking: DATT-style feedforward-window policies, privileged/asymmetric
   critics, sensor-noise domain randomization, and cross-airframe learned low-level
   rate controllers (xadapt).
Each paragraph ends with the specific gap we close.

### 2.3 Contributions (4 bullets)
1. A **cross-paradigm benchmark** — six controllers, one per paradigm, on a single
   nano-quadrotor under a shared wind / gust / payload / ground-effect / realistic-
   sensing matrix, with per-cell seed statistics rather than single runs.
2. The **deployment-cell convergence result**: under realistic sensing plus wind, an
   offset-free MPC, a privileged-critic RL policy and an ESO over a learned adaptive
   rate loop become statistically indistinguishable at ≈0.06 m — evidence that the
   regime is estimator-limited, not architecture-limited.
3. A **lessons-learnt analysis** organised by a three-class failure taxonomy, including
   two findings that overturn conclusions we ourselves had drawn from single-seed,
   full-window data.
4. A **hardware validation protocol** in a programmable fan-array wind tunnel with
   motion capture, designed so that the physical disturbance conditions correspond
   one-to-one with the simulated ones.

## 3. METHODOLOGY (~3 pages)

### 3.1 Platform and simulator (0.4 p)
crazyflow, `cf21B_500` (Crazyflie 2.1 Brushless): m = 43.38 g,
J = diag(25, 28, 49)·10⁻⁶ kg m², collective thrust 0.085–0.8 N, TWR 1.88;
`first_principles` rigid body + firmware-replica Mellinger attitude loop at 500 Hz as
ground truth; the identified `so_rpy` second-order closed-loop attitude model as the
*internal* model for MPC/MPPI — a deliberate, disclosed mismatch. State plainly what the
simulator omits (drag, motor asymmetry, battery sag, estimator lag unless the sensor
model is on) and that absolute errors are consequently optimistic; this is the sentence
that licenses the hardware campaign in Sec. 3.7.

### 3.2 Reference family, metrics, and the fairness protocol (0.4 p)
p(t) = [A cos ωt, B sin 2ωt, z], A = 1 m, B = 0.5 m, two cycles,
T ∈ {15.0, 5.5, 3.5} s. RMSE₃D / RMSE_xy / max error with a 1 s warm-up excluded.
All stacks command [roll, pitch, yaw, collective thrust] at 100 Hz with yaw held at
zero; the xadapt stack runs its pretrained rate loop at 500 Hz with the outer loop
decimated to 100 Hz — stated as the one deviation, with its justification.

### 3.3 Controller pool (0.9 p — one short paragraph + key equation per stack)
Only what is needed to reproduce: the control law, the estimator, and the tuned
parameters, in a single compact table (T1). Tuning history is *not* narrated; where a
tuning outcome is itself a result (ADRC bandwidth) it moves to the lessons section.

### 3.4 The learned policy (0.5 p)
Observation (position error, velocity, attitude, 10-step 0.6 s relative reference
window, $\mathcal{L}_1$ estimate), action mapping, PPO settings in one sentence, the
training reference distribution, the domain randomization (force ±3.5 m/s², sensor-noise
scale, initial position), and the asymmetric critic's privileged inputs. Emphasise that
the policy is evaluated **zero-shot** on the Lissajous — it never sees the benchmark
trajectory. Footnote: the repo's `configs/datt.yaml` is stale and unused; parameters are
as stated here.

### 3.5 Disturbance models (0.3 p)
Constant wind 0.11 N (≈2.5 m/s²), gust = mean + 0.7 Hz sinusoid + Ornstein–Uhlenbeck
turbulence, Cheeseman–Bennett ground effect at z = 0.08 m, payload 10 g (23 % of
weight). One sentence each on why these magnitudes (they bracket the perturbation range
used in the DATT literature and are reproducible in the wind tunnel of Sec. 3.7).

### 3.6 Realistic sensing: the Lighthouse measurement model (0.3 p)
Position ZOH at 34 ± 18 Hz, 0.7 mm jitter, per-episode quasi-static bias 1.5 cm/axis
(≈2.6 cm 3D), velocity 3 cm/s, attitude 0.5°, gyro 0.02 rad/s, 10 ms latency on the
optical chain only (the gyro is an onboard IMU and bypasses the delay). Grounded in the
published LH2 characterization dataset — and note that its "2–4 cm accuracy" figure is
itself *motion-capture-referenced*, which is exactly the comparison Sec. 3.7 closes.

### 3.7 Hardware validation setup (0.5 p — WRITTEN, see `methodology.tex`)
- **Vehicle**: Crazyflie 2.1 Brushless, the airframe the simulation is parameterized on.
- **Wind**: WindShaper fan-array wind generator (iMMC, UCLouvain). Modules of ≈25×25 cm,
  each a 3×3 array of independently driven counter-rotating fan pairs ("wind pixels");
  wind speed up to ≈16–20 m/s; programmable turbulence intensity ≈5–30 %; spatial and
  temporal profile control u = f(x, y, t) at 0.1 s time steps through a Python API.
  The argument to make: a fan array can reproduce the *same disturbance classes* used in
  simulation — a uniform steady field and a periodic-plus-broadband gust — as programmed
  set points, so the simulated and physical conditions correspond rather than merely
  resemble each other.
- **Ground truth**: OptiTrack PrimeX 22, 2048×1088 at 360 fps (up to 1000 fps at reduced
  resolution), 79°×49° FOV, ±0.2 mm typical 3D accuracy, hardware sync. Two roles:
  the same RMSE metric as in simulation, and the reference against which the onboard
  Lighthouse estimate is measured — closing the loop on Sec. 3.6.
- **Conditions**: same Lissajous references and speeds; steady wind and gust profiles
  matched to the simulated magnitudes; payload steps of the same 23 % of weight;
  repetitions per cell to give hardware error bars comparable to the simulation seeds.
- **What it is designed to test** (state up front, so the campaign is falsifiable):
  (i) the deployment-cell convergence, (ii) payload invisibility of the hybrid adaptive
  stack, (iii) whether the variance behaviour predicted under the simulated Lighthouse
  model appears with a real positioning deck.
- Facility-specific numbers are marked TODO in the source and must be confirmed against
  the installation before submission.

### 3.8 Statistical protocol (0.2 p)
Ten evaluation seeds (sensor bias, gust realization, sampling noise) and three training
seeds (policy initialization, evaluation seed fixed). Mean ± std, with [min–max] where
the spread is the point. Every run directory carries a reason, git commit and config.

## 4. RESULTS AND LESSONS LEARNT (~3.5 pages)

### 4.1 Nominal tracking (0.4 p) — T2 + F2
Compact. Offset-free MPC sets the records (0.004/0.036/0.052); ADRC+xadapt best at
normal (0.018); MPPI takes fast (0.068). One qualitative point: the Fig. 5 signature
(clean at slow, corner cutting at normal, lobe overshoot at fast) reproduces, so the
benchmark behaves like the literature one before we perturb it.

### 4.2 Disturbances (0.7 p) — T3 + F3
Constant wind separates the pool by a factor of four (ADRC 0.025 vs PID 0.109); the gust
champion is the RL family through its disturbance channel; payload is invisible to the
hybrid adaptive stack (0.018 = its own nominal); ground effect is won by PID because the
thrust-gain disturbance is nearly collinear with its feedforward. The organising claim:
**every stack that beats PID does so through some form of disturbance estimation** — the
paradigms differ in where the estimate enters, not in whether one is needed.

### 4.3 Realistic sensing and the deployment condition (0.7 p) — T3 + F4
The headline. Three-way tie at 0.057 ± 0.014 / 0.059 ± 0.002 / 0.060 ± 0.009 m;
plain MPC an order of magnitude behind at 0.199 ± 0.017. Argument for
*estimator-limited*: three mechanisms with nothing in common converge, and each is
further from its own clean-sensing number than from the others.

### 4.4 Hardware validation (RESERVED — 0.6 p when filled)
Placeholder subsection with the table skeleton already in place: per-controller RMSE
under tunnel-generated steady wind, gust, and payload, against the simulated
counterparts, plus the sim-to-real gap column. To be written after the campaign.

### 4.5 Lessons learnt (1.1 p — the analytical core, T4)
Seven lessons, each stated as a claim, a mechanism, and the evidence:
1. **Disturbance estimation is the price of entry.** Everything above the baseline wins
   by estimating a lumped disturbance; the architectures differ in where the estimate is
   injected (control, prediction model, observation, or low-level adaptation).
2. **One bandwidth knob cannot do two jobs.** Low observer bandwidth filters noise and
   tracks static loads; high bandwidth tracks gusts; no fixed value wins both, and
   innovation-scheduled adaptation fails for an identifiable reason — the statistic
   cannot separate an external disturbance from the observer's own attitude-lag residual.
3. **Mean-only tables mislead.** Two pool leaders fail only on unlucky sensor-bias draws
   (0.228 ± 0.178, range 0.091–0.480; and 0.323 ± 0.106); the RL policy's advantage is a
   variance collapse (± 0.007), not a mean shift.
4. **Audit transients before blaming noise.** An apparent noise fragility was a launch
   excursion outside the warm-up window; steady-state error was a quarter of the
   full-window figure, the fix was a 1.5 s observer soft-start, and the residual is
   generic to the MPC family, not to the disturbance observer.
5. **Single-seed policy conclusions invert.** A clean-state regression we had reported
   reversed at three training seeds — the two policies had drawn their best and worst
   initializations respectively.
6. **Robustness is bought with agility, and the exchange rate is measurable.** Training
   on noisy observations improves the noisy cells and costs the clean ones; a memoryless
   policy averages over the randomization range instead of calibrating to the episode,
   and frame stacking did not fix it at this budget.
7. **Mechanisms compose when they address disjoint error sources.** An ESO cancelling
   external force over a learned rate loop that makes command realization
   airframe-independent yields payload invisibility — neither layer achieves that alone.

### 4.6 Recommendations (0.3 p — T4 second half)
A condition-indexed table: clean sensing and precision → offset-free MPC; sustained wind
with clean state → ADRC; payload and airframe change → hybrid adaptive; realistic
onboard sensing → any of the three tied stacks, chosen on compute (20–70 s wall per
episode for the optimizer versus a single forward pass for the policy) and on
initialization robustness.

## 5. CONCLUSION (~0.4 p)
No dominance; the convergence result and its estimator-limited reading; the lessons as a
transferable checklist for anyone publishing tracking numbers; limitations (idealized
simulator, single airframe, fixed yaw, hardware campaign pending at the time of writing
/ reported in Sec. 4.4); future work (recurrent policies for noise-level inference,
state pre-filtering ahead of the optimizer, reference-aware residual whitening).

---

## Figure and table plan (7 figures, 4 tables — sized for 10 pages)

| # | type | content | source | tool |
|---|---|---|---|---|
| F1 | diagram | Benchmark architecture: simulator ground truth, sensor model, disturbance injection, the six stacks, and the hardware-validation branch (tunnel + mocap) | schematic | TikZ |
| F2 | 3 panels | Fig. 5 replication: reference vs tracked XY at slow/normal/fast for PID, offset-free MPC, DATT-Asym | `results/*_fig5-final/*.npz` | matplotlib → PDF |
| F3 | heatmap | 6 stacks × 7 conditions RMSE₃D, log colour, annotated | reports 07-22 / 07-23 | matplotlib |
| F4 | dot + error bar | Deployment cell with seed spread; tie band shaded | `ms-mpcof-lhwind-s*`, `mst-v5-lhwind-s*`, `ms-lhwind-xa-s*` | matplotlib |
| F5 | strip plot | Per-seed RMSE for the variance phenomena vs the variance collapse | `ms-lhfix-s*`, `ms-lh-s*` | matplotlib |
| F6 | time series | Error vs time: offset-free MPC pre/post soft-start and plain MPC on a bad seed; warm-up and steady-state windows shaded | `mpcof-*`, `mpc-plain-lh-s{4,8}` | matplotlib |
| F7 | photo/diagram | Hardware setup: Crazyflie 2.1 Brushless in the WindShaper test section with the OptiTrack volume | to be taken during the campaign | — |
| T1 | table | Controller pool: paradigm, interface, rate, internal model, estimator, key parameters | code | — |
| T2 | table | Nominal RMSE₃D, three speeds | `results/*_fig5-final/summary.csv` | — |
| T3 | table | Disturbance + sensing matrix with seed statistics | aggregators | — |
| T4 | table | Lessons → mechanism → evidence, and the condition-indexed recommendation | discussion | — |
| T5 | table | *(reserved)* Hardware vs simulation, per condition, with the sim-to-real gap | campaign | — |

Dropped from rev. 1 to fit the page budget: the ADRC bandwidth sweep figure (becomes
three numbers inside Lesson 2), the DATT ablation-ladder figure (becomes a three-row
inset table in Sec. 4.5, Lessons 5–6), the Lighthouse-model illustration (becomes two
sentences in Sec. 3.6), and the taxonomy schematic (becomes the structure of T4).

## Status (2026-08-03)

Full draft written and compiling: abstract, introduction, methodology (3.1–3.8),
results (4.1–4.3, 4.5–4.6) and conclusion. Reserved / outstanding:

1. **Results 4.4 + Table 5 + Fig. 7** — hardware campaign, to be written after the runs.
2. **Figures 2, 4, 6** — currently framed placeholders in the source
   (`\figplaceholder`); generate from the `results/` run dirs and drop the PDFs into
   `figures/`.
3. **Open data cells** (marked `\tbd` in red in Table 3, and TODO comments in the
   source) — see the list below; these must be zero before submission.
4. **Facility numbers** in Sec. 3.7, pending confirmation on the UCLouvain installation.
5. **Length** — the draft renders long; trim candidates are listed below.

### Benchmark runs still needed
- ADRC at $\omega_o = 7$: nominal slow and fast (the current row mixes bandwidths);
  payload and ground effect (current values predate the retune).
- **ADRC at $\omega_o = 7$, LH + wind, 10 evaluation seeds.** Its single-seed 0.053 is
  nominally better than all three tied stacks — until this run exists, the paper cannot
  safely call the deployment tie three-way.
- Tuned MPPI + $\mathcal{L}_1$ under wind, payload, ground, and LH + wind.
- Offset-free MPC (soft-start) under gust, payload, ground.
- Ground effect for the hybrid adaptive stack and the RL policy.
- PID under LH + wind.

### Trim candidates if over length
Lesson 2's bandwidth numbers → one sentence; Lesson 6's ladder → two sentences plus the
inset; the related-work paragraphs → merge threads 3 and 4; Table 1 → fold the internal
model and disturbance columns together; Sec. 3.2's metric equation → inline.

## Writing order (completed)
Abstract ✔ → Methodology 3.7 ✔ → rest of Methodology ✔ → Results 4.1–4.3 ✔ →
Lessons 4.5 ✔ → Introduction ✔ → Conclusion ✔ → **next: figures, then the number audit
against `reports/`, then hardware subsections 4.4 / T5 / F7 when the campaign completes.**
