# Paper 1 — Trajectory-controller benchmark on the Crazyflie 2.1 brushless

Fig-5/Table-III-style Lissajous benchmark (arXiv:2311.13081) on crazyflow,
extended with disturbances, a Lighthouse LH2 sensor model (arXiv:2104.11523),
and multi-seed statistics. **Status: results complete and statistically
qualified; manuscript drafted, all tables and five figures final as of
2026-08-04. Open: length (see the trim plan in
`reports/2026-08-04_p1-round2.md`) and the hardware campaign.**

## Scope
The manuscript reports a **six-stack pool**: PID + feedforward, ADRC
(velocity-ESO, $\omega_o=7$), MPPI + L1 (tuned), offset-free MPC (+soft-start
ESO), ADRC + xadapt learned low level, and DATT-Asym (= v5, the
privileged-critic policy). Plain MPC and DATT-L1 (= v3) appear as *context
rows* below the pool, not as pool members; PID+xadapt, DATT v2/v4/v6a and the
acro policies are part of the study's history and live in the reports, not in
the paper's tables. (The acrobatic controller is paper 2.)
- Conditions: 3 speeds, wind_const / wind_gust / ground / payload, Lighthouse
  sensing, and LH+wind as the deployment condition.
- Statistics: 10 evaluation seeds for the noisy cells; 3 training seeds for
  every learned-policy cell (evaluation seed fixed to isolate training
  variance). Classical stacks are deterministic in clean-sensing conditions
  and are reported as single runs.

## Headline claims (each with its evidence trail)

| claim | evidence | source runs |
|---|---|---|
| **Deployment cell (LH+wind) is a FOUR-way tie ~0.06**: offset-free MPC 0.057±0.014, DATT-Asym 0.059±0.002, ADRC+xadapt 0.060±0.009, ADRC 0.063±0.006. The single-seed 0.053 that once looked like a new best stack was the *minimum* of ten draws. | 10 eval seeds (3 training seeds for the policy) | `ms-mpcof-lhwind-s*`, `mst-v5-lhwind-s*`, `ms-lhwind-xa-s*`, `ms-adrc-lhwind-s*` |
| Offset-free MPC nominal records 0.004/0.036/0.052; its "noise fragility" was a launch-transient artifact (steady-state 0.046±0.008), fixed by ESO soft-start | 10-seed sweeps + time-series root-cause + discriminating test vs plain MPC | `mpcof-softstart-*`, `ms-mpcofss-lh-s*`, `mpc-plain-lh-s{4,8}` |
| v5 dominates or ties v4 in all 8 cells at 3 training seeds; the "v5 costs clean state" single-seed reading was inverted by seed luck | 3 training seeds x 4 conditions, eval seed 0 | `mst-v{4,5}-*-s{0,1,2}` |
| Gusts go to the hybrid adaptive stack (0.054); DATT-L1 is second at 0.066 (re-measured 2026-08-04, was 0.061). Its LH-fast failure is a variance phenomenon (0.323±0.106) | 10 eval seeds | `p1-xadrc-wind_gust`, `p1-dattl1-gust`, `ms-lh-s*` |
| Tuned MPPI's fast-nominal crown (0.068) does not survive Lighthouse (0.157±0.113, range 0.091-0.480, worst/best 5.3x) | 10 eval seeds | `ms-lhfix-s{0,1,2}` + `ms-mppi-lhfast-s{3..9}` |
| ADRC's noise-vs-gust bandwidth dilemma is fundamental (no fixed w wins both; adaptive-w false-positives on its own attitude-lag residual) | bandwidth study + documented negative result | report 2026-07-22, `adrc_adaptive` runs |
| ESO-family launch transients on noisy state are generic (benchmark refs start at nonzero velocity) | matched-seed plain-MPC test | `mpc-plain-lh-s{4,8}` |

## Manuscript
`publication1/` (SPIE format; `spie.cls` is gitignored — get it from the
author kit). Tables 2–4 and the five figures are final. Figures are
regenerated from the run directories by
`python scripts/make_paper1_figures.py` (read-only w.r.t. `results/`).
**Figure/table number rule:** a number printed in a figure panel equals its
table cell; where the cell is a seed aggregate the panel prints the aggregate
and the caption names the single realization that is drawn.

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
- **Length is the largest open item**: ~14–15 pages against a 10-page target.
  A costed trim plan is in `reports/2026-08-04_p1-round2.md`; the author
  chooses the cuts before any are made.
- Hardware validation campaign (Sec. 3.7 is written and pre-registered; the
  results subsection is reserved).
- Optional realism (drag model, battery sag, motor asymmetry) — only if
  reviewers ask; documented as out of scope.
- Report naming convention from 2026-07-23 on: `reports/*_p1-*.md`.
