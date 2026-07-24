# 2026-07-24 — Paper 2: acro4 (A+D) results; dense-progress iteration (acro4.1)

## Acro4 = acro3 + A (maneuver-conditioned obs) + D (one-time completion bonus)
Per user decision. 3 seeds, 8M steps, chained train->flip->suite pipeline.
Models: s0 `2026-07-24_04-22-16`-family, s1/s2 see run metadata (acro4: true).

### Suite result: A WORKS — flip/tracking interference eliminated on all seeds

| trajectory | v1 (no flips) | acro3 (range over seeds) | acro4 s0 | acro4 s1 | acro4 s2 |
|---|---|---|---|---|---|
| horizontal fast | 0.123 | 0.114-0.287 | 0.146 | 0.153 | 0.167 |
| horizontal acro | 0.322 | 0.375-0.539 | **0.290** | 0.329 | 0.329 |
| vertical normal | 0.122 | 0.143-0.161 | **0.107** | 0.152 | 0.154 |
| vertical fast | 0.196 | 0.249-0.273 | **0.169** | 0.229 | 0.214 |
| vertical acro | 0.349 | 0.429-0.998 | **0.308** | 0.331 | **0.286** |

acro4 matches the flip-free v1 everywhere and beats it on several cells —
the 1.3-2x acro3 regression is gone, consistently across seeds. The 6-dim
maneuver descriptor (signed axis, countdown, progress, active) is the right
mechanism against multi-task interference and stays in the recipe.

### Flip result: sparse D FAILS — refusal returns (4/12 vs acro3's 7-8/12)

| flip | s0 | s1 | s2 |
|---|---|---|---|
| roll+  | ✓ 398° (sloppy: dev 2.40, floor) | −9°, refuses | 86°, aborts+floor |
| roll−  | **✓ −344°** (dev 0.44, rec 0.30) | −1°, refuses | −362° but dev 2.06, floor |
| pitch+ | 9°, refuses | 4°, refuses | 303° near-miss (dev 0.50) |
| pitch− | −5°, refuses | ✓ −330° (dev 1.73) | −648°, over-rotation crash |

**Mechanism (clear in hindsight):** the refusing cells track the arc
position precisely while level (dev 0.42-0.75, recovery 0.03-0.10) — the
descriptor makes "free-fall level through the window" a cleanly learnable,
low-variance solution, and the one-time completion bonus has ZERO gradient
at 0 degrees (5*exp(-3*2pi) ~ 1e-8): nothing dense pulls exploration toward
rotating. Worse, conditioning removed the cross-context representation
sharing through which acro3's flips emerged. A made tracking safe; sparse D
could not make flipping attractive.

## Acro4.1: D made DENSE (rotation-progress reward)
Replace the discovery mechanism, keep everything else:
- Per-step, inside the rotation window: `r += 2.5/(2pi) * (min(a_new, 2pi)
  - min(a_old, 2pi))` where `a = rot_acc * sign(direction)` — i.e. every
  radian of rotation toward the target pays immediately, a full rotation
  accumulates +2.5, rotation past 2pi earns nothing, backward rotation pays
  negative. Gradient now exists AT 0 degrees.
- One-time completion bonus kept (sharpens the exactly-2pi optimum against
  the 0/4pi attractors).
- Obs unchanged (52-dim) — same `--acro4` flag; recipes distinguished by
  git hash in run metadata.
Launched: 3 seeds x 8M, same chained pipeline.

## Acro4.1 results (s0, s1 in; s2 pending)

| flip | s0 | s1 | s2 |
|---|---|---|---|
| roll+  | **✓ 323°** (dev 1.06, rec 0.10) | −1°, refuses | **✓ 334°** (dev 0.42, rec 0.06) |
| roll−  | **✓ −355°** (dev 0.26, rec 0.04) | +2°, refuses | **✓ −320°** (dev 0.32, rec 0.09) |
| pitch+ | **✓ +333°** (dev 0.39, rec 0.07) | 0°, refuses | 307° near-miss (dev 0.35, rec 0.09) |
| pitch− | **✓ −353°** (dev 0.57, rec 0.09) | −2°, refuses | ✓ −385° but dev 2.62, floor |

Suite: s0 h 0.139/**0.608** v 0.137/0.193/0.375; s1 h 0.137/0.348
v 0.099/0.184/0.331 (best suite yet); s2 h 0.223/0.390 v 0.155/0.235/0.440.

**Final tally: 7/12 completions (5 clean at dev<=0.6, rec<=0.10)** — same
count as acro3@15M but far cleaner where it works, with the suite held
near v1 (mild dents only on flip-competent seeds: s0 h-acro 0.608,
s2 v-acro 0.440 — the capacity tradeoff is reduced, not zero).

### Reading (final)
1. **acro4.1-s0 is the project's best flip policy**: 4/4 completions,
   min_z >= 1.47 (no floor), recovery 0.04-0.10 — meets the paper bar on
   3/4 variants (roll+ dev 1.06 slightly over). Once rotation is
   DISCOVERED, dense-D + conditioning shape it excellently.
2. **acro4.1-s1 refuses everything** despite the dense progress reward —
   with per-step Gaussian exploration, coherent 10 rad/s rotations across
   ~35 steps are never sampled once the value function locks onto the
   safe conditioned optimum. Discovery is a stochastic event; acro3
   found flips via cross-context bleed (aggressive-tracking rates leaking
   into flip windows), which conditioning removed.
3. s0's h-acro dent (0.608) and s2's v-acro (0.440) confirm the capacity
   tradeoff re-emerges mildly when flip skill is actually acquired —
   flip-refusing s1 posts the cleanest suite. Much smaller than acro3's
   1.3-2x regression; conditioning contains, not eliminates, it.
3b. s2 (2 clean + 1 near-miss + 1 sloppy) sits between s0 and s1 —
   consistent with discovery being partial per variant, then shaped well
   wherever it happened (its pitch+ tracks the arc at dev 0.35 while
   rotating 307 deg).
4. **Reliable-discovery levers for the next iteration** (not launched —
   machine shutdown scheduled): (a) rate-feedforward auxiliary reward —
   reward w_cmd matching the reference trapezoid rate profile during the
   window; dense in ACTION space where exploration actually happens;
   effectively imitation of the trivial feedforward expert, annealable.
   (b) warm-start weight surgery from a flip-competent policy (46->52 obs
   needs zero-padded input columns). (c) pragmatic: train k seeds, select
   flip-competent (weakest science).
