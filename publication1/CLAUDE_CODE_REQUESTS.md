# Requests for a Claude Code session — paper 1, round 2

Round 1 (gap runs + figures) is done and was good work: zero red cells, five vector
figures, four corrections found and documented, and the four-way tie discovery is a
better result than the claim it replaced. This round is **verification fallout, two
data gaps that undermine specific claims, and a length problem.**

**Read this first — the manuscript prose has already changed.** Pull before starting.
The following were fixed outside this repo session and are already committed:

- `abstract.tex` and `introduction.tex` still said *three-way* tie after round 1
  updated `results.tex` and `conclusion.tex` to four-way. Both now name all four stacks.
- `tab:recommend` overflowed (the predicted overfull `\hbox`); column widths narrowed.
- The deployment table listed MPPI (0.078) above DATT-Noisy (0.077); reordered.

**The build check you could not run has now been run.** With a stub class standing in
for `spie.cls`: `pdflatex` + `bibtex` complete with **0 errors, 0 overfull boxes, 0
undefined references or citations**. So the manuscript is structurally sound — the open
issues below are about content, not LaTeX.

---

## Kickoff prompt (paste this)

> Continue paper 1 in the crazy_track repo. Read
> `publication1/CLAUDE_CODE_REQUESTS.md` (round 2) and execute Parts A, B and C in that
> order. Pull first — the .tex prose changed outside this session. Same discipline as
> last time: meaningful `--reason`, commit and push per work unit, and append findings
> to a new report `reports/2026-08-XX_p1-round2.md`. Where a request asks you to change
> a number in the manuscript, state the old and new value in the report.

---

# Part A — two claims resting on too little data

Both of these are load-bearing sentences that a reviewer can attack, and both are cheap
to fix.

### A.1 The variance lesson rests on three seeds for MPPI

Lesson 3 ("mean-only tables mislead") leans hardest on MPPI's Lighthouse-fast cell,
quoted as $0.228\pm0.178$ with range $0.091$--$0.480$. **That is $n = 3$**, while every
other stack in Figure 5 is $n = 10$ — the figure itself prints `(n = 3)` under the
controller whose spread carries the argument. A reviewer will notice that a claim about
the unreliability of small samples is itself made from a small sample.

```bash
for S in 3 4 5 6 7 8 9; do
  python -m crazy_track.eval.lissajous_benchmark --controllers mppi_l1 --speeds fast \
    --sensor lighthouse --seed $S --tag ms-mppi-lhfast-s$S \
    --reason "paper1 Lesson 3: extend tuned MPPI LH-fast from 3 to 10 eval seeds; the variance claim currently rests on n=3"
done
python -m crazy_track.eval.aggregate_seeds --prefix ms-mppi-lhfast
```

Seeds 0--2 already exist under `ms-lhfix-s*`; reuse them rather than re-running, but
**check they are the same controller configuration** before pooling — if they are not,
run all ten fresh and say so. Update Table 4, Lesson 3 and Figure 5. If the ten-seed
spread turns out narrower than the three-seed one, say so plainly: it weakens the
example but the lesson survives on DATT-L1, which is already $n = 10$.

### A.2 The learned-policy row mixes seed counts silently

In Table 3, DATT-Asym's wind cell is a three-training-seed mean while its gust
($0.091$) and payload ($0.102$) cells are single evaluations of the seed-0 model. The
row reads as homogeneous and is not.

```bash
for S in 0 1 2; do
  M=results/<v5-seed-$S-train-run>/datt_ppo_final.zip
  python -m crazy_track.eval.lissajous_benchmark --controllers datt:$M --speeds normal \
    --disturbance wind_gust --tag mst-v5-gust-s$S \
    --reason "paper1 Table 3: DATT-Asym gust cell is single-seed while the rest of the row is 3-seed"
  python -m crazy_track.eval.lissajous_benchmark --controllers datt:$M --speeds normal \
    --disturbance payload --tag mst-v5-payload-s$S \
    --reason "paper1 Table 3: DATT-Asym payload cell is single-seed while the rest of the row is 3-seed"
done
python -m crazy_track.eval.aggregate_seeds --prefix mst-v5
```

