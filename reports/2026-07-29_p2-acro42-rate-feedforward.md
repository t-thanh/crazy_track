# Paper 2 — acro4.2: rate-feedforward auxiliary reward (flip discovery)

**Date:** 2026-07-29 · **Code:** `ffd9e91` · **Status: RUNNING — results pending**

## Problem

acro4.1 verdict (report 2026-07-24): shaping after discovery and general
acro-suite tracking are both solved; flip **discovery** is the last open
problem. Same recipe: s0 4/4 (best flip policy of the project), s2 3/4,
**s1 0/4 total refusal** (±2° through the rotation window for 8M steps while
tracking the ballistic arc — and posting the best suite numbers). The dense
rotation-progress term is dense in **state** space: at total refusal the
policy never produces the body rotation that would generate the gradient, so
refusal is a self-consistent optimum reachable by unlucky exploration.

## Intervention

Auxiliary reward, dense in **action** space (where exploration noise lives):

    + 0.5 * exp(-|w_cmd - w_ref| / 5)   per step, rotation window only

- `w_cmd` — commanded body rate about the maneuver axis (the CTBR action,
  clipped, × RATE_MAX), NOT the achieved rate. The Gaussian policy explores
  in action space every step, so this term has nonzero gradient at total
  refusal — the state never needs to move for the policy to be pulled toward
  emitting rotation commands.
- `w_ref` — analytic trapezoid rate profile of `BallisticFlipTrajectory`
  (blend 0.2, peak 2π/(0.8·Tb) ≈ 11.2 rad/s at Tb=0.7; verified: integrates
  to exactly 2π, matches the derivative of `att_ref_rotvec`).
- Magnitude +0.5 peak (vs ~2.0 tracking terms in-window) — small enough that
  post-discovery behavior stays governed by the acro4.1 terms that produced
  clean flips; /5 rad/s decay is wide enough to give signal from w_cmd = 0
  (exp(-11.2/5) ≈ 0.11 ≠ 0, and any sampled rotation command in the right
  direction is immediately better).
- No annealing (constant coefficient) — chosen over annealing for simplicity;
  the term rewards the *reference-consistent* rate, so at convergence it is
  aligned with, not competing against, the tracking objective.

Same `--acro4` flag; distinguished from acro4.1 by git hash ≥ `ffd9e91`
(acro4.1 precedent). Obs layout unchanged (52-dim).

Pre-launch verification: 16 Windows tests pass; 40k-step WSL smoke run; a
single-step deterministic check (window shifted onto step 1 at u=0.5):
reward gap matching-vs-zero command +0.433 (theoretical aux gap +0.444),
ordering match > zero > anti-rotation.

## Runs

3 seeds × 8M, chained train→flip_eval→suite per seed
(`scripts/acro42_pipeline.sh`; stream I = seeds 0,2, stream J = seed 1).
Launched 2026-07-29 16:24. Train run dirs: `2026-07-29_16-24-22[-b]_datt-train`
(s0/s1; s2 follows s0 on stream I).

**Success gate:** ≥3/4 completions on ALL 3 seeds at dev<0.75 / rec<0.15;
suite near flip-free v1 (`2026-07-22_18-58-56`: h 0.123/0.322,
v 0.122/0.196/0.349).

## Results — flips (4 variants per seed)

_s0/s2 PENDING (stream I)._ Cell format: total rotation ° / max ref dev m /
recovery err m; ✓ = complete (|rot−360°| < 45°).

| seed | roll+ | roll− | pitch+ | pitch− | completions |
|------|-------|-------|--------|--------|-------------|
| 0    | ✓ 362/0.69/0.04 | ✓ −347/0.27/0.04 | ✓ 353/0.43/0.04 | ✓ −357/0.53/0.05 | **4/4** |
| 1    | ✓ 333/0.96/0.06 | ✓ −361/0.31/0.03 | ✗ 315/0.39/0.06 | ✓ −326/0.29/0.03 | **3/4** |
| 2    |       |       |        |        | /4          |

Reference (acro4.1): s0 4/4, s1 0/4, s2 3/4.

**s0: 4/4, every variant within the dev<0.75/rec<0.15 gate** (model
`2026-07-29_16-24-22-b_datt-train`, flip eval `18-18-04`, min_z ≥ 1.65 —
no floor). Matches acro4.1 s0's 4/4; the aux reward did not disturb the
already-working seed.

**s1 (the acro4.1 total refuser) discovers flips: 0/4 → 3/4** (model
`2026-07-29_16-24-22_datt-train`, flip eval `18-17-56`). min_z ≥ 1.92 (no
floor). Two caveats: roll+ completes at dev 0.96 (above the 0.75 gate; the
other three variants sit at 0.29–0.39), and pitch+ misses the completion
threshold by 0.2° (314.8° vs 315°) — a near-miss, not a refusal.

## Results — suite

_s0/s2 PENDING._ RMSE 3d; v1 flip-free reference h 0.123/0.322,
v 0.122/0.196/0.349.

| seed | h fast | h acro | v normal | v fast | v acro |
|------|--------|--------|----------|--------|--------|
| 0    | 0.128  | 0.335  | 0.131    | 0.205  | 0.435  |
| 1    | 0.131  | 0.373  | 0.132    | 0.194  | 0.362  |
| 2    |        |        |          |        |        |

s1 suite (`18-18-09` h, `18-18-21` v): near v1 everywhere; mild acro-tier
dent (+0.05 h-acro, +0.01 v-acro) — the same contained capacity tradeoff
flip-competent seeds showed in acro4.1. Notably s1's acro4.1 "best suite"
(v normal 0.099) degrades only to 0.132 while gaining flips.

## Verdict

_PENDING_
