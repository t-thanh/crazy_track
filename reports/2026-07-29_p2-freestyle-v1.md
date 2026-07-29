# Paper 2 — freestyle v1: gate sequences + traveling flips, zero-shot

**Date:** 2026-07-29 · **Status: v1 COMPLETE — zero-shot 4/4 gates clean +
traveling roll complete**

## What was built

`src/crazy_track/trajectories/freestyle.py` (user direction: freestyle
sequence planning using the lsy_drone_racing gate):

- **`RaceGate`** — lsy_drone_racing geometry, verified against the repo's
  `assets/gate.xml` and track configs: square, 0.72 m outer frame, 0.4 m
  opening, collision extent to ±0.36 m; pose = opening center + yaw,
  pass-through normal = gate-frame +x. Same drone (cf21B_500) and sim
  (crazyflow) as lsy_drone_racing, so their tracks port verbatim.
- **`FreestyleTrajectory`** — closed-form chaining of validated primitives:
  quintic connect segments (the C² family the policy trains on) between
  full boundary states, ops = gate crossings (velocity along the gate
  normal), **traveling ballistic flips**, free-space vias, hover ends.
- **Traveling flip** — the in-place boost/arc/brake primitive generalized
  with a constant horizontal drift velocity. Feasibility is preserved for
  free: thrust is vertical in boost/brake (level attitude leaves horizontal
  velocity untouched) and zero in the arc (conserves it). drift=0 recovers
  the training primitive exactly.
- **`maneuver_descriptor(t)`** on the trajectory + `DATTAcroController`
  extension: the acro4 conditioning descriptor generalizes to multi-window
  sequences (active window, else next upcoming, countdown clipped at 1 s as
  in training).
- **`feasibility_report`** — analytic ref checks: thrust demand ≤ 0.95·TWR·g
  outside arcs, trapezoid peak rate, floor margin, and gate-plane crossing
  discipline (every crossing through the opening with ≥0.07 m margin OR
  fully clear of the frame; the intended crossing must be the former).
- 15 tests (`tests/test_freestyle.py`); suite now 31.

## Demo track

`lsy_level2_freestyle()`: the four level-2 nominal gates (poses verbatim
from `config/level2.toml`) in track order + one traveling roll− (Tb 0.7,
drift (−0.7, −0.35) m/s) between gates 2 and 3, wide-via U-turn into gate
4, hover finish. Cruise 1.5 m/s, duration ~11.2 s. Plan verifies feasible
(max thrust demand 16.8 vs 17.5 limit; peak rate 11.2 vs 11.25 bound).

Two planning lessons already captured in code comments:
1. A direct g3→g4 quintic U-turn clips gate 3's frame (crossing at 0.23 m
   in-plane, inside the 0.20–0.36 collision band) — the via op exists for
   this; the crossing-discipline check catches it analytically.
2. Flip placement must respect downstream gate planes: an entry that lets
   the drift carry the maneuver past gate 3's plane forced the reference to
   double back, and the rolled-out policy smoothed that into flying OVER
   the gate. Plan margin, not just plan feasibility, matters.

## Zero-shot result (acro4.2 s2, `2026-07-29_18-18-41`, run `22-29-12`)

The policy never trained on gates, traveling flips, multi-flip
descriptors, or this track — flips in training were in-place, from hover,
one per episode.

| metric | value |
|---|---|
| gates passed / clean (<0.13 m) | **4/4 / 4/4** (offsets 0.016 / 0.116 / 0.065 / 0.060) |
| traveling roll | **−361.1° — complete** |
| RMSE 3d / max ref dev | 0.138 / 0.319 |
| min z | 0.704 (never near floor) |

The maneuver-conditioned primitive COMPOSES: post-boost the arc is
identical in the drone's frame regardless of drift (relativity does the
work), and the descriptor tells it when.

## 3-seed × 3-track matrix (user-directed expansion, runs `22-42`–`22-43`)

Two more tracks so the suite covers all four flip variants:
**pitch-line** (pitch+ forward flip over the travel direction, then a
roll+ barrel roll about it — TWO flips back-to-back) and **tower-climb**
(climb through short + tall gates, pitch− at the top, REVERSE traversal
back through both gates, the lsy signed-gate-order convention). Both
analytically feasible first-try. All rollouts zero-shot.

