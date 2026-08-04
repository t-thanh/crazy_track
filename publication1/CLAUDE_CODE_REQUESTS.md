# Requests for a Claude Code session — paper 1, round 4 (restore, then hand over)

Round 3 was the best report of the four. Three things in particular:

- **Reporting that the cuts delivered 1.6 pages instead of 5, and why**, rather than
  padding the number — the diagnosis (cuts 1, 2, 3 and 7 were costed on the assumption
  that their words were restatement, and they were not) is exactly right.
- **Refusing cut 3's second half after trying it**: removing Lesson 2's bandwidth numbers
  turned the lesson into an assertion, so they went back. That is the correct instinct.
- **The "claims the trim weakened" list.** That list is what this round acts on.

## The premise has changed

The author has since said: **length is not a strict requirement, provided the scientific
contributions are clearly stated.** Several of round 3's cuts were made only to buy
pages. Those should come back. This round is mostly `git revert` plus a few restorations
— then the manuscript goes to a writing pass and this workflow ends.

Current state, built here against a stub class: **0 errors, 0 undefined references,
2 minor overfull boxes, 18 pages** (≈14 real SPIE pages, matching round 3's arithmetic).

---

## Kickoff prompt (paste this)

> Continue paper 1 in the crazy_track repo. Pull first. Read
> `publication1/CLAUDE_CODE_REQUESTS.md` (round 4). The page limit has been relaxed, so
> this round restores content that round 3 cut only for length, takes one structural
> improvement worth having regardless, and closes the last two data cells. Record
> everything in `reports/2026-08-XX_p1-round4.md`. After this round the manuscript goes
> to a writing pass elsewhere — so leave prose style alone and change only what is
> listed.

---

# Part A — restore what was cut only for length

### A.1 Bring back Lesson 4 and Figure 6

`git revert 2ed7ff3`, then re-apply the bookkeeping in reverse: lessons renumber back to
seven, "six lessons" → "seven" in the abstract and the lessons preamble,
`fig6_transient` returns to the figure script's default set, and the three loose-end
patches from round 3 are reconciled rather than duplicated —

- the sentence added under Table 4 explaining the $0.141\pm0.058$ outlier now overlaps
  Lesson 4. **Keep the table sentence** (a reader meeting that number should not have to
  wait for the lessons section) and shorten Lesson 4's opening so it does not repeat it;
- the soft-start justification clause in §3.3 should stay as well — it is the right
  place for *why the mechanism exists*, while Lesson 4 is the right place for *how we
  misdiagnosed it*. Make sure the two do not use the same sentence twice.

Lesson 4 is the paper's most transferable procedure — "check when the maximum error
occurs before attributing an error level to steady-state noise" — and it is the only
lesson a reader can apply to a paper that is not this one.

### A.2 Restore three of the six claims deleted whole

From round 3's own list, restore:

1. **MPPI's AR(1) exploration noise as the single largest tuning gain measured**
   (methodology). It is a concrete empirical result about a method the paper includes,
   and it is the only place the sampling stack's tuning is justified at all.
2. **Lesson 5's next step** — recurrence or explicit innovation-variance features. A
   negative result without a stated remedy is half a result.
3. **The conclusion's state-pre-filtering next step**, which follows Lesson 4 back in.

Leave deleted: the hybrid stack's layer-complementarity sentence in the methodology (it
does duplicate Lesson 6 verbatim — that call was right), and the conclusion's
"several cells remain to be completed", which is now simply false.

### A.3 Reconcile the abstract's self-corrections

With Lesson 4 back, the paper records **three** occasions on which our own earlier
reading of the data was wrong: a launch transient misdiagnosed as noise fragility, a
single evaluation seed that proved to be the minimum of ten draws, and a three-seed
variance figure that overstated both its mean and its spread. The abstract currently
promises two, both seed-related.

Rather than pick two, consider stating it as what it is — that the study corrected
itself three times, and that this is an argument for the protocol rather than an
embarrassment. One sentence. The introduction's contribution bullet should match, and
the introduction's motivation paragraph (which round 3 flagged as over-promising on
transients) becomes accurate again automatically.

---

# Part B — one structural improvement worth taking anyway

**Merge Tables 2 and 3.** Round 3 identified this and it is not a length cut: Table 3's
`nominal` column *is* Table 2's `normal` column, printed twice, which is a place where a
reader can find two numbers that must agree and has to check that they do. One table
with slow / normal / fast plus the four disturbance columns removes a caption, a header
and six duplicated cells, and makes the speed axis and the disturbance axis visible in
one place.

Watch two things: the merged table is eight columns wide, so it needs `\small` and
compact headers (it is the shape that overflowed twice before); and the learned-policy
row carries its spreads in a footnote — keep that convention.

If on inspection the merge makes the table unreadable rather than clearer, do not force
it: say so in the report and leave both tables. This is a judgement about legibility,
not a mandate.

---

# Part C — the last two cells, and two typographic defects

1. **DATT-L1 nominal (0.048) and wind (0.050)** were not on round 3's list and remain at
   their original measurement. Its other three cells reproduced to the fourth decimal,
   so this is almost certainly a formality — but "every cell of Table 3 is current"
   should be literally true.
2. **Two overfull boxes** appeared in the round-3 edits, both small and both in text
   that the writing pass will touch anyway: `introduction.tex` lines 50–66 (0.3 pt, the
   merged disturbance-rejection/predictive paragraph) and `methodology.tex` lines 94–101
   (12.7 pt, the observer paragraph). Fix by rewording, not by `\sloppy`.

---

# Part D — the hardware bring-up flights (author's call, not a default)

The first hardware flights are logged and analysed, and the round-3 report is right that
they do not belong in the results — they are bring-up, and their limiting factor is a
command clip rather than a controller property.

But one finding is a **precondition for the campaign the paper pre-registers**, and the
paper currently promises a protocol that these flights show cannot yet measure what it
claims: the deployed attitude command is clipped at $\pm15^\circ$ while the policy was
trained against roughly $\pm40^\circ$, and the reference starts far from the vehicle, so
the policy rails immediately and the actuator saturates for 84--97 % of samples. A
campaign run under those conditions would measure the clip, not the controller.

My recommendation, for the author to accept or decline: **two sentences in §3.7's
protocol paragraph** stating that the command envelope must be aligned with the training
envelope and the reference initialized at the vehicle's position, and that both were
identified in bring-up flights. That makes the pre-registration stronger, not weaker —
it shows the protocol is informed by contact with the hardware rather than designed on
paper. The counter-argument, which is legitimate: a paper with no hardware results yet
may not want to introduce a hardware problem it has not solved.

Do not make this change unless the author confirms it.

---

# Part E — handover

After this round the manuscript goes to a writing pass. To prepare:

1. Confirm the stub-class build: errors, overfull boxes, undefined references, pages.
2. Update `publication1/OUTLINE.md`, which is still rev. 2 and now describes a paper that
   no longer exists — wrong title, eight-stack pool language, "three-way tie",
   seven-then-six-then-seven lessons, and a figure plan that predates the figures. Either
   bring it current or mark it clearly as a historical planning document.
3. List anything you believe is still weakly evidenced or over-claimed. You have found
   three such things unprompted across three rounds; a fourth pass with fresh eyes on
   the finished draft is worth more than another round of cuts.
