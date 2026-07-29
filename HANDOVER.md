# Session handover — 2026-07-29

For the next agent/session. Read this + `papers/*/README.md` first; deep
context in `reports/*.md` (chronological; p1-/p2- prefixes from 07-23 on)
and per-run `results/*/metadata.yaml` (date-time, reason, git hash).

## PICKUP PROMPT (paste this to start the next session)
> Continue the crazy_track project (two-paper plan) at
> `C:\Users\tient\Documents\GitHub\crazy_track`. Read `HANDOVER.md` first
> (environment setup, state, gotchas). Paper 1 (fig-8 benchmark) is
> results-complete; writing remains. Paper 2: the acro4.2 experiment is
> COMPLETE and flip DISCOVERY IS SOLVED (results in
> `reports/2026-07-29_p2-acro42-rate-feedforward.md`): the action-space
> rate-feedforward aux reward gives 11/12 flip completions across 3 seeds
> (s0 4/4, s1 3/4 — was the 0/4 total refuser, s2 4/4 cleanest of the
> project), zero refusals, suite near flip-free v1. The core paper-2
> result is achieved; the consolidated results table is in
> `papers/paper2-acrobatics/README.md`. FREESTYLE v1 is also COMPLETE
> (user direction 2026-07-29; report
> `reports/2026-07-29_p2-freestyle-v1.md`): gate sequences with
> lsy_drone_racing gates + traveling ballistic flips, and the acro4.2 s2
> policy tracked the demo track ZERO-SHOT (4/4 gates clean, roll -361
> deg, RMSE 0.138). Next candidates (ask the user which): (a) expand
> freestyle to a 3-seed x multi-track claim (more flips, both axes,
> cruise sweeps); (b) settle the acro4.2 blemishes (s1 roll+ dev 0.96 >
> 0.75 gate, pitch+ 314.8-deg near-miss; v-acro dent worst 0.523 vs v1
> 0.349 — report as limitation vs iterate); (c) recovery precision /
> Lighthouse-sensing flips / feasibility-projected acro-tier refs
> (paper-2 README). Keep discipline: meaningful --reason, commit+push
> per work unit, document failures in reports, 3 seeds minimum for any
> claim.

## The two papers
1. **Paper 1 — fig-8 controller benchmark: RESULTS COMPLETE** (all claims
   statistically qualified 2026-07-23). Writing remains. Index with
   claims->evidence map: `papers/paper1-benchmark/README.md`.
2. **Paper 2 — acrobatic trajectory tracking** (vertical fig-8 + acro tier
   + flips as the attitude-referenced extreme; user-clarified scope).
   Index: `papers/paper2-acrobatics/README.md`. ACTIVE.

## Environment (CRITICAL)
- Windows 11 host; all sim work in WSL2 `Ubuntu-24.04`, venv
  `~/venvs/crazy_track`. Repo from WSL:
  `/mnt/c/Users/tient/Documents/GitHub/crazy_track`.
- Run pattern: `wsl -d Ubuntu-24.04 -- bash -c "tr -d '\r' <
  /mnt/c/<script>.sh | bash"` (PowerShell quoting + CRLF both bite).
- Background training via run_in_background PowerShell wsl calls,
  `set -o pipefail`. Two parallel 16-env streams fit on 14 cores.
  RunLogger suffixes -b/-c on same-second collisions.
- Windows-side tests: `.venv-win`, `python -m pytest tests/` (16 tests).
- Laptop lid-close = Modern Standby sleep = WSL VM suspended (trainings
  pause, resume on wake). Lock screen alone is harmless.

## Paper-2 state (chronology of recipes; full tables in reports)
- **acro3** (ballistic feasible flip ref, balanced reward): validated the
  plan-then-track pivot — 7-8/12 flip completions at 15M (vs acro2.2's
  3/12), pitch asymmetry gone; BUT 1.3-2x suite regression vs flip-free
  v1, and s0 stuck in a bad optimum (budget-refuted).
- **acro4** (+ A: 6-dim maneuver-descriptor obs, 52-dim total; + D: sparse
  completion bonus): **A works — suite regression eliminated on all 3
  seeds** (matches/beats v1 everywhere). **Sparse D fails — flips 4/12,
  refusal returns** (zero gradient at 0 deg; conditioning removed the
  cross-context transfer acro3 relied on).
- **acro4.1** (D made DENSE: per-step rotation-progress reward +2.5 over a
  full rotation, nothing past 2pi, negative backwards; completion bonus
  kept; same --acro4 flag, distinguished by git hash >= 8464372): 3 seeds
  x 8M launched 2026-07-24 morning with chained train->flip->suite
  pipeline. **STATUS AT SHUTDOWN: see the results table below / check
  results dirs.** Stream J = s1; stream I = s0 then s2 (s2 was expected
  NOT to finish before shutdown -> likely needs relaunch).
- Key prior models: acro3 15M s0/s1/s2 = `2026-07-23_19-40-03` /
  `19-40-06` / `21-35-52`; acro4 sparse-D seeds = 2026-07-24 04:22 family;
  flip-free datt_acro v1 = `2026-07-22_18-58-56` (suite reference:
  h 0.123/0.322, v 0.122/0.196/0.349).

## acro4.1 results (COMPLETE — see report 2026-07-24)
Models: s0 `2026-07-24_08-38-52`, s1 `08-38-56`, s2 `10-39-38`.
s0 4/4, s1 **0/4 total refusal** (±2°), s2 3/4; suite near v1 with mild
dents on flip-competent seeds. Verdict: discovery is a stochastic
exploration event and was the only remaining problem — post-discovery
shaping produces clean flips.

