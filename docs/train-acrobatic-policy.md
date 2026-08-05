# Training an acrobatic quadrotor policy — replication guide

**Target result:** one CTBR policy that flips a Crazyflie 2.1 brushless
(cf21B_500) about roll± and pitch±, tracks the ordinary fig-8 benchmark
without regression, and composes into freestyle gate sequences zero-shot.
**Measured outcome of this recipe (acro4.2, 3 seeds × 8 M steps):** 11/12
flip completions, zero refusals, suite tracking at flip-free baseline level.

**Who this is for:** students replicating the paper-2 result. It is written
so you can (a) get the result with two commands, and (b) understand *why*
every ingredient is there — including by reproducing the failures yourself,
which is the part that actually teaches.

**Budget:** ~30 min setup, ~1.7 h per training seed (16 envs, ~1300 steps/s
on CPU). Two seeds run in parallel on 14 cores → 3 seeds in ~3.5 h. All
evaluation is seconds.

---

## Part 0 — Setup

The simulator (crazyflow/MuJoCo-MJX) is Linux-first. On Windows use WSL2.

```bash
git clone https://github.com/t-thanh/crazy_track && cd crazy_track && ./scripts/setup_env.sh
```

Then, in every new shell:

```bash
source ~/venvs/crazy_track/bin/activate
```

Sanity check before you burn 5 hours of compute:

```bash
python -m pytest tests/ -q
```

The venv must live in the WSL filesystem (`~/venvs/...`), **not** under
`/mnt/c` — Windows-mounted paths are slow and break editable installs
without the `metadata` automount option.

---

## Part 1 — The short path

Train + evaluate all three seeds with the chained pipeline:

```bash
bash scripts/acro42_pipeline.sh 0 1 2
```

That runs, per seed: 8 M-step training → flip evaluation (4 variants) →
horizontal suite → vertical suite. If you have ≥14 cores, split it into two
shells (`... 0 2` and `... 1`) to halve wall-clock.

The single training command it wraps, if you want to drive it yourself:

```bash
python -m crazy_track.training.ppo_train --timesteps 8000000 --acro4 --seed 0 --reason "replication: acro4.2 recipe, seed 0"
```

`--reason` is mandatory by design: every run directory records the reason,
the git commit, and the full config in `metadata.yaml`. You will thank
yourself in three weeks.

**Read Part 2 before you interpret the numbers.** The recipe is five
decisions stacked on top of each other, and each one exists because a
simpler version measurably failed.

---

## Part 2 — The five design steps, and the real reason each works

The flags are cumulative: `--acro2` ⊂ `--acro3` ⊂ `--acro4`. Stages 4 and 5
share the `--acro4` flag and are distinguished by git commit (acro4.1 ≥
`8464372`, acro4.2 ≥ `ffd9e91`). You can therefore reproduce every failure
below with the current code plus, where noted, `git checkout`.

### Step 1 — Command body rates, not attitude

**Change.** Action = `[collective thrust, ω_x, ω_y, ω_z]` (CTBR) through the
`force_torque` sim interface, instead of `[roll, pitch, yaw, thrust]` through
the firmware attitude loop. See `_denorm_action` in
[`datt_env.py`](../src/crazy_track/envs/datt_env.py).

**Why you'd think of it.** Racing and acrobatic stacks in the literature all
use body rates; the attitude loop is an extra low-pass between you and the
motors.

**The real reason it works.** A 360° flip *passes through inverted*. An
attitude command is a target orientation, and the roll/pitch parameterisation
is singular at ±90° — you cannot express "keep rotating past vertical" as a
sequence of attitude setpoints without the representation folding over. A
rate command expresses it directly and has no singularity. This is also why
the project's Euler-based MPC (`so_rpy`) is structurally excluded from
acrobatics: not a tuning problem, a coordinate problem.

**Cost to know about.** TWR is 1.88, so thrust saturates fast; and the CTBR
interface is why acro runs cannot be mixed with attitude-mode controllers in
one benchmark process (see Pitfalls).

