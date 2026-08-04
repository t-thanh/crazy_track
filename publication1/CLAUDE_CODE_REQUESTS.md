# Requests for a Claude Code session — paper 1, round 3 (the trim)

Round 2 was thorough and the two self-corrections it surfaced are exactly right: the
ten-seed MPPI cell being *narrower* than the three-seed one, reported plainly instead of
buried, is what makes Lesson 3 credible. Nothing in Part A or B needs redoing.

**The author has now made the two decisions that were blocking.** This round executes
them. It is mostly deletion, which is harder to do well than addition — the instruction
throughout is *cut whole ideas, not adjectives*.

## What changed outside this session (pull first)

Committed already; do not redo:

- **Retitled**, away from reinforcement learning: *"Quadrotor Trajectory Tracking under
  Varying Payloads, Wind and Degraded Sensing: A Cross-Paradigm Controller Benchmark and
  Lessons Learnt."*
- **Table 3 overflowed** once the learned-policy row gained $\pm$ spreads. The spreads
  moved to a footnote under the table; the row is plain means again.
- **"the policy is the only one that barely moves" was wrong.** It moves the *other
  way*: 0.075 m with clean state, 0.059 m under degraded sensing. Rewritten to say so.
- **Two paragraphs added**: one in §4.2 explaining why the sampling stack is retained
  although it wins no column, one in the conclusion stating the learned policy's
  position plainly.
- **Build verified** at each step: 0 errors, 0 overfull boxes, 0 undefined references.
  Current length **20 pages** against the stub class, which I estimate at **15--16 real
  SPIE pages**.

One correction to round 2's page arithmetic: the references line assumed *88 bib
entries, ~25 cited*. `refs.bib` has **14 entries, all cited** — so the back matter is
about 0.35 pages cheaper than the plan assumed. Good news for the budget.

---

## Kickoff prompt (paste this)

> Continue paper 1 in the crazy_track repo. Pull first — the title and several
> paragraphs changed outside this session. Read
> `publication1/CLAUDE_CODE_REQUESTS.md` (round 3) and execute Part A, then Part B.
> This round is almost entirely cutting: the target is 10 SPIE pages, from ~15.
> Work in one commit per numbered cut so anything can be reverted individually, and
> record the before/after word count of each in
> `reports/2026-08-XX_p1-round3-trim.md`. Do not cut anything not on this list, and do
> not paraphrase a claim into vagueness to save words — if a claim cannot survive at
> full strength, delete it whole and say so in the report.

---

# Part A — the trim (author-approved)

Execute cuts 1--9 from your round-2 plan **as written** — they were well costed and all
are low risk. Then the two decisions:

### A.1 Drop Lesson 4 (launch transient) and Figure 6 — but not silently

The author chose to keep the hardware section and pay for it here. Removing Lesson 4
leaves three loose ends that must be tied, or the paper acquires an unexplained number:

1. **Table 4's offset-free MPC entry at $0.141\pm0.058$ under Lighthouse-normal is an
   outlier** — roughly triple its neighbours — and Lesson 4 was the only place that
   explained it. Add **one sentence** where that table is discussed: the elevated cell
   is a launch excursion whose tail extends past the one-second warm-up exclusion; the
   steady-state error beyond \SI{2.5}{\second} is \SI{0.046}{\meter}. Without it the
   table looks like an unexplained failure of the paper's best stack.
2. **The soft-start, Eq.~(\ref{eq:softstart}), loses its justification.** It currently
   reads as an unmotivated implementation detail. Add a clause in
   Sec.~\ref{sec:method:pool}: it was introduced because a cold observer's first
   innovations are noise-dominated at full gain, and ramping the estimate in also
   improved every nominal cell.
3. **The abstract cites the transient** as one of two self-corrections. Replace that
   clause with the seed corrections, which are stronger and now better evidenced: a
   single-seed reading that turned out to be the minimum of ten draws, and a three-seed
   variance figure that overstated both mean and spread. Check the introduction's
   contribution bullet for the same phrase.

Delete `fig6_transient` from `results.tex` and from the figure script's default set —
keep the generating code, marked as unused, since the campaign may want it later.

### A.2 Keep the sampling-based stack in the pool

Your plan offered demoting it to a context row for ~0.3 pages. **Do not.** It is the
only representative of its paradigm, and Lesson 3 — the strongest methodological result
in the paper — is built on its variance. A pool that silently drops every stack that
fails to win a column stops being a benchmark. The justifying paragraph is already
written; the 0.3 pages come from A.1 instead.

### A.3 Reframing follow-through

The title no longer names reinforcement learning, so sweep for places that still frame
the paper as an RL study: the introduction's related-work ordering (the learned-tracking
paragraph currently reads as the climax), the contribution bullets, and any phrasing
that positions the policy as the subject rather than one of six stacks. The finding that
the policy is worst under clean sensing and joins the lead only under degraded sensing
must **stay** — it is now a result among results, not the headline, and it should read
as neither a defence nor an attack.

---

# Part B — the last provenance gap

Four plain-MPC cells and three DATT-L1 cells in Table 3 were never re-measured at the
current code state. Both are context rows, so the exposure is low, but you flagged it
yourself as the last place a reviewer could press. If the trim leaves time:

```bash
python -m crazy_track.eval.lissajous_benchmark --controllers mpc --speeds normal \
  --disturbance wind_gust --tag p1-mpc-verify-gust \
  --reason "paper1 provenance: last un-re-measured context cells at current code state"
# and likewise payload, ground, plus nominal; then datt:<v3 model> for gust/payload/ground
```

If any value moves by more than \SI{0.005}{\meter}, say so in the report and update the
table; if none does, one line recording that the context rows are current closes the gap
permanently.

---

# Part C — what happens after this round

The manuscript then goes into a **writing pass** in the Cowork session — voice,
transitions, precision of claims, caption quality — so please leave the prose as it is
apart from the cuts listed above. Structural work that would help that pass:

1. Confirm the final page count against the stub class and report it.
2. List any place where a cut left a dangling reference, an orphaned figure mention, or
   a paragraph that now begins with "Second," having lost its "First".
3. Flag any claim that the trim weakened, so the writing pass can decide whether to
   restore it in fewer words or drop it outright.