The three v5 training runs are listed in `papers/paper1-benchmark/README.md`. If a
three-seed run is not worth the time, the acceptable alternative is to **mark the two
cells as single-seed in the table** — but do not leave them unmarked.

### A.3 The context rows you flagged yourself

Your report notes that the plain-MPC and DATT-L1 context rows were not re-measured, and
the xadapt row moved substantially once it was. Two of those context values are quoted
in the running text and carry arguments: plain MPC under wind (0.196, the "most
sophisticated controller is also the worst" point) and DATT-L1 under gust (0.061, the
gust champion). Re-run at least those two; if they move, the surrounding sentences move
with them.

---

# Part B — figure fixes

The figures are good. Three fixes, one of which matters a lot.

### B.1 (important) Figure 3's deployment row prints the number the paper says not to read

The LH\,+\,wind row labels each panel with that panel's own single-seed RMSE. For ADRC
this prints **0.053 m** — which is precisely the lucky-minimum draw that
Sec.~4.3 spends a paragraph explaining we must not read, against a ten-seed mean of
0.063. The figure currently contradicts the text on the exact point the text is making.

Fix: in the LH\,+\,wind row (and any other row where the table value is a seed
aggregate), print the **aggregate** in the panel corner —
`0.063 ± 0.006 m` — and let the drawn trace remain one representative seed, identified
in the caption (as Figure 2's caption already does for the learned policy). If the
aggregate does not fit, print the mean alone and put the spread in the caption.

Check every other panel label in Figures 2, 3 and 4 for the same mismatch and make the
rule uniform: **a printed number matches its table cell, or the caption says which
single realization it is.**

### B.2 Figure 4: the `n = 3 train` annotation collides with the DATT-Asym marker

Visible overlap in the rendered PDF. Offset the annotation or right-align the whole
column of `n = ...` labels.

### B.3 Figure 6: annotate that 0.217 m is one seed

The panel quotes a full-window RMSE of 0.217 m; Table 4 gives $0.141\pm0.058$ for the
same controller and cell. Both are right — the figure is seed 4 — but a reader
cross-checking will think one is wrong. Add `(seed 4; 10-seed mean 0.141 m)` to the
annotation.

### B.4 Minor, only if quick

The Lighthouse sample dots in Figure 3's bottom row are hard to see at print size, and
they are the visual evidence for the 34 Hz staircase. Slightly larger, or a lighter path
alpha underneath.

---

# Part C — length

**This is now the largest open problem.** The manuscript is **8,330 words** of body text
plus five figures and five tables. Compiled against a stub class it is 19 pages;
allowing for SPIE's denser layout, expect roughly **14--15 pages against a 10-page
target.**

Do not start cutting unilaterally — propose first. Produce a trim plan in the report
that reaches ~10 pages, showing estimated words saved per cut, working down this
priority order:

1. **Methodology (2,617 + 708 words) is the biggest block and the most compressible.**
   The controller pool subsection restates parameters that Table 1 already carries; the
   equations for PID and the observer are standard and could be cited rather than
   written. Target: 600--800 words.
2. **Lessons 2 and 6** carry full numeric evidence inline. Each could keep its claim and
   mechanism and drop half its numbers to the tables. Target: 300 words.
3. **The hardware subsection (708 words)** is long for a campaign whose results are not
   yet in the paper. The falsification-targets paragraph is worth keeping — it is what
   makes the campaign pre-registered — but the specification detail could halve.
   Target: 300 words.
4. **Related work** — four paragraphs could become three by merging the predictive and
   sampling threads. Target: 150 words.
5. **Figures 5 and 6** could merge into one two-panel figure, or Figure 5 could become a
   two-column inset. Saves roughly half a page.

Report the plan with numbers; the author decides which cuts to take before any are made.

---

# Part D — bookkeeping

1. The report's own note that `tab:recommend` was the layout risk was correct, and it
   has been fixed; nothing further needed there.
2. `rollout()` gaining `meas_pos` is a good change — please confirm the existing test
   suite still passes (`python -m pytest tests/`) and note it in the report, since it
   touched shared harness code.
3. `papers/paper1-benchmark/README.md` still describes the eight-stack pool and the
   three-way tie. Update it to the six-stack pool and the four-way result so the repo
   index does not contradict the manuscript.