### Step 2 — Give the policy a *dynamically feasible* reference

**Change.** Replace the hover-pinned flip reference with
`BallisticFlipTrajectory` ([`flip.py`](../src/crazy_track/trajectories/flip.py)):
**boost** (level attitude, accel +A) → **ballistic arc** (zero thrust, rotate
here) → **brake** (level, accel +A), closed-form symmetric so it lands back
at the hover point with zero velocity.

**The failure it fixes.** `--acro2` pins the *position* reference at the
hover point while the *attitude* reference sweeps 0→2π. Measured: policies
learn 0° "flips" — hovering is reward-optimal. Forcing the issue by making
the attitude term dominate (weight 2.0 vs 0.25) gives 2/4 variants, floor
strikes, and a level-attitude bonus that leaks into non-flip episodes and
penalises the banking aggressive tracking needs. A 3-seed test settled it:
**3/12 (seed, variant) cells** — a per-seed lottery.

**The real reason the fix works.** During a flip the drone *must* leave the
hover point: while inverted, thrust points down, so gravity is unopposed.
The hover-pinned reference therefore asks for two things that cannot both be
true, and the optimiser resolves the contradiction by refusing to rotate —
correctly, given what you asked for. In the ballistic design the rotation
happens in the **zero-thrust arc, where attitude is unconstrained by the
translational dynamics**: in freefall *any* orientation is consistent with
the position reference. Position and attitude become simultaneously
satisfiable, so equal reward weights suffice and the domination hack retires.

A second, quieter fix in the same step: the reference **rate profile** must
be flyable. acro2's cosine sweep demanded 24.7 rad/s against a 15 rad/s
limit — physically impossible, so the tracking error could never go to zero.
The ballistic version uses a trapezoid with peak `2π/(0.8·Tb)` ≈ 11.2 rad/s
at `Tb=0.7`, i.e. 0.75 × `RATE_MAX`.

**Evidence.** 7–8/12 completions vs 3/12; the pitch/roll asymmetry disappears.

**Residual problem it creates.** Suite tracking regresses 1.3–2×. One policy
is now splitting capacity between two jobs.

### Step 3 — Make the task identity observable (maneuver conditioning)

**Change.** Append 6 observation dimensions (46 → 52): signed flip-axis
vector (3), countdown to the rotation window (1), progress through it (1),
active flag (1) — all **zero outside flip episodes**. See
`_maneuver_descriptor` in `datt_env.py`.

**The real reason it works.** Without the descriptor, a flip episode and an
aggressive tracking episode can look *identical* in the observation at the
moment before the maneuver. A deterministic policy facing two different
optimal actions for the same input can only hedge — blending flip-ish and
track-ish behaviour everywhere. That hedge **is** the 1.3–2× regression. The
descriptor makes the two contexts distinguishable, so the network can gate
two clean behaviours instead of averaging them. This is textbook multi-task
interference, and the fix is the textbook one: condition on the task.

**Evidence.** Suite restored to the flip-free baseline on all 3 seeds.

**Residual problem it creates — and it is subtle.** Conditioning also removes
the *accidental* cross-context transfer acro3 was leaning on. Previously,
rotation behaviour learned in flip episodes bled into tracking and back
again; once the contexts are cleanly separated, the flip behaviour has to be
discovered on its own. Paired with a **sparse** completion bonus, flips
collapsed to **4/12**. Fixing the suite exposed a discovery problem.

### Step 4 — Pay for rotation continuously, not at the finish line

**Change.** Dense rotation-progress reward: `+2.5` accumulated over a full
rotation, credited per radian *toward* the target, nothing past 2π, negative
for backwards. Keep the one-time completion bonus on top.

**The real reason sparse fails.** A bonus that pays only at 2π has **zero
gradient at 0°**. A policy that never rotates receives no signal that
rotation is worth anything — the reward landscape is flat exactly where the
policy is sitting.

