# 2026-08-04 — Paper 1: gap-filling runs, figures, and four corrections

Part A (every `\tbd` cell) and Part B (all figures) of
`publication1/CLAUDE_CODE_REQUESTS.md`. **Result: zero red cells, five vector
figures, and four numbers in the manuscript that had to change.** All runs at
git `50b28f8`+ in the WSL venv; every run carries its `--reason`.

## Headline: the deployment tie is FOUR-way, and the single seed was the best of ten

The paper flagged plain ADRC's \SI{0.053}{\meter} at LH+wind as unreadable
under its own Lesson 3. The ten-seed re-run (`ms-adrc-lhwind-s0..s9`):

| statistic | value |
|---|---|
| mean ± sd | **0.063 ± 0.006** |
| min / max | **0.053** / 0.075 |

**The single-seed 0.053 was the minimum of the ten draws** — not merely
noisy but the most favourable sample available. Reading it would have
produced a false claim of a new best stack.

Tie band (gap between means within the larger seed spread):

| stack | LH+wind | in band? |
|---|---|---|
| Offset-free MPC | 0.057 ± 0.014 | yes (best) |
| DATT-Asym | 0.059 ± 0.002 | yes |
| ADRC + xadapt | 0.060 ± 0.009 | yes |
| **ADRC** | **0.063 ± 0.006** | **yes — new fourth member** |
| MPPI + L1 | 0.078 ± 0.014 | no (21 mm from best) |
| PID | 0.116 ± 0.013 | no |
| Plain MPC | 0.199 ± 0.017 | no |

This is the *stronger* branch the request anticipated: four unrelated
mechanisms — disturbance-augmented prediction, privileged-critic policy,
observer over an adaptive rate loop, and observer in the control law —
saturate at the same value, so the estimator-limited reading gains a fourth
independent witness. Manuscript updated throughout (`results.tex`,
`conclusion.tex`): "three-way" → "four-way", \SI{3}{\milli\meter} →
\SI{6}{\milli\meter}, and the caveat paragraph now *records* the correction
rather than promising the run.

## Corrections to numbers already in the paper

Per the instruction not to change an existing number silently:

### 1. ADRC row, ω_o = 7 (Table 2 and 3) — the row mixed two bandwidths
| cell | was (ω=10) | now (ω=7) | note |
|---|---|---|---|
| nominal slow | 0.012 | **0.005** | second-best in the pool |
| nominal fast | 0.089 | **0.098** | worse — Lesson 2's trade, measured again |
| payload | 0.036 | **0.024** | |
| ground | 0.066 | **0.024** | biggest single move in the table |

### 2. ADRC + learned low level: the row predated commit `c9ca86e`
The xadapt stack's cells were measured before the fix that replaced
differentiated-velocity `proper_acc` with commanded-thrust specific force and
decimated the outer loop to \SI{100}{\hertz}. Re-running at the current code
state moves them, so the row was refreshed for the same reason A.1 exists:

| cell | was | now |
|---|---|---|
| nominal slow / normal / fast | 0.020 / 0.018 / 0.084 | **0.010 / 0.015 / 0.124** |
| wind | 0.037 | **0.040** |
| gust | 0.063 | **0.054** |
| payload | 0.018 | **0.019** |

The fast-tier loss (0.084 → 0.124) is mechanistically consistent with the
decimation: a \SI{100}{\hertz} outer loop over a \SI{500}{\hertz} inner loop
is exposed exactly where the reference is most demanding. Lesson 7 updated:
payload is no longer *exactly* its own nominal (0.019 vs 0.015) but is within
a fifth of it, against a factor of four for the baseline — the claim survives
in weaker, accurate form, and the fast-tier cost is now stated as a second
measurable price of layering.

### 3. Ground effect is no longer "won by the baseline"
With the observer at ω=7 the ground column collapses to near-ties, and the
hybrid stack wins it:

