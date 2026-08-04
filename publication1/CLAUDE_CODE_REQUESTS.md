# Requests for a Claude Code session — paper 1, round 5 (two experiments)

Round 4 executed cleanly, and two judgement calls in it were better than the request
that prompted them: splicing Lesson 4 out of `2ed7ff3^` rather than reverting (which
would have taken cuts 7–9 with it), and **measuring the four context-row cells the table
merge required rather than asserting them.** The merged table is clearer than the two it
replaced.

The fresh-eyes list in E.3 is the most useful thing produced in this project. This round
acts on it. Two of the four items need runs; the other two are writing fixes and will be
handled in the writing pass, not here.

## Build, confirmed here

`pdflatex` + `bibtex` against a stub class: **0 errors, 0 overfull boxes, 0 undefined
references, 19 pages** (≈14–15 real SPIE pages).

The two overfull boxes were **not** fixed by the round-4 rewording — both survived at
byte-identical widths, because in each case the culprit was `parameterization` welded to
a `\cite` at a line end, and splitting the sentence did not give TeX a break opportunity
inside that unit. Both are now reworded to avoid the word entirely, plus
`\emergencystretch=1em` in the preamble. Already committed; do not redo.

---

## Kickoff prompt (paste this)

> Continue paper 1 in the crazy_track repo. Pull first. Read
> `publication1/CLAUDE_CODE_REQUESTS.md` (round 5). Two experiments, both from your own
> E.3 list: a sensor-bias sweep that tests whether the deployment cell is actually
> estimator-limited, and an evaluation-seed run for the learned policy so the four-way
> tie compares like with like. Report in `reports/2026-08-XX_p1-round5.md`. **Report
> what the data says even if it contradicts the paper's central claim** — especially
> then.

---

# Part A — test the estimator-limited claim (your E.3 item 3)

This is the most valuable experiment left in the project. You wrote:

> "Estimator-limited, not architecture-limited" is an interpretation presented as a
> finding. […] That is consistent with an estimator bound, but also with four stacks all
> being limited by the same actuator envelope, or by the reference itself at that tier.

That is correct, and it is the paper's headline claim. The proposed discriminating test
is right and cheap: **if the binding constraint is the estimator, scaling the sensor
model's error should move all four tied stacks together; if it is the actuator envelope
or the reference, it should not.**

`LighthouseSensor` already takes `bias_std` (default \SI{0.015}{\meter} per axis) and the
noise parameters. Add a scalar multiplier — a `--sensor-scale` flag on the benchmark
that multiplies `bias_std`, `vel_std`, `att_std_deg` and `jitter_std` together, so a
single knob moves the whole measurement quality. Then sweep it over the deployment cell:

```
scales:      0.25, 0.5, 1.0, 2.0
controllers: mpc_offsetfree, xadapt_adrc, adrc, datt:<v5 seed 0>
condition:   --speeds normal --sensor lighthouse --disturbance wind_const
seeds:       5 evaluation seeds per cell   (4 x 4 x 5 = 80 runs)
```

**What each outcome means, decided in advance so the analysis cannot drift:**

- *All four improve monotonically and stay within each other's spread as the scale
  falls* → the claim is demonstrated, not inferred. It becomes the paper's strongest
  result and earns a figure: RMSE against sensor-error scale, four curves converging at
  every point.
- *They improve but separate as the scale falls* → the tie is a property of this sensor
  quality specifically, which is a **more precise** and still publishable claim. The
  scale at which they separate is then a number worth reporting.
- *They do not improve* → the claim is wrong, and something else binds. Say so plainly;
  a benchmark paper that falsifies its own interpretation is worth more than one that
  asserts it.

Do not adjust the claim's wording yourself — report the curves and let the writing pass
rewrite §4.3 to match whichever outcome occurred.

# Part B — make the tie compare like with like (your E.3 item 2)

You noted that three tied members are ten *evaluation* seeds while the policy is three
*training* seeds, and that these are not commensurable. The cheap fix is to measure the
missing object rather than caveat it:

```
python -m crazy_track.eval.lissajous_benchmark \
  --controllers datt:results/2026-07-22_17-32-52_datt-train/datt_ppo_final.zip \
  --speeds normal --sensor lighthouse --disturbance wind_const --seed $S \
  --tag ms-datt-asym-lhwind-s$S --reason "paper1: evaluation-seed spread for the policy so the four-way tie compares like with like"
```

for `S` in 0..9, on the **seed-0 training run** so the result is a pure evaluation-seed
spread. The paper can then report both for the policy — an evaluation-seed spread
directly comparable to the other three members, and the training-seed spread as a
separate statement about initialization robustness. Two numbers, two meanings, neither
doing the other's job.

If the evaluation-seed spread turns out much wider than $\pm0.002$, that is itself
important: the variance-collapse claim in Lesson 3 would then be about training
initialization only, not about the policy's run-to-run behaviour, and Lesson 3 needs
rewording.

# Part C — not for this round

Your items 1 and 4 are writing problems and will be fixed in the writing pass:

- **Item 1** ("each the best member of its own family") will be replaced by a per-stack
  statement of how each configuration was chosen — sweeps where sweeps exist, and plainly
  "standard gains, not swept" where they do not. Your observation that the claim is
  strongest where the paper spent effort and weakest where it did not, which is the exact
  asymmetry the paper criticises in others, is the right reason to fix it.
- **Item 4** (the recommendation table's "Cost" column) will be relabelled to name what
  it measures. If a per-control-step solver time is cheap to instrument, report it in
  your round-5 notes and it will be used instead; if not, the relabel stands.

Do not edit prose for either — just flag anything you notice in passing.

# Part D — after this

The manuscript goes to the writing pass. Nothing further will be asked of this workflow
unless Part A overturns something.
