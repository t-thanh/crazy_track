# Handover plan — train a racing stack from a blank page to beat the lsy leaderboard

**Goal.** Fastest lap on the lsy_drone_racing level-2 online competition
(github.com/learnsyslab/lsy_drone_racing). Targets to beat: **3.419 s**
(current board, 100 % success) / **3.394 s** (all-time, winter25). Note the
board resets each semester — the *standing* target is 3.394 s.

**Teaching goal (equal priority).** Students leave with a *methodology* —
hypothesis → experiment → verdict — not a bag of tricks that happened to
work. Every phase below has a pre-registered question, a measurable gate,
and a kill criterion. The rules at the end are distilled from the
crazy_track project's measured failures, each tagged with the receipt.

---

## 0. Protocol facts that shape everything (verified against their repo)

1. **The clock starts with the drone ON THE GROUND** (start z = 0.01 m) and
   stops at the last gate. Takeoff is inside your lap time.
2. **Evaluation = 20 randomized episodes.** Ranking = fastest average over
   successful runs, **subject to ≥ 50 % success (≥ 10/20)**. Speed–risk is
   therefore an explicit design dial, not an afterthought.
3. **Level-2 randomization** (from `config/level2.toml`): drone mass
   ±0.005 kg (**±11.5 %** of the 43.38 g airframe), inertia jitter, gate
   position ±0.15 m xy / ±0.10 m z, gate yaw ±0.2 rad, obstacle ±0.15 m,
   start pose jitter, action noise, dynamics disturbance.
4. **Sensor range 0.7 m**: you see *nominal* gate/obstacle poses until the
   drone is within 0.7 m of the true one — then the exact pose snaps in.
   Whatever you build must absorb a mid-approach reference jump.
5. **Allowed control interfaces: `state` or `attitude` only.** Our paper-2
   CTBR interface (`force_torque`) is **not submittable**. What transfers
   from crazy_track: the attitude-mode DATT v5 recipe (asymmetric
   actor-critic + domain randomization), the trajectory/feasibility
   toolkit, the evaluation discipline. What does not: the acro policy
   itself.
6. Submission may change only `controller.file` and `env.control_mode`;
   same drone (cf21B_500, TWR 1.88), same sim (crazyflow, 500 Hz), env at
   50 Hz. Extra Python deps are allowed via the project files.