| stack | ground |
|---|---|
| ADRC + learned low level | **0.016** |
| Offset-free MPC | 0.023 |
| PID | 0.023 |
| ADRC | 0.024 |
| MPPI + L1 | 0.032 |
| DATT-Asym | 0.089 |

The old claim ("the observers spend bandwidth chasing it") was an artifact of
the ω=10 setting, not a property of observers. Rewritten: ground effect is
the *mildest* column — the baseline needs no disturbance estimate to hold
\SI{0.023}{\meter}, and correctly-tuned observers match or beat it. Only the
learned policy, which never saw a thrust-gain disturbance in training, is
clearly worse. The recommendation row changed from PID to the hybrid stack,
with the note that the baseline is within \SI{7}{\milli\meter} at a
twentieth of the compute.

### 4. "The only stack below 1 cm anywhere" was false after the ADRC re-run
Offset-free MPC 0.004, ADRC 0.005, ADRC+xadapt 0.010 at the slow tier. The
paragraph now makes the point at the *fast* tier, where the optimizer really
is alone (0.052 vs 0.098 and 0.124).

## Part A — every cell of Tables 2–4 mapped to its run

New runs are in **bold**. Values re-measured this session that reproduce the
existing table exactly are marked ✓ (PID, MPPI and offset-free MPC nominal
all reproduced to the third decimal, which is the reproducibility check for
the whole harness).

### Table 2 — nominal
| controller | slow | normal | fast | run |
|---|---|---|---|---|
| PID | 0.012 ✓ | 0.022 ✓ | 0.088 ✓ | `2026-08-04_10-42-03_p1-fig-nominal-att` |
| ADRC | **0.005** | **0.023** | **0.098** | `2026-08-04_10-41-22_p1-adrc-w7-nominal` |
| MPPI+L1 | 0.023 ✓ | 0.035 ✓ | 0.068 ✓ | `2026-08-04_10-42-03_p1-fig-nominal-att` |
| Offset-free MPC | 0.004 ✓ | 0.036 ✓ | 0.052 ✓ | `2026-08-04_10-42-03_p1-fig-nominal-att` |
| ADRC+xadapt | **0.010** | **0.015** | **0.124** | `2026-08-04_10-45-13_p1-fig-nominal-xadapt` |
| DATT-Asym | 0.038±0.014 | 0.075±0.010 | 0.157±0.007 | `mst-v5-nom-s{0,1,2}` (3 train seeds) |

### Table 3 — force disturbances, normal tier
| controller | nominal | wind | gust | payload | ground |
|---|---|---|---|---|---|
| PID | see T2 | 0.109 `22-22-28_lissajous-wind_const` | 0.117 `22-23-11_lissajous-wind_gust` | 0.093 `22-24-05_lissajous-payload` | 0.023 `22-24-51_lissajous-ground` |
| ADRC | see T2 | 0.025 (same wind run) | 0.082 (same gust run) | **0.024** `p1-adrc-w7-payload` | **0.024** `p1-adrc-w7-ground` |
| MPPI+L1 | see T2 | **0.042** `p1-mppi-wind_const` | 0.076 (gust run) | **0.031** `p1-mppi-payload` | **0.032** `p1-mppi-ground` |
| Offset-free MPC | see T2 | 0.045 `2026-07-23_08-18-12_mpcof-softstart-wind` | **0.097** `p1-ofmpc-wind_gust` | **0.098** `p1-ofmpc-payload` | **0.023** `p1-ofmpc-ground` |
| ADRC+xadapt | see T2 | **0.040** `p1-xadrc-wind_const` | **0.054** `p1-xadrc-wind_gust` | **0.019** `p1-xadrc-payload` | **0.016** `p1-xadrc-ground` |
| DATT-Asym | see T2 | 0.073 `mst-v5-wind-s{0,1,2}` | 0.091 (v5 gust eval) | 0.102 (v5 payload eval) | **0.089** `p1-datt-asym-ground` |
| *Plain MPC* | 0.063 | 0.196 | 0.142 | 0.137 | 0.055 | (pre-existing context rows) |
| *DATT-L1* | 0.048 | 0.050 | 0.061 | 0.053 | 0.049 | (pre-existing context rows) |

