# Requests for a Claude Code session — paper 1 completion

Paste the **Kickoff prompt** below into a fresh Claude Code session at the repo root.
Everything after it is the detailed spec that session should follow.

---

## Kickoff prompt (paste this)

> Work on the crazy_track repo. Paper 1 (`publication1/`) is drafted; two things are
> missing: benchmark cells and figures. Read `publication1/CLAUDE_CODE_REQUESTS.md` and
> execute Part A then Part B. Run everything in the WSL venv
> (`wsl -d Ubuntu-24.04`, `~/venvs/crazy_track`). Use a meaningful `--reason` on every
> run, commit and push after each work unit, and record any cell that fails or looks
> anomalous in a new report `reports/2026-08-XX_p1-figure-and-gap-runs.md` rather than
> silently dropping it. When Part A finishes, update the tables in
> `publication1/results.tex` — replace every red `\tbd` with the measured value and
> delete the corresponding TODO comment. Do not change any number that is already there
> without saying so in the report.

---

# Part A — benchmark cells still missing

The paper's tables currently render unmeasured cells in red (`\tbd`). **The target is
zero red cells.** The controller pool is six stacks; the naming map is
DATT-Asym = v5 = `results/2026-07-22_17-32-52_datt-train/datt_ppo_final.zip`.

Two constraints from `HANDOVER.md`, do not rediscover them: controller families cannot
be mixed in one run (`attitude` / `force_torque` / `rotor_vel`), and single-seed
conclusions on anything policy-level are worthless.

### A.1 ADRC bandwidth consistency (the row currently mixes $\omega_o = 7$ and $10$)

`ADRCController` now defaults to $\omega_o = 7$, so plain `--controllers adrc` is correct.

```bash
python -m crazy_track.eval.lissajous_benchmark --controllers adrc \
  --speeds slow normal fast --tag p1-adrc-w7-nominal \
  --reason "paper1 Table 2: ADRC nominal row currently mixes w=10 (slow/fast) and w=7 (normal)"

python -m crazy_track.eval.lissajous_benchmark --controllers adrc \
  --speeds normal --disturbance payload --tag p1-adrc-w7-payload \
  --reason "paper1 Table 3: ADRC payload cell predates the w=7 retune"

python -m crazy_track.eval.lissajous_benchmark --controllers adrc \
  --speeds normal --disturbance ground --tag p1-adrc-w7-ground \
  --reason "paper1 Table 3: ADRC ground cell predates the w=7 retune"

python -m crazy_track.eval.lissajous_benchmark --controllers adrc \
  --speeds slow fast --sensor lighthouse --tag p1-adrc-w7-lh \
  --reason "paper1 Table 4: ADRC lighthouse slow/fast cells missing at w=7"
```

### A.2 THE IMPORTANT ONE — is the deployment tie three-way or four-way?

The paper claims a three-way statistical tie at LH\,+\,wind
(offset-free MPC $0.057\pm0.014$, DATT-Asym $0.059\pm0.002$, ADRC+xadapt
$0.060\pm0.009$). Plain ADRC posted **0.053** in that cell — better than all three —
but from a **single** evaluation seed, which the paper's own Lesson 3 says we may not
read. Until this runs, the headline claim has a hole in it.

```bash
for S in 0 1 2 3 4 5 6 7 8 9; do
  python -m crazy_track.eval.lissajous_benchmark --controllers adrc --speeds normal \
    --sensor lighthouse --disturbance wind_const --seed $S --tag ms-adrc-lhwind-s$S \
    --reason "paper1 headline: 10-seed ADRC w=7 at LH+wind; single-seed 0.053 would make the deployment tie four-way"
done
python -m crazy_track.eval.aggregate_seeds --prefix ms-adrc-lhwind
```

**Report the result explicitly**, whichever way it goes. If the 10-seed mean lands
inside the tie band, the paper gains a fourth tied stack and the estimator-limited
argument gets *stronger* (four unrelated mechanisms, not three). If it lands below,
the headline must be rewritten. Either outcome is publishable; a missing run is not.

### A.3 Remaining `\tbd` cells

