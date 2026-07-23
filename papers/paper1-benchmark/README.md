# Paper 1 — Trajectory-controller benchmark on the Crazyflie 2.1 brushless

Fig-5/Table-III-style Lissajous benchmark (arXiv:2311.13081) on crazyflow,
extended with disturbances, a Lighthouse LH2 sensor model (arXiv:2104.11523),
and multi-seed statistics. **Status: results complete and statistically
qualified (2026-07-23); writing remains.**

## Scope
- 8 controller stacks: PID(+ff), ADRC (velocity-ESO, w=7), MPPI+L1 (tuned),
  MPC, offset-free MPC (+soft-start ESO), PID+xadapt, ADRC+xadapt,
  DATT v2-v6a (learned; v3 = clean-sensing pick, v5 = deployment pick).
  (datt_acro appears only as a pool member on the acro tier; the acrobatic
  controller itself is paper 2.)
- Conditions: 3 speeds (+acro tier), wind_const / wind_gust / ground /
  payload, Lighthouse sensing, and combinations.
- Statistics: 10 eval seeds for the noisy cells; 3 training seeds for
  policy-level claims (eval seed fixed to isolate training variance).

## Headline claims (each with its evidence trail)

| claim | evidence | source runs |
|---|---|---|
| Deployment cell (LH+wind) is a 3-way tie ~0.06: offset-free MPC 0.057±0.014, DATT v5 0.059±0.002, ADRC+xadapt 0.060±0.009 | 10 eval seeds / 3 training seeds / 10 eval seeds | `ms-mpcof-lhwind-s*`, `mst-v5-lhwind-s*`, `ms-lhwind-xa-s*` |
| Offset-free MPC nominal records 0.004/0.036/0.052; its "noise fragility" was a launch-transient artifact (steady-state 0.046±0.008), fixed by ESO soft-start | 10-seed sweeps + time-series root-cause + discriminating test vs plain MPC | `mpcof-softstart-*`, `ms-mpcofss-lh-s*`, `mpc-plain-lh-s{4,8}` |
| v5 dominates or ties v4 in all 8 cells at 3 training seeds; the "v5 costs clean state" single-seed reading was inverted by seed luck | 3 training seeds x 4 conditions, eval seed 0 | `mst-v{4,5}-*-s{0,1,2}` |
| DATT v3 is pool-best under gusts (0.061±0.002); its LH-fast failure is a variance phenomenon (0.323±0.106) | 10 eval seeds | `ms-gust-s*`, `ms-lh-s*` |
| Tuned MPPI's fast-nominal crown (0.068) does not survive Lighthouse (0.228±0.178, range 0.091-0.480) | 3 eval seeds (refresh) | `ms-lhfix-s*` |
| ADRC's noise-vs-gust bandwidth dilemma is fundamental (no fixed w wins both; adaptive-w false-positives on its own attitude-lag residual) | bandwidth study + documented negative result | report 2026-07-22, `adrc_adaptive` runs |
| ESO-family launch transients on noisy state are generic (benchmark refs start at nonzero velocity) | matched-seed plain-MPC test | `mpc-plain-lh-s{4,8}` |

## Key tables
- Nominal 3-speed table: `README.md` (repo root, current results section).
- Deployment/disturbance/Lighthouse matrices + ranking and failure-mode
  synthesis: `reports/2026-07-23_multi-seed-training-and-lighthouse-refresh.md`
  ("Paper-1 synthesis" section — intended as the discussion skeleton).
- Full analysis trail: `reports/2026-07-22_setup-and-pid-baseline.md`,
  `reports/2026-07-22_lighthouse-sensor-mppi-tuning.md`.

## Key models (all `datt_ppo_final.zip` under `results/<run>/`)
- DATT v3: `2026-07-22_16-35-10_datt-train`
- DATT v4 s0/s1/s2: `2026-07-22_17-07-10`, `2026-07-23_06-47-56`, `2026-07-23_08-05-04`
- DATT v5 s0/s1/s2: `2026-07-22_17-32-52`, `2026-07-23_06-49-11`, `2026-07-23_07-30-13`
- v6a (negative result): `2026-07-22_18-11-05`

## Reproduction
Aggregators: `python -m crazy_track.eval.aggregate_seeds --prefix ms-` (eval
seeds) / `--prefix mst-` (training seeds). Every run dir carries
`metadata.yaml` with reason + git hash. Benchmark CLI recipes: `HANDOVER.md`.

## Remaining
- Optional realism (drag model, battery sag, motor asymmetry) — only if
  reviewers ask; documented as out of scope.
- Paper text. Report naming convention from 2026-07-23 on: `reports/*_p1-*.md`.