## acro4.2 results (COMPLETE — DISCOVERY SOLVED; report 2026-07-29)
Rate-feedforward aux reward `+0.5*exp(-|w_cmd - w_ref|/5)` per step in
the rotation window (w_cmd = commanded body rate about the maneuver axis,
w_ref = analytic trapezoid of the ballistic ref). Dense in ACTION space
-> gradient exists at refusal. Same `--acro4` flag, git hash >= `ffd9e91`.
Models: s0 `2026-07-29_16-24-22-b`, s1 `16-24-22`, s2 `18-18-41`.
- **11/12 completions, zero refusals: s0 4/4 (dev 0.27-0.69), s1 3/4
  (was 0/4! roll+ dev 0.96 is the one gate breach; pitch+ 314.8° misses
  completion by 0.2°), s2 4/4 (dev 0.20-0.36, cleanest of the project).**
- Recovery err <= 0.06 everywhere (gate 0.15); min_z >= 1.65, no floor.
- Suite: fast/normal tiers match/beat v1 on all seeds; v-acro dent on
  flip-competent seeds persists (0.36-0.52 vs v1 0.349), worst s2 0.523.
- **Core paper-2 result achieved.** Open blemishes (user decision:
  report-as-limitation vs iterate): s1 roll+ precision; v-acro dent.
- Pipeline script now persisted: `scripts/acro42_pipeline.sh <seeds...>`
  (chained train -> flip_eval -> suite-h -> suite-v per seed).

## Freestyle v1 (COMPLETE — report 2026-07-29_p2-freestyle-v1)
`trajectories/freestyle.py`: RaceGate (lsy_drone_racing geometry, 0.4 m
opening / 0.72 m frame, tracks port verbatim — same drone+sim), quintic
connects, TRAVELING ballistic flip (primitive + constant horizontal
drift, feasibility exact), via/hover ops, multi-window
maneuver_descriptor (DATTAcroController prefers it), analytic
feasibility_report incl. gate-plane crossing discipline. Eval:
`python -m crazy_track.eval.freestyle_eval [--model ...] --reason ...`.
**Zero-shot: acro4.2 s2 flew the level-2 demo track 4/4 gates clean +
roll −361°, RMSE 0.138** (run `2026-07-29_22-29-12`). Planning lessons:
route U-turns wide of frames (via op); flip drift must not overshoot the
next gate plane (first attempt flew over gate 3 — documented).

## How to run (WSL venv, repo root)
- Train acro4.1 seed N (8M):
  `python -m crazy_track.training.ppo_train --timesteps 8000000 --acro4
   --seed N --reason "..."`
- Flip eval: `python -m crazy_track.eval.flip_eval --model
  results/<run>/datt_ppo_final.zip --ballistic --reason "..."`
- Suite: `python -m crazy_track.eval.lissajous_benchmark --controllers
  datt_acro:results/<run>/datt_ppo_final.zip --speeds fast acro --tag
  acro41-suite-h-sN --reason "..."` and `--speeds normal fast acro
  --vertical --tag acro41-suite-v-sN`.
- Multi-seed stats: `aggregate_seeds --prefix ms-` (eval seeds) /
  `--prefix mst-` (training seeds).
- ALWAYS meaningful `--reason`; commit results + reports and push after
  each work unit.

## Paper-2 next steps (post-acro4.2: core result achieved)
- Consolidate the paper-2 results table: acro2.2 3/12 -> acro3 7-8/12
  (suite regressed) -> acro4 4/12 (sparse D) -> acro4.1 7/12 (one
  refuser) -> acro4.2 11/12 (no refusal, suite held). All numbers in
  reports/.
- Then: recovery precision, optional Lighthouse-sensing flips, and the
  feasibility-projected acro-tier reference design question (paper-2
  README). DAgger escalation path no longer needed for flips.
- ZJU planners (user ref): method citations only; MINCO-style optimizer
  becomes relevant only for chained freestyle sequences (see report
  2026-07-23 + chat analysis: flat-output singularity at zero-thrust core;
  TWR 1.88 excludes constant-speed loops, pull-out needs ~2.2+).

## Known gotchas (do not rediscover)
1. Controller sim modes cannot mix in one benchmark run (attitude /
   force_torque / rotor_vel). DATT model version auto-detected from obs
   dim (43/46/52/56/185); 52 = acro4 descriptor obs.
2. SB3 resume (`--resume-from`): `--timesteps` is ADDITIVE, not cumulative.
3. Benchmark refs start at nonzero velocity: launch transients pollute
   RMSE past the 1s warmup for noise-sensitive optimizers — check max-err
   TIMING before blaming steady-state noise (offset-free MPC lesson).
4. Flip reward shaping: sparse terminal bonuses have no gradient at
   refusal, and dense STATE-space progress terms still stall there (the
   state never moves if the policy never commands rotation — acro4.1 s1).
   ACTION-space terms (reward the commanded rate matching the reference
   profile) are the reliable discovery mechanism (acro4.2). The
   post-window level bonus creates a 720-deg attractor after
   over-rotation — the completion bonus counteracts it.
5. Single-seed conclusions on ANYTHING policy-level are worthless in this
   project (measured repeatedly). 3 seeds minimum.
6. Lighthouse gyro bypasses the latency buffer (onboard IMU) — sensors.py.
7. acro2's level-attitude bonus leaked into aggressive tracking episodes;
   acro4+ scopes attitude terms via the per-env flip mask. Do not revert.

## Paper-1 leftovers (low priority)
- Optional realism: drag model, battery sag, motor asymmetry; xadapt
  norm_RMS.npz warning. Only if reviewers ask.
- MPC launch-transient remedies (state pre-filter / reference ramp-in /
  hover-spinup protocol change) — documented, deliberate decision needed.
