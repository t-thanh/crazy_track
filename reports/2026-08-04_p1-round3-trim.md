# 2026-08-04 — Paper 1 round 3: the trim

Round 3 of `publication1/CLAUDE_CODE_REQUESTS.md`. One commit per numbered cut,
so any single cut can be reverted with `git revert` without disturbing the
others. **Headline: the listed cuts deliver about 1.6 pages, not the 5 the plan
budgeted.** Why, and what would close the rest, is at the bottom.

## Word counts, per cut

Body words only: comments, floats (`table`, `figure`, `equation`, `center`) and
captions are excluded, so a cut that removes a table shows as no change here and
is costed in page area instead. Baseline **7,132**.

| # | commit | scope | before | after | saved |
|---|---|---|---|---|---|
| 1 | `97ac149` | methodology controller pool + learned policy | 669 | 509 | **160** + 2 equations |
| 2 | `c6cf052` | hardware subsection | 703 | 544 | **159** |
| 3 | `67fcc02` | Lessons 2 and 6 | 358 | 332 | **26** (Lesson 2 not takeable) |
| 4 | — | merge Figs 5 and 6 | — | — | superseded by A.1 |
| 5 | `e5b3e36` | related work, four paragraphs to three | 371 | 337 | **34** |
| 6 | `02a58c3` | Fig. 3 to $0.8\linewidth$ | — | — | ~0.17 page |
| 7 | `87f7a0a` | results §4.1–4.3 prose | 1,348 | 1,325 | **23** (largely not takeable) |
| 8 | `980b2d6` | conclusion | 630 | 571 | **59** |
| 9 | `8c037fe` | deployment inline tabular to prose | — | — | ~0.22 page (adds 83 words) |
| A.1 | `2ed7ff3` | delete Lesson 4 + Fig. 6 | 233 | 0 | **233** + ~0.37 page |
| A.2 | — | keep the sampling stack in the pool | — | — | no change, by instruction |
| A.3 | `f6a63de` | reframing follow-through | 112 | 123 | **−11** (correctness, not a cut) |

**Body total 7,132 → 6,643 (−489 words, −6.9 %).**

## Where a cut could not be taken at full strength

Per the instruction to delete whole rather than weaken:

- **Cut 3, Lesson 2 half — not taken.** The cut was to move its numeric
  evidence "to the tables it duplicates", but the bandwidth sweep
  ($\omega_o \in \{3,5,7,10\}$ across six conditions) is tabulated nowhere.
  Those four pairs of numbers are the entire evidence both for the crossing and
  for the adaptive-bandwidth negative result. I removed them, saw the lesson
  become an assertion, and restored them verbatim.
- **Cut 7 — mostly not taken.** The plan expected "several sentences restating
  table values" in §4.1–4.3. On inspection each restated number is doing
  mechanism work (which stack is alone at the fast tier; which mechanism wins
  each disturbance column; the single-seed correction the abstract now
  advertises). Only one true duplication existed — one that cut 9 had just
  created — and it was removed.
- **Cuts 1 and 2 fall short of their targets** (509 vs 300, 544 vs 350). The
  300-word figure assumed Table 1 already carried the controller gains and
  hyperparameters; it carries paradigm, representative, internal model and
  disturbance handling only, so deleting the numbers would leave the pool
  unreproducible. What is left of the hardware subsection is the vehicle, the
  two motion-capture roles, the flight matrix and the falsification targets.

### Claims deleted whole (not weakened)

1. MPPI's AR(1) exploration noise as "the single largest tuning gain we
   measured" (methodology).
2. The hybrid stack's layer-complementarity sentence in the methodology —
   Lesson 6 states it in the same words.
3. Lesson 4 in its entirety (the launch transient), per A.1.
4. Lesson 5's "recurrence or explicit innovation-variance features is the
   indicated next step".
5. The conclusion's limitation "several cells of the disturbance matrix remain
   to be completed", which round 1 made false by filling every cell.
6. The conclusion's state-pre-filtering next step, which existed only to close
   the transient story.

## A.1 — the three loose ends, tied

| loose end | resolution |
|---|---|
| Table 4's $0.141\pm0.058$ outlier | one sentence added where Table 4 is discussed: a launch excursion whose tail extends past the \SI{1}{\second} warm-up exclusion; steady-state error beyond \SI{2.5}{\second} is \SI{0.046}{\meter} |
| Eq. (softstart) left unmotivated | justification clause added in §3.3: a cold observer's first innovations are noise-dominated at full gain, and ramping the estimate in also improved every nominal cell |
| abstract cites the transient | replaced with the two seed corrections; the matching introduction contribution bullet updated identically |

Bookkeeping that A.1 forced: lessons renumbered 5,6,7 → 4,5,6, every
cross-reference updated (`Lesson~6`→`5`, `Lesson~7`→`6`), "seven lessons" →
"six" in both the abstract and the lessons preamble, and `fig6_transient` moved
out of the figure script's default set into `OPTIONAL` with a comment marking it
unused. No dangling `\ref` remains.

## A.3 — reframing

The related-work section closed on "what remains open is what these methods buy
once the classical alternatives are tuned under the same conditions", which
frames the study as an RL evaluation. The gap is symmetric and now says so:
comparisons rarely tune every candidate under the same conditions, most tune the
method under study carefully and its alternatives casually, and reported
differences therefore confound paradigm with tuning effort. The critique is kept
at full strength; only its direction changed. The contribution bullets and the
abstract already listed the six stacks as peers, and the finding that the policy
is worst under clean sensing and joins the lead only under degraded sensing is
untouched in both the results and the conclusion.

