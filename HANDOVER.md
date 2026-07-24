# Session handover — 2026-07-24

For the next agent/session. Read this + `papers/*/README.md` first; deep
context in `reports/*.md` (chronological; p1-/p2- prefixes from 07-23 on)
and per-run `results/*/metadata.yaml` (date-time, reason, git hash).

## PICKUP PROMPT (paste this to start the next session)
> Continue the crazy_track project (two-paper plan) at
> `C:\Users\tient\Documents\GitHub\crazy_track`. Read `HANDOVER.md` first —
> it has environment setup, current state, and the acro4.1 status. Paper 1
> (fig-8 benchmark) is results-complete; current work is paper 2 (acrobatic
> trajectory tracking): the acro4.1 recipe (maneuver-conditioned obs +
> DENSE rotation-progress reward + completion bonus) was training 3 seeds
> at session end. Check `results/*_datt-train` metadata (acro4: true, git
> hash 8464372+) for which seeds finished; relaunch any missing seeds
> (command in HANDOVER "How to run"), run `flip_eval --ballistic` + the
> acro-suite benchmarks for each, then write the acro4.1 verdict vs the
> acro4 table in `reports/2026-07-24_p2-acro4-maneuver-conditioning.md`.
> Success bar: >= 3/4 flip completions per seed at dev<0.75/rec<0.15 AND
> suite still at flip-free-v1 level. Keep the discipline: meaningful
> --reason on every run, commit+push each work unit, document failures.

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

## acro4.1 results at session end (fill state: see below)
- s0: PENDING at write time — check `results/2026-07-24_*_datt-train`
- s1: PENDING at write time
- s2: PENDING (expected killed by shutdown — relaunch)
(If a seed finished, its flip-eval + acro41-suite-h/v-sN runs exist too;
the chained scripts create them automatically.)

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

## Paper-2 next steps after acro4.1 verdict
- If flips >= 3/4 per seed with suite held: core result achieved ->
  consolidate paper-2 results table; then recovery precision (<0.3 m
  already near on good seeds), optional Lighthouse-sensing flips, and the
  feasibility-projected acro-tier reference design question (see paper-2
  README).
- If flips still weak: escalation path is DAgger from a quaternion CTBR-MPC
  expert (DDA recipe; so_rpy Euler MPC cannot serve — singular at +-90 deg).
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
   refusal; dense progress terms are the discovery mechanism. The
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