### Table 4 — realistic sensing
| controller | LH slow | LH normal | LH fast | LH+wind |
|---|---|---|---|---|
| PID | 0.012 `ms-lh-s*` | 0.053±0.010 `ms-lh-s*` | 0.155±0.007 `ms-lh-s*` | **0.116±0.013** `ms-pid-lhwind-s0..9` |
| ADRC | **0.021** `p1-adrc-w7-lh` | 0.056 (LH sweep) | **0.181** `p1-adrc-w7-lh` | **0.063±0.006** `ms-adrc-lhwind-s0..9` |
| MPPI+L1 | 0.051±0.001 `ms-lhfix-s*` | 0.079±0.018 `ms-lhfix-s*` | 0.228±0.178 `ms-lhfix-s*` | **0.078±0.014** `ms-mppi_l1-lhwind-s0..9` |
| Offset-free MPC | **0.021** `p1-ofmpc-lh-slow` | 0.141±0.058 `ms-mpcofss-lh-s*` | 0.070±0.010 `ms-mpcofss-lh-s*` | 0.057±0.014 `ms-mpcof-lhwind-s*` |
| ADRC+xadapt | 0.025 | 0.046 | 0.145 | 0.060±0.009 `ms-lhwind-xa-s*` |
| DATT-Asym | 0.033±0.008 `mst-v5-lh-s*` | 0.056±0.005 | 0.120±0.011 | 0.059±0.002 `mst-v5-lhwind-s*` |
| *Plain MPC* | 0.014±0.003 | 0.122±0.021 | 0.067±0.001 | 0.199±0.017 `ms-mpcof-lhwind-s*` (mpc rows) |
| *DATT-L1* | 0.034 | 0.073 | 0.323±0.106 `ms-lh-s*` | 0.067 |

**Note on the two LH-sensing rows left un-refreshed.** The ADRC+xadapt LH row
(0.025/0.046/0.145) and the LH+wind aggregate post-date `c9ca86e` — they were
measured *by* the commit that fixed the stack — so unlike its clean-sensing
cells they are current and were not re-run.

## Part B — figures

`scripts/make_paper1_figures.py` regenerates all five as vector PDFs from the
run directories; read-only w.r.t. `results/`; re-runnable
(`--only fig3` to rebuild one). Style is shared: serif, 8 pt, \SI{17}{\cm}
maximum width, one fixed colour per controller, reference always thin dashed
black *under* the flown path, one legend per figure.

| figure | content | source runs |
|---|---|---|
| fig2 | nominal 6×3 geometry, RMSE per panel | `p1-fig-nominal-att`, `p1-fig-nominal-xadapt` |
| fig3 | 6×5 disturbance grid, path coloured by instantaneous error, disturbance glyphs, payload z-strip, LH sample dots | `p1-fig-dist-*` (8 runs) + nominal runs |
| fig4 | deployment dot/error-bar, tie band, clean-sensing hollow points | the seven LH+wind aggregates |
| fig5 | per-seed scatter at LH-fast with worst/best ratios | `ms-lh-s*`, `ms-lhfix-s*` |
| fig6 | launch transient, three traces on seed 4 | `ms-lh-s4`, `ms-mpcofss-lh-s4`, `mpc-plain-lh-s4` |

Three decisions worth recording because they change what the reader sees:

1. **fig3's colour map saturates at the 97th percentile of pooled error.**
   With a true max normalization one \SI{0.68}{\meter} excursion pushed every
   other panel into the bottom decile of viridis and the figure showed six
   uniformly dark lobes — i.e. it destroyed exactly the spatial structure it
   exists to show. The colourbar carries an extend arrow.