7. Install their repo in **its own venv** — never into the crazy_track
   venv (dependency cross-contamination cost us an afternoon once; don't).

## 1. What we already measured that de-risks this (crazy_track receipts)

- **Closed-form plan-then-track posts 4.464 s** on the *nominal* track
  (full state, no takeoff, no randomization): plan floor 4.49 s at cruise
  3.0 m/s, tracker actually *beat* its reference by corner-cutting.
  **Tracking was not the bottleneck — the plan was** (never brakes: min
  thrust demand along the ref stayed at 8 m/s²). The ~1 s to the leaders
  is plan optimality, now with a measured bound.
- DATT-style trackers: RMSE ≈ 0.13 m at the fast tier, robust under
  sensor noise when trained with noise DR (v5). Aggressive-reference
  training distributions (to 5 m/s, 15 m/s²) work.
- **Best-precision checkpoint ≠ most robust checkpoint** (measured twice,
  independently: racing test and paper-1 crossover). Select checkpoints
  against the *leaderboard criterion*, nothing else.

## 2. Phases

Each phase: question → experiment → gate → kill criterion. Timeboxes
assume a student team with one shared GPU-less workstation (all our
training was CPU; 8 M PPO steps ≈ 1.7 h at 16 envs).

### Phase 0 — Reproduce their evaluation, byte for byte (week 1)

*Question:* what exactly is being scored?
*Do:* fresh venv; run `scripts/evaluate.py` on the shipped
`state_controller` and on `attitude_controller` if present; log per-episode
times, success causes of failure; render two episodes.
*Also:* port our closed-form race trajectory as a `state`-mode controller
(feed `FreestyleTrajectory` setpoints at 50 Hz) and score it under THEIR
protocol — takeoff, randomization, sensor gating included. This is the
known-good baseline and the first honest number.
*Gate:* a baseline table (their controllers + our port) over 20 episodes ×
3 protocol seeds, plus a one-page protocol memo.
*Kill criterion:* none — this phase cannot fail, only be skipped, and
skipping it is how teams discover the takeoff clock in week 5.

### Phase 1 — Bottleneck decomposition before any optimization (week 2)

*Question:* where does the time actually sit? Decompose
`lap = takeoff + Σ segment times`, and gap = (plan floor − physics floor)
+ (flown − plan) + (risk margin).
*Do:*
1. **Physics floor**: point-mass time-optimal bound through the nominal
   gate sequence with |a| ≤ 0.95·TWR·g (bang-bang, students derive it).
   If the floor is ≈ 2.8–3.0 s, beating 3.394 s is physics-feasible and
   the winnable slack is quantified.
2. **Plan floor**: our 4.49 s closed-form number, re-derived by the
   students with the time-scaling law.
3. **Flown vs plan**: from Phase-0 telemetry.
*Gate:* a one-page decomposition with numbers. Every later experiment must
name which term it attacks.
*Kill criterion:* if physics floor > 3.4 s (it won't be, but compute it),
the goal is impossible and the target moves to "top of this semester's
board" — decided by data, not morale.

### Phase 2 — Two competing hypotheses, raced head-to-head (weeks 3–5)

Strong inference: run both tracks with pre-registered comparison, don't
argue about which is better — measure.

**Track A — plan-then-track.** Time-optimal trajectory through the
nominal gates (upgrade our per-segment heuristic to real optimization:
MINCO-style or even CMA-ES over segment durations under the feasibility
checker), tracked by (i) their state interface directly, and (ii) a
DATT-v5-style attitude policy trained on a racing reference distribution.
Handles randomization by *replanning locally* when a gate pose snaps in
(0.7 m sensor range).
- Attacks: the 1 s plan-optimality term (our known dominant term).
- Known risk: replan latency and the reference jump; brittle under gate
  displacement.

**Track B — end-to-end RL.** Attitude-mode policy, observations in
*gate-relative* frames (current + next gate, nominal-vs-known flag),
progress-along-track + gate-passage reward, trained under level-2
randomization *from day one* (DR ≥ eval ranges — v5 lesson), asymmetric
actor-critic (privileged true poses to the critic, sensor-gated obs to the
actor). Their repo ships an RL scaffold (`train_rl.py`); literature anchor:
champion-level racing results are end-to-end.
- Attacks: plan optimality *and* robustness in one object (the policy
  discovers its own racing line, including takeoff).
- Known risk: reward shaping iterations; discovery pathologies — if the
  policy stalls at a behavior boundary, apply the state-dense vs
  action-dense gradient diagnosis before adding hacks (paper-2 step-5
  lesson).

*Pre-registered decision (end of week 5):* frozen protocol, 20 episodes ×
3 protocol seeds × 3 training seeds (learned tracks). Score = mean
successful time s.t. ≥ 50 % success. Winner becomes the main line; loser
survives only if within 5 %.

### Phase 3 — Robustness and the speed–risk frontier (weeks 6–7)

*Question:* what is the fastest setting that still clears 10/20?
*Do:* one aggressiveness knob (time-allocation scale for Track A; reward
speed weight or reference-speed cap for Track B). Sweep it; plot
(mean time, success rate) with 3 seeds per point. Pick the knee, then back
off one notch (their 20-episode draw adds binomial noise: at true p = 0.5,
P(fail the gate) ≈ 41 % — flying *at* the constraint is a coin flip;
students compute this).
*Also:* takeoff optimization is free time nobody budgets — a dedicated
minimum-time ground-to-first-gate segment (it is inside the clock; nominal
first gate is known before launch).
*Gate:* the frontier plot with the chosen operating point marked and the
binomial argument written down.

### Phase 4 — Selection, submission, report (week 8)

- Checkpoint selection on **validation protocol seeds disjoint from
  anything ever tuned on**; final claim numbers on a third, untouched seed
  set. (Receipt: our "best" seeds inverted between precision and
  robustness twice; selection on the training signal would have shipped
  the wrong model.)
- Submit; then write the report that would let next semester reproduce it:
  every experiment with hypothesis, config hash, verdict — including the
  failures. The failures are the syllabus.

## 3. The methodology rules (the actual pedagogy)

1. **Pre-register every experiment**: hypothesis, metric, threshold,
   seeds — written *before* the run. (Our HANDOVER pickup-prompt pattern.)
2. **One variable per experiment.** The acro2→3→4→4.1→4.2 chain
   worked because each step changed one thing against a measured failure.
3. **Three seeds minimum for any learned-policy claim.** Receipts: v5's
   "costs clean state" inverted by seed luck; the flip-discovery lottery
   (4/4, 3/4, 0/4 on identical recipes) invisible at one seed.
4. **Measure the bottleneck before optimizing.** Receipt: everyone's
   instinct was "better tracking"; the data said the *plan* was slow and
   the tracker was already corner-cutting past it.
5. **Feasibility first.** Never command what physics forbids (TWR 1.88,
   15 rad/s). Receipt: acro2's reference demanded 24.7 rad/s — the error
   could never reach zero and learning chased an impossible target.
6. **If learning refuses a behavior, check where the reward gradient
   lives** (state-dense terms are silent at refusal; action-dense terms
   are not). Receipt: paper-2 step 5, 0/4 → 3/4 on the refusing seed.
7. **Freeze eval; split protocol seeds** train/validate/test and never
   tune on the last set. The leaderboard's 20 draws are the test set you
   don't control — simulate that locally.
8. **Baselines before novelty.** Day-one port of the known-good stack;
   every improvement is measured against it, not against hope.
9. **Log everything**: `--reason`, git hash, config in metadata; commit
   per work unit; failures documented in dated reports. Receipt: three
   times this project caught a wrong conclusion only because the run
   metadata made the contradiction visible.
10. **Kill criteria are declared before the experiment.** Receipt: the
    "more budget will fix s0" hypothesis was budget-refuted at 15 M and we
    stopped instead of doubling down.

## 4. Compute and calendar

~8 weeks part-time. CPU-only is proven viable (1300 steps/s at 16 envs on
14 cores; two streams in parallel). Track B needs the most steps —
budget ≥ 3 × 8 M for the decision point, more for the frontier sweep.
Everything else is seconds-to-minutes per run.

## 5. What I would bet on (so students argue with a position, not a void)

Track B wins the head-to-head at equal budget, *because* the clock
includes takeoff and the randomization is wide — both favor a policy that
optimizes the whole episode over a nominal-track plan with local repair.
But Track A's plan floor is the instrument that tells you *how good* B's
racing line actually is — keep it alive as the measuring stick even after
the decision point. Write the prediction down now, check it in week 5;
being measurably wrong is the second-best outcome the course can produce.