```bash
# MPPI+L1 at the tuned config, force disturbances
for D in wind_const payload ground; do
  python -m crazy_track.eval.lissajous_benchmark --controllers mppi_l1 --speeds normal \
    --disturbance $D --tag p1-mppi-$D \
    --reason "paper1 Table 3: tuned MPPI $D cell; existing values predate the N=512/AR(1) tuning"
done

# Offset-free MPC, force disturbances + lighthouse slow
for D in wind_gust payload ground; do
  python -m crazy_track.eval.lissajous_benchmark --controllers mpc_offsetfree --speeds normal \
    --disturbance $D --tag p1-ofmpc-$D \
    --reason "paper1 Table 3: offset-free MPC (soft-start) $D cell never measured"
done
python -m crazy_track.eval.lissajous_benchmark --controllers mpc_offsetfree --speeds slow \
  --sensor lighthouse --tag p1-ofmpc-lh-slow \
  --reason "paper1 Table 4: offset-free MPC lighthouse slow cell missing"

# Ground effect for the two remaining stacks (separate sim modes -> separate runs)
python -m crazy_track.eval.lissajous_benchmark --controllers xadapt_adrc --speeds normal \
  --disturbance ground --tag p1-xadrc-ground \
  --reason "paper1 Table 3: ground-effect cell missing for the hybrid adaptive stack"
python -m crazy_track.eval.lissajous_benchmark \
  --controllers datt:results/2026-07-22_17-32-52_datt-train/datt_ppo_final.zip \
  --speeds normal --disturbance ground --tag p1-datt-asym-ground \
  --reason "paper1 Table 3: ground-effect cell missing for DATT-Asym"

# LH+wind rows for PID and MPPI (10 seeds each, same protocol as A.2)
for C in pid mppi_l1; do for S in 0 1 2 3 4 5 6 7 8 9; do
  python -m crazy_track.eval.lissajous_benchmark --controllers $C --speeds normal \
    --sensor lighthouse --disturbance wind_const --seed $S --tag ms-$C-lhwind-s$S \
    --reason "paper1 Table 4: $C deployment-cell row, 10 eval seeds"
done; done
python -m crazy_track.eval.aggregate_seeds --prefix ms-
```

### A.4 Deliverable for Part A

A single markdown table in the new report mapping **every** cell of
`publication1/results.tex` Tables 2, 3 and 4 to its run directory, then the edits to
`results.tex` replacing each `\tbd`. Flag any value that contradicts what the paper
currently states.

---

# Part B — figures

Write **one script**, `scripts/make_paper1_figures.py`, that regenerates every figure
from the run directories and writes vector PDFs into `publication1/figures/`. It must be
re-runnable and must not modify anything under `results/`.

## Shared style

- Vector PDF, no rasterization. `matplotlib.rcParams` with a serif font, font size 8
  (labels 8, tick labels 7, panel titles 8).
- Widths: \SI{17}{\cm} for a full-width figure (SPIE is single-column with a
  \textasciitilde\SI{17.5}{\cm} text block); never exceed it.
- Colour per controller, fixed across **all** figures, colour-blind safe:
  PID `#4C72B0`, ADRC `#DD8452`, MPPI+L1 `#55A868`, offset-free MPC `#C44E52`,
  ADRC+xadapt `#8172B3`, DATT-Asym `#937860`.
- The reference is always thin black, dashed, drawn **under** the flown path.
- No chartjunk: no grid boxes, no panel frames except left/bottom spines, no legends
  repeated per panel — one shared legend per figure.

## B.1 Figure 2 — nominal tracking (the "Figure 5" figure)

This is the figure the reader looks at first; get it right.

- Layout: **6 columns (controllers) × 3 rows (speeds)**, `sharex`/`sharey`, equal aspect.
  Controller name as a column title on the top row only; speed label
  (`slow, T = 15.0 s`) rotated on the left of each row only.
- Each panel: reference figure-eight in dashed black, flown $xy$ path in the
  controller's colour, and the RMSE printed in the panel corner
  (`0.022 m`, 7 pt, same colour as the path).