## Part B — the last provenance gap

The seven context-row cells that had never been re-measured at the current code
state were re-run. **None moved by more than \SI{0.0005}{\meter}, so Table 3 is
unchanged and the gap is closed.**

| cell | table | re-measured | Δ |
|---|---|---|---|
| Plain MPC, nominal | 0.063 | 0.0628 | 0.0002 |
| Plain MPC, gust | 0.142 | 0.1425 | 0.0005 |
| Plain MPC, payload | 0.137 | 0.1371 | 0.0001 |
| Plain MPC, ground | 0.055 | 0.0545 | 0.0005 |
| DATT-L1, gust | 0.066 | 0.0657 | 0.0003 |
| DATT-L1, payload | 0.053 | 0.0531 | 0.0001 |
| DATT-L1, ground | 0.049 | 0.0486 | 0.0004 |

Plain MPC under wind was verified in round 2 (0.196, exact), so all five
plain-MPC cells are now current. Two cells were not on the request's list and
remain from their original measurement: **DATT-L1 nominal (0.048) and DATT-L1
wind (0.050)**. Given that its other three cells reproduced to the fourth
decimal, the risk is negligible, but the statement "every cell of Table 3 is
current" is not yet literally true.

## Page arithmetic, honestly

| source | saving |
|---|---|
| 489 body words at ~650 words/page | ~0.75 |
| Fig. 6 deleted (incl. caption) | ~0.37 |
| deployment tabular removed | ~0.22 |
| Fig. 3 narrowed to $0.8\linewidth$ | ~0.17 |
| two display equations removed | ~0.13 |
| **total** | **~1.6 pages** |

Against the round-3 starting point of 15–16 real SPIE pages that lands at
**≈ 14**, not 10. The gap is not in the execution of the cuts — it is in their
budgeted sizes: cuts 1, 2, 3 and 7 were costed on the assumption that their
words were restatement, and for the most part they are not.

**Not executed, because they are not on the list.** The remaining ~4 pages would
have to come from structural decisions, in rough order of value per page:

1. **Merge Tables 2 and 3.** Table 3's `nominal` column is Table 2's `normal`
   column, printed twice. One table with slow/normal/fast plus the four
   disturbances removes a caption, a header and six duplicated cells: ~0.3 page,
   no information lost. This is the one I would take first, and it is pure
   de-duplication rather than a cut.
2. **Drop the hardware subsection** (~544 words + its share of §4.4's reserved
   space): ~0.9 page. The author explicitly chose to keep it and pay elsewhere,
   so this is listed only for completeness.
3. **Drop Fig. 2** (~0.59 page). It carries the "we reproduce the published
   error signature" check that licenses the benchmark, so this costs a real
   argument.
4. **Recommendation table to prose** (~0.45 page). Seven rows of wrapped text;
   the condition-indexed advice survives as a paragraph, the compute column
   would have to move into the text that already cites it.
5. **Lesson 1 (67 words)** is a one-paragraph summary of §4.2 and could be folded
   into that section's closing sentence.

Taking 1, 4 and 5 would reach ~13 pages without touching a result; reaching 10
needs 2 or 3.

## Verification

- Static checks after every cut: braces balanced in all seven `.tex` files,
  every `tabular` row matches its column spec, all `\includegraphics` targets
  exist, all labels resolve (30 after Fig. 6's removal, was 33), no `\tbd` or
  `\figplaceholder` in content files.
- Figures regenerated; the default set is now four (fig6 on request only).
- **Not verified: the compiled page count.** No LaTeX toolchain is installed
  here and `spie.cls` is absent, so the ~14-page figure above is arithmetic on
  measured word counts and measured float geometry, not a build. The round-3
  note says the stub-class build was at 20 pages; re-running it is the check.

## Dangling references and orphaned mentions (Part C.2)

Swept after the cuts; the following were found and fixed in the same commits:

- `Lesson~4` in the methodology (soft start) — replaced by the justification.
- `Fig.~\ref{fig:transient}` — removed with the figure.
- `Lesson~6`/`Lesson~7` cross-references — renumbered to 5/6.
- "seven lessons" / "seven transferable lessons" — now six.
- Falsification target (i) said "the three leading stacks" — now four.

None left. No paragraph begins with "Second," having lost its "First": the
conclusion's methodological-corrections sentence was rewritten as a whole, and
§4.1's "Three observations" list is intact.

## Claims the trim weakened (for the writing pass)

1. **The soft start's motivation is now one clause in the methodology**, where
   before it had a lesson to itself with the misdiagnosis that produced it. The
   fact that the paper *first got this wrong* is no longer stated anywhere — the
   abstract's self-correction pair is now both seed-related. If the writing pass
   wants the "check when the maximum error occurs" procedure back, it needs one
   sentence somewhere, and Lesson 3 is its natural home.
2. **The transient motivation in the introduction now over-promises.** The
   second of the two effects that "motivate the present study" is transients,
   and with Lesson 4 gone the paper delivers one explanatory sentence under
   Table 4 rather than an analysis. Either trim that motivation to variance
   alone, or keep it and accept the asymmetry.
3. **Lesson 5 no longer says what to do about the frame-stacking negative
   result** (recurrence / innovation-variance features). The negative result and
   its mechanism remain; only the recommendation is gone.
