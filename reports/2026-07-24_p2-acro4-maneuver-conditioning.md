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
