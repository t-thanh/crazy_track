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
work), and the descriptor tells it when. This is the paper's freestyle
claim in miniature; next steps: more aggressive sequences (multiple flips,
both axes, pitch), cruise sweeps, 3-seed × track table, and only if
closed-form chaining runs out of headroom, a MINCO-style optimizer.
