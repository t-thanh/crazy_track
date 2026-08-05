# Crossover test: the paper-2 acrobatic controller on the paper-1 benchmark

**Date:** 2026-08-05 · **Status: COMPLETE** · **ADDITIVE — changes nothing in paper 1**

> This is an *additional* experiment requested after paper 1's results were
> frozen. It adds no row to any paper-1 table, figure, or claim. Every run
> here carries the tag prefix `p1x-`, which is disjoint from the `ms-` /
> `mst-` prefixes the paper-1 reproduction path aggregates — verified after
> the runs: `aggregate_seeds --prefix ms-` and `--prefix mst-` return zero
> `p1x` rows and the same 58 `ms-` rows as before. Paper-1 numbers,
> `publication1/`, and `scripts/make_paper1_figures.py` were not touched.

## Question

Paper 1 benchmarks six controller stacks on the horizontal Lissajous fig-8
under disturbances and Lighthouse sensing. Paper 2 built a CTBR acrobatic
policy for a different job (flips, acro-tier references, freestyle gate
sequences). **How does the acrobatic controller do on the benchmark it was
never tuned for — and what does flip capability cost, or buy, on ordinary
tracking?**

## Which model is "the best acrobatic model"

acro4.2 (report 2026-07-29), the recipe that solved flip discovery: 11/12
flip completions over 3 seeds with zero refusals. Per-seed maneuver quality
ranks **s2 > s0 > s1** (s2: 4/4 flips at the project's cleanest deviations
0.20–0.36 m, the only seed to complete both flips of the two-flip freestyle
track). So **s2 is the best acrobatic model**; all three seeds are run here
because a single-seed policy claim is worthless in this project (gotcha 5).

The flip-free CTBR predecessor **datt_acro v1** (`2026-07-22_18-58-56`) is
included as a context row — same action space, same benchmark, no flip
capability — which turns the comparison into a controlled test of what the
acro4.2 training recipe does to plain tracking. v1 is a single model, so its
rows are single runs, reported as context (the same status plain MPC has in
paper 1).

## Protocol

Copied cell-for-cell from the paper-1 runs (configs read from
`results/*_mst-v5-*/metadata.yaml`, `*_ms-adrc-lhwind-*`, `*_p1-xadrc-*`):
nominal `slow normal fast`; lighthouse `normal fast`; LH+wind `normal` +
`wind_const` + lighthouse; each disturbance at `normal`. Same sim ground
truth (cf21B_500, first-principles, 500 Hz firmware loop), same trajectory,
same metric (RMSE 3D, 1 s warmup excluded), same 100 Hz control rate, eval
seed 0 fixed, learned policies reported over 3 training seeds.
Runner: `scripts/p1_acro_crossover.sh`.

**One protocol difference, unavoidable and load-bearing:** the acro policy
commands body rates through the `force_torque` sim interface, while paper 1's
pool commands attitude (gotcha 1 — the modes cannot be mixed in one run, so
these are separate runs). The comparison is therefore *stack vs stack*
(controller + interface), not controller-in-isolation. This favours the acro
policy at high speed, where attitude-interface stacks are rate-limited by the
firmware loop, and is part of why it is interesting.

## Results

RMSE 3D (m), mean±std over 3 training seeds. DATT v5 is paper 1's learned
deployment policy, recomputed live from the same aggregator for an
apples-to-apples learned-vs-learned comparison.

| cell | **acro4.2** (3 seeds) | DATT v5 (3 seeds) | v1 flip-free (1 run) | paper-1 leader |
|---|---|---|---|---|
| nominal slow | 0.057±0.008 | 0.038±0.014 | 0.058 | offset-free MPC 0.004 |
| nominal normal | 0.085±0.006 | 0.075±0.010 | 0.083 | ADRC+xadapt (see Table 2) |
| **nominal fast** | **0.128±0.002** | 0.157±0.007 | 0.123 | offset-free MPC 0.052 |
| lighthouse normal | 0.104±0.003 | 0.056±0.005 | 0.103 | — |
| lighthouse fast | 0.151±0.016 | 0.120±0.011 | 0.146 | DATT v5 0.120 |
| **LH+wind (deployment)** | 0.095±0.017 | 0.059±0.002 | 0.121 | four-way tie ≈0.057–0.063 |
| wind_const | 0.084±0.013 | 0.073±0.007 | 0.105 | ADRC 0.025 |
| wind_gust | 0.124±0.007 | 0.087±0.005 | 0.130 | hybrid adaptive 0.054 |
| payload | 0.101±0.038 | 0.093±0.006 | **0.968** | ADRC+xadapt 0.018 |
| ground effect | 0.086±0.006 | 0.074±0.011 | 0.081 | PID 0.023 |

Per-seed, for the anti-correlation noted below:

| seed | nom slow/normal/fast | lh n/f | LH+wind | wind | gust | payload | ground |
|---|---|---|---|---|---|---|---|
| s0 | 0.056 / 0.080 / 0.128 | 0.099 / 0.142 | **0.079** | 0.080 | 0.123 | **0.073** | 0.081 |
| s1 | 0.068 / 0.094 / 0.131 | 0.105 / 0.137 | 0.089 | **0.072** | **0.116** | 0.074 | 0.094 |
| s2 | **0.047** / 0.081 / **0.125** | 0.108 / 0.173 | 0.118 | 0.101 | 0.132 | 0.155 | 0.082 |

## Findings

**1. The acrobatic policy beats paper 1's deployment policy at the fastest
fig-8 tier — 0.128±0.002 vs v5's 0.157±0.007, non-overlapping ranges**
(0.125–0.131 vs 0.148–0.163). It is the only cell the acro stack wins against
v5, and it is the cell its training targets: aggressive references plus a
body-rate interface. This is the crossover's one genuinely new *positive*
result, and it is statistically qualified at 3 training seeds.

**2. Everywhere else it is mid-pack, and on clean precision it is far
behind.** Nominal slow 0.057 vs offset-free MPC's 0.004 is a 14× gap. That is
the expected shape of the trade: the acro policy is trained on aggressive
references with sensor noise and a maneuver head, not on hitting a gentle
fig-8 to the millimetre. In the deployment cell (LH+wind) it lands at
0.095±0.017 — behind the four-way ≈0.06 tie and behind DATT v4 (0.077±0.006),
but well ahead of plain MPC (0.199±0.017). It would not change paper 1's
ranking if it were added, which is one reason it does not belong there.

**3. The acro4.2 recipe fixed a catastrophic failure mode of the flip-free
predecessor.** Under a 10 g payload (23 % of the airframe weight) the v1 CTBR
policy **collapses: RMSE 0.968 m, ground contact (min z = −0.001 m), mean
altitude error −0.20 m, error dominated by xy (0.89) once it is scraping the
floor**. All three acro4.2 seeds hold altitude in the same cell (s0: min z
0.879 m, mean altitude error −0.013 m). Mechanistic reading, offered as a
hypothesis rather than a demonstrated cause: the payload's 2.26 m/s² downward
bias exceeds the ±1.75 m/s² vertical perturbation range both policies trained
on, but acro4.2 additionally saw ballistic boost/freefall phases spanning
+7.5 to −9.81 m/s², so its thrust envelope extrapolates where v1's does not.
Testing that properly would need an ablation (acro4.2 recipe minus flips);
it is not claimed here.

**4. Acrobatic quality and disturbance-robust tracking are anti-correlated
across seeds.** s2 — the best acrobatic seed — is the best on clean nominal
(0.047 slow, 0.125 fast) and the *worst* on every noisy cell (LH+wind 0.118,
payload 0.155, lighthouse fast 0.173). s0, the weaker flipper, is the most
robust (LH+wind 0.079, payload 0.073). The same inversion appeared
independently in the paper-2 racing test (s0 posted the fastest lap, s2
clipped a gate at every speed). Two unrelated probes, same ordering: the
capacity a seed spends on maneuver precision appears to come out of
disturbance rejection. This is the most interesting finding for paper 2, and
it argues that "best acrobatic model" and "best deployment model" should not
be assumed to be the same checkpoint.

## Caveats

- Different control interface (force_torque vs attitude) — stack-level
  comparison, see Protocol. The high-speed win is partly an interface result.
- 3 training seeds at fixed eval seed 0; the noisy cells therefore carry
  training-seed variance, not eval-seed variance (paper 1's convention for
  learned policies).
- v1 rows and the paper-1 leader column are single runs / previously
  published aggregates respectively; the payload contrast rests on one v1 run
  — deterministic and reproducible (clean sensing, constant force), but one
  model, not a seed distribution.
- The classical-stack column is quoted from paper 1's frozen tables for
  orientation only. Note that the ADRC+xadapt nominal row was re-measured on
  2026-08-04 (report `2026-08-04_p1-round2.md`); consult the manuscript, not
  this report, for the authoritative classical numbers.

## What this does not change

Nothing in paper 1. No table, figure, claim, or manuscript file was edited;
no paper-1 run directory was read-modified; the `ms-`/`mst-` aggregates are
byte-identical. If the crossover is ever wanted in print, it belongs in
paper 2 as a "does the acro controller regress ordinary tracking" section,
where findings 3 and 4 are the substance.

## Runs

`results/2026-08-05_07-4*_p1x-acro42-{nom,lh,lhwind,wind,gust,payload,ground}-s{0,1,2}`
and `results/2026-08-05_07-*_p1x-acrov1-*-s0` (28 runs).
Note for anyone reconciling dates: the WSL clock lagged earlier in this
session, so the acro4.2 / freestyle runs these rows compare against carry
`2026-07-29` stamps despite being same-week work.
Reproduce: `bash scripts/p1_acro_crossover.sh`, then
`python -m crazy_track.eval.aggregate_seeds --prefix p1x-`.