2. **fig3's payload z-strip is scaled to the sustained sag, not the
   transient.** Measured: PID holds ~\SI{8}{\centi\meter} low for the whole
   episode (median z 0.919 against a 1.000 reference) while ADRC, MPPI,
   xadapt and DATT return to 1.000 and offset-free MPC holds 1.000 apart from
   one dip to \SI{0.511}{\meter}. A shared axis covering the dip flattens
   everything else, so the window is [0.82, 1.06] and a caret marks the
   clipped trace.
3. **fig4's tie rule.** Overlap of raw ±1 s.d. intervals is too permissive —
   it admits MPPI (0.078±0.014) because a wide bar reaches back to the
   best stack's upper edge, 21 mm away. The figure instead calls a tie when
   the gap between means is within the larger of the two spreads, which
   yields exactly the four stacks claimed in the text.

**Verification of fig6 against the metric:** the figure recomputes the
soft-start run's full-window RMSE from the `.npz` as 0.21694, identical to
the value in that run's `summary.csv` — so the figure's arithmetic and the
reported metric agree. Its steady-state (t > 2.5 s) value is 0.048, a factor
of 4.5 apart, which is the whole point of Lesson 4.

**One source-code change was needed:** `rollout()` now also logs `meas_pos`,
the state the controller actually saw. It is additive (no dynamics or control
path touched) and it is what makes the \SI{34}{\hertz} Lighthouse staircase
plottable in fig3's deployment row; older `.npz` files simply lack the key and
the figure script degrades gracefully.

## Part C

**C.1 — compute, measured rather than remembered.** Median wall-clock for one
two-cycle episode over the three nominal tiers (`wall_time_s` in
`summary.csv`), unoptimized CPU harness:

| controller | slow | normal | fast | median |
|---|---|---|---|---|
| ADRC | 6.6 | 2.9 | 1.7 | **2.9** |
| PID | 9.6 | 3.1 | 1.8 | **3.1** |
| DATT-Asym | 5.6 | 3.2 | 1.8 | **3.2** |
| ADRC+xadapt | 24.3 | 9.5 | 5.4 | **9.5** |
| MPPI+L1 | 46.2 | 19.7 | 11.1 | **19.7** |
| Offset-free MPC | 87.0 | 41.0 | 36.0 | **41.0** |

The paper's remembered "20–70 s per episode" for the optimizer is close but
low at the slow tier (measured 36–87 s). Roughly \SI{3}{\second} of every row
is simulation overhead common to all stacks, so the column separates solver
load, not real-time feasibility; the recommendation table now carries it with
that caveat stated.

**C.2 — `\tbd` audit.** `grep -c '\tbd' publication1/*.tex` → `0` in every
content file; the single hit in `main.tex` is the macro definition itself.
Same for `\figplaceholder` (definition only).

## Build status — NOT verified, and why

`spie.cls` / `spiebib.bst` are gitignored and absent, and no LaTeX toolchain
is installed on either the Windows host or in WSL, so **the "compiles with no
overfull boxes" check could not be run.** Rather than assert it, the
following static checks were run instead (all pass):

- brace balance in all seven `.tex` files;
- every `tabular` row cell-count against its column spec (this caught nothing
  in the manuscript, but only after the checker itself was fixed — its first
  version mis-parsed `p{0.24\linewidth}` specs and reported 20 false
  failures);
- every `\includegraphics` target exists on disk;
- all 33 `\label`s resolve for every `\ref`;
- no `\tbd` / `\figplaceholder` left in content files.

The one layout risk a compile would catch and these checks cannot:
`tab:recommend` gained a fourth column, so it is the table to look at first
for an overfull `\hbox` once the author kit is in place.

## Open

- Compile with the real `spie.cls` and check box warnings (needs the author
  kit download).
- Table 3's two context rows (plain MPC, DATT-L1) were not re-measured this
  session; if the xadapt-style code-state question is raised for them too,
  they should be re-run before submission.