| track | seed | gates passed/clean | flips complete | RMSE | max dev | min z |
|---|---|---|---|---|---|---|
| lsy-level2 (roll−) | s0 | 4/4 / 4/4 | 1/1 (−366°) | 0.122 | 0.28 | 0.76 |
| | s1 | 4/4 / 3/4 | 1/1 (−387°) | 0.123 | 0.23 | 0.74 |
| | s2 | 4/4 / 4/4 | 1/1 (−361°) | 0.138 | 0.32 | 0.70 |
| tower-climb (pitch−) | s0 | 4/4 / 4/4 | 1/1 (−372°) | 0.173 | 0.56 | 0.71 |
| | s1 | 4/4 / 2/4 | 1/1 (−382°) | 0.157 | 0.38 | 0.65 |
| | s2 | 4/4 / 4/4 | 1/1 (−368°) | 0.143 | 0.24 | 0.68 |
| pitch-line (pitch+, roll+) | s0 | 2/3 / 2/3 | 1/2 (309°, 380°) | 0.542 | 1.75 | **0.20** |
| | s1 | 3/3 / 2/3 | **0/2** (294°, 274°) | 0.494 | 1.80 | **−0.00** |
| | s2 | 3/3 / 2/3 | **2/2** (395°, 362°) | 0.374 | 0.80 | 0.41 |

**Findings:**
1. **Single-flip freestyle composes on ALL seeds**: 24/24 gates passed and
   6/6 flips complete across lsy-level2 + tower-climb, including reverse
   gate traversal and the pitch− variant. RMSE 0.12–0.17 — barely above
   the plain acro-suite level.
2. **pitch-line is the discriminator**: two flips back-to-back with ~2 s
   between recovery and the next boost. s2 (the cleanest flip seed)
   completes everything; s0 drops its known-weak pitch+ variant (309°)
   and the resulting deviation costs gate 3; s1 completes neither flip
   and grazes the floor (min_z −0.00) before recovering to pass all
   gates. The per-seed flip-eval hierarchy (s2 > s0 > s1) transfers
   directly to freestyle — chaining amplifies, not masks, primitive
   weakness.
3. Traveling context costs the pitch+ variant ~40–20° of rotation vs its
   in-place eval on the weaker seeds (s0 353°→309°, s1 315°→294°), while
   s2 is unaffected (361°→395°/362° — over-rotates slightly instead).

**Paper claim this supports:** freestyle sequences need no new training —
the conditioned primitive + closed-form planning compose zero-shot — and
sequence difficulty is bounded by per-primitive quality, which the
acro4.2 discovery recipe already measures per seed. Improving s1's
pitch+ (the acro4.2 blemish) is the same lever that would fix its
pitch-line run.

## Speed run vs the TUM leaderboard (user question, runs `23-07`–`23-08`)

`lsy-level2-race` track variant: gates only, per-gate speeds (slow-in at
the g1→g2 hairpin), racing-line vias, and a new segment-duration law —
seed guess from distance/Δv, then classical TIME-SCALING per segment until
the quintic's analytic peak thrust demand fits under 17.2 m/s²
(0.95·TWR·g − margin). `race_time` metric = motion onset → actual
last-gate crossing.

Reference sweep: fastest feasible plan is **4.49 s at cruise 3.0** —
higher cruise makes the two U-turns longer (time-scaling), so the
closed-form plan is TWR-limited at ≈4.5 s on this hairpin-heavy track.

Achieved (zero-shot, nominal track, single run):

| cruise | s0 | s1 | s2 |
|---|---|---|---|
| 2.5 | 4.586 (4/4) | 4.624 (4/4) | DNF (g1, 0.218 m) |
| 3.0 | **4.464 (4/4)** | 4.508 (4/4) | DNF (g1) |
| 3.5 | 4.800 (4/4) | DNF | DNF |

Leaderboard (competition branch, level 2): current best **3.419 s**
(100% success), then 4.652 / 4.896 / 5.404; all-time best **3.394 s**
(winter25); summer25 best 4.290. **Our 4.464 s would place 2nd on all
three boards**, ~1.05 s behind the all-time best.

Honest caveats — the protocols differ in both directions: the
leaderboard clock starts with the drone ON THE GROUND (takeoff included,
which costs them time), but level 2 also randomizes gates/dynamics with
a 0.7 m sensor range and requires ≥50% success across randomized runs
(much harder than our nominal, deterministic, full-state single run).

Gap analysis: tracking is NOT the bottleneck — s0's achieved 4.464 s
beats its own 4.49 s reference by corner-cutting. The ~1 s gap to 3.4 s
is PLAN optimality: per-segment time-scaling is conservative (min thrust
demand along the ref never drops below 8 m/s² — a time-optimal plan
would use the full brake envelope). That is precisely the MINCO-style /
time-optimal-optimization upgrade path, now with a measured payoff bound.

Cross-finding: the racing hierarchy INVERTS the flip hierarchy — s0
(weaker flipper) races best; s2 (cleanest flipper) clips gate 1 by 1.8 cm
at every speed. The capacity tradeoff between maneuver precision and
aggressive tracking shows up even within flip-competent seeds.