- Source: one run per sim mode so all cells are from the same code state —
  `pid adrc mppi_l1 mpc_offsetfree datt:<v5>` in one attitude-mode invocation,
  `xadapt_adrc` in a second (`rotor_vel`), both at `--speeds slow normal fast`.
  Tag them `p1-fig-nominal-att` and `p1-fig-nominal-xadapt`.
- Read `pos` and `ref_pos` from the per-rollout `.npz`; drop the first \SI{1}{\second}
  so the plotted path matches the reported metric.

## B.2 Figure 3 — tracking under disturbance (the new one)

Same geometry, but now the disturbance must be **visible in the plot**, which is the
point the reviewer will look for.

- Layout: **6 columns (controllers) × 5 rows (conditions)**: nominal, constant wind,
  gust, payload, LH\,+\,wind. Normal tier throughout.
- **Colour the flown path by instantaneous error magnitude** (`viridis`, shared
  normalization across the whole figure, one horizontal colourbar underneath labelled
  `position error [m]`). This is what makes the figure earn its space: the reader sees
  *where on the lobe* the error concentrates, not just how much there is.
- **Disturbance glyphs**, drawn identically in every panel of a row:
  - *constant wind*: three light grey arrows across the panel background pointing
    $+x$, annotated once per row `2.5 m/s² (+x)`;
  - *gust*: the same arrows drawn with a sinusoidal shaft, annotated
    `0.7 Hz + turbulence`;
  - *payload*: a downward arrow glyph in the corner annotated `+10 g (23 % weight)`,
    **plus** a \SI{1}{\cm} strip below each payload panel showing $z(t)$ against
    $z_{\mathrm{ref}}$ — the payload error is vertical and is invisible in an $xy$ plot,
    which is exactly the trap to avoid;
  - *LH + wind*: wind arrows as above, and overlay the raw Lighthouse position samples
    as small grey dots so the \SI{34}{\hertz} staircase and the bias offset are visible.
- Print RMSE in each panel corner as in Fig. 2.

## B.3 Figure 4 — the deployment cell

Horizontal dot-and-error-bar plot, one row per controller, sorted best to worst.
Filled dot = mean, bar = $\pm$ one standard deviation across seeds, hollow dot = the
same controller's clean-sensing value at the same tier (so the reader sees each stack is
further from itself than from the others — that is the argument). Shade the tie band
spanning the tied stacks' error bars. Annotate each row with its seed count and type
(`n = 10 eval` / `n = 3 train`).

## B.4 Figure 5 — variance, not means

Strip plot: x = controller, y = RMSE at the LH-fast cell, one marker per seed, with the
mean drawn as a horizontal tick. Include MPPI+L1, DATT-L1 and DATT-Asym at minimum. The
figure must make one thing obvious at a glance: two controllers scatter over a factor of
five while the third collapses onto its mean.

## B.5 Figure 6 — the launch transient

$\lVert \mathbf{p}(t) - \mathbf{r}(t)\rVert$ against time for three traces on the *same*
unlucky seed (4 or 8): offset-free MPC before soft start, after soft start, and plain
MPC. Shade $t < \SI{1}{\second}$ (the excluded warm-up) in light grey and
$t > \SI{2.5}{\second}$ (the steady-state window) in a lighter tint; annotate the two
RMSE values for the after-soft-start trace — full-window and steady-state — to show that
the metric and the mechanism disagree.

## B.6 Deliverable for Part B

`publication1/figures/*.pdf` plus the script, and in `results.tex` replace each
`\figplaceholder{...}` with the corresponding
`\includegraphics[width=\linewidth]{figN}`. Rebuild the document and confirm it
compiles with no overfull boxes. Note that `spie.cls` and `spiebib.bst` are gitignored —
they must be downloaded from the SPIE author kit for a real build.

---

# Part C — nice to have, only if A and B are done

1. **Wall-clock / compute column.** The recommendation table claims the optimizer costs
   \SIrange{20}{70}{\second} per episode against a single forward pass for the policy.
   `summary.csv` already carries `wall_time_s`; extract the median per controller across
   the nominal runs so the claim is sourced rather than remembered.
2. **A `\tbd` audit hook**: a one-line grep in the report confirming
   `grep -c '\\tbd' publication1/*.tex` returns 0.