**Why the completion bonus stays.** Over-rotation has its own attractor: past
2π, the level-attitude recovery bonus pulls toward the *nearest* level
orientation, which is 4π (720°). The completion bonus re-sharpens the optimum
at exactly one turn.

**Evidence.** Clean, precise flips **when discovered**: s0 4/4, s2 3/4 —
and **s1 0/4, total refusal (±2° for 8 M steps)**.

### Step 5 — The discovery fix: reward the *commanded* rate ★

This is the step that turns a lottery into a recipe, and it is the one
genuinely transferable idea in the whole progression.

**Change.** Inside the rotation window only, add

```
+0.5 · exp( −|ω_cmd − ω_ref| / 5 )
```

where `ω_cmd` is the **commanded** body rate about the maneuver axis (the
policy's own action, clipped × `RATE_MAX`) and `ω_ref` is the analytic
trapezoid rate profile of the reference. ~20 lines at the end of the `acro4`
branch of `step()` in `datt_env.py`.

**The real reason Step 4 still failed on some seeds.** The progress reward is
dense in **state** space — it reads the measured body rate ω. If the policy
never *commands* a large rate, the body never rotates, so ω ≈ 0, so the
progress term is identically zero **and so is its gradient with respect to
the policy parameters**. Refusal is a self-consistent local optimum with no
escape gradient. Whether a given seed escapes depends on whether exploration
noise happens to produce a *sustained* rotation command by luck. That is
precisely what a 4/4 · 3/4 · 0/4 spread across identical recipes looks like.

**The real reason the fix works.** The new term is dense in **action**
space — where a Gaussian policy explores *every single step, unconditionally*.
At total refusal (`ω_cmd = 0`) the term is not zero, it is
`0.5·exp(−11.2/5) ≈ 0.053`, and its gradient points unambiguously toward
larger rotation commands. The policy is paid for *intending* to rotate before
it can be paid for *having* rotated. State never has to move first.

**Why it does not corrupt the flips it enables.** It is small (+0.5 peak
against ~2.0 of tracking terms in-window), it is scoped to the rotation
window, and it rewards the *reference-consistent* rate — so at convergence it
points the same way as the tracking objective rather than competing with it.
No annealing needed.

**Evidence.** **11/12 completions, zero refusals** (s0 4/4, s1 3/4 — the
former refuser, s2 4/4), suite held at baseline.

> **The lesson to take away, stated generally:** when a policy refuses a
> behaviour entirely, ask whether your shaping reward is dense in *state* or
> in *action* space. State-dense rewards are silent exactly at refusal,
> because the state never moves. Action-dense rewards still have a gradient,
> because exploration lives in action space. If you have an analytic
> reference for what the action *should* be, feeding it in as a small
> auxiliary term is often the whole fix.

---

## Part 3 — Verification protocol (do not skip)

**Three seeds minimum for any claim.** This is not ceremony: in this project
single-seed policy conclusions have been measured wrong repeatedly, in both
directions. Steps 4 and 5 are *only distinguishable* at 3 seeds — at seed 0
alone they look identical.

Flip evaluation — 4 variants (roll±, pitch±) on the ballistic reference:

```bash
python -m crazy_track.eval.flip_eval --model results/<run>/datt_ppo_final.zip --ballistic --reason "..."
```

Tracking suite — confirms flips did not cost ordinary tracking:

```bash
python -m crazy_track.eval.lissajous_benchmark --controllers datt_acro:results/<run>/datt_ppo_final.zip --speeds fast acro --tag acro-suite-h --reason "..."
```

Multi-seed aggregation:

```bash
python -m crazy_track.eval.aggregate_seeds --prefix mst-
```

**Acceptance gates.**

| gate | threshold | reference result |
|---|---|---|
| flip completions | ≥ 3/4 on **every** seed | 4/4, 3/4, 4/4 |
| rotation | \|total − 360°\| < 45° | 333–362° |
| max deviation from reference | < 0.75 m | 0.20–0.69 m (one outlier 0.96) |
| recovery error | < 0.15 m | ≤ 0.06 m |
| floor clearance | min z > 0.15 m | ≥ 1.65 m |
| suite regression | near flip-free baseline | h-fast 0.125–0.131 vs 0.123 |

Reference baseline for the suite column: flip-free `datt_acro` v1,
`results/2026-07-22_18-58-56_datt-train`.

---

## Part 4 — Which checkpoint is "the best model"?

For **acrobatics**, rank by flip quality: seed 2 of the reference run
(`results/2026-07-29_18-18-41_datt-train`) — 4/4 flips at the cleanest
deviations (0.20–0.36 m) and the only seed to complete both flips of the
two-flip freestyle track.

**But do not assume that checkpoint is your deployment model.** Two
independent probes found the same inversion: the *best acrobatic* seed is the
*worst* on disturbance-rejection cells (Lighthouse+wind 0.118 vs seed 0's
0.079; payload 0.155 vs 0.073) and it clips a gate at every speed in the
racing test, where the weaker flipper posts the fastest lap. Maneuver
precision and disturbance robustness appear to trade against each other
across seeds. **Select your checkpoint against the job you actually have,
and report which one you used.**

---

## Part 5 — Exercises (this is where the learning is)

1. **Reproduce the infeasible-reference failure.** Train `--acro2 --seed 0`
   for 2 M steps, run `flip_eval` *without* `--ballistic`. Expect near-0°
   rotations. Explain, in terms of the reward, why hovering wins.
2. **Reproduce the multi-task regression.** Train `--acro3` for 8 M, run the
   suite, compare to the flip-free baseline. Where does the capacity go?
3. **Reproduce the discovery lottery.** Check out `8464372` (acro4.1) and
   train seeds 0, 1, 2. You should see a wide spread. Then return to `main`
   and repeat. This is the whole thesis of the recipe in one experiment.
4. **Ablate Step 5 directly.** On `main`, comment out the rate-feedforward
   block and retrain the seed that refused. Predict the outcome first.
5. **Measure the gradient claim.** Log `ω_cmd` during a refusing run.
   Confirm the progress term is identically zero while the feedforward term
   is not — the argument in Step 5 made empirical.

---

## Pitfalls (already paid for — do not rediscover)

1. **Controller sim modes cannot be mixed in one benchmark process** —
   `attitude` / `force_torque` / `rotor_vel`. Acro policies need
   `force_torque`; invoke them in separate runs.
2. **DATT model version is auto-detected from observation width** (43/46/52/
   56/185). 52 = the acro4 descriptor observation. If you change the obs
   layout, update `datt_acro.py` too.
3. **`--resume-from` makes `--timesteps` additive, not cumulative** (SB3
   `reset_num_timesteps=False`).
4. **Sparse terminal bonuses have no gradient at refusal**, and state-dense
   ones stall there too — see Step 5.
5. **Single-seed conclusions on anything policy-level are worthless here.**
   Measured repeatedly. Three seeds.
6. **Laptop lid-close suspends the WSL VM**, pausing training (it resumes on
   wake). Locking the screen alone is harmless.
7. **Known wart:** the action-magnitude penalty
   `0.02·‖action[:, 0:2]‖` was written for the attitude action layout, where
   columns 0:2 are roll and pitch. In CTBR mode those columns are *thrust*
   and *roll rate*. It is small and every reported result includes it, so it
   is left as-is for comparability — but it is not principled, and it is a
   reasonable thing for a student to fix and re-measure.

---

## Provenance

Full experimental record, including the failed recipes with their numbers:
`reports/2026-07-24_p2-acro4-maneuver-conditioning.md` (steps 3–4),
`reports/2026-07-29_p2-acro42-rate-feedforward.md` (step 5),
`reports/2026-07-29_p2-freestyle-v1.md` (composition + racing),
`reports/2026-08-05_p1x-acro-crossover.md` (the robustness anti-correlation).
Index: `papers/paper2-acrobatics/README.md`.
