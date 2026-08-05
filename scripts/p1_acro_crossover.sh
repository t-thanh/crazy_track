#!/bin/bash
# Paper-1 benchmark crossover: run the paper-2 ACRO (CTBR) policies through the
# paper-1 condition matrix. ADDITIVE ONLY - tag prefix `p1x-` is disjoint from
# paper 1's `ms-`/`mst-` aggregation, so `aggregate_seeds --prefix ms-|mst-`
# (the paper-1 reproduction path) is bit-for-bit unaffected.
# Protocol copied from the paper-1 cells (see reports 2026-07-23 / 2026-08-04):
#   nominal   : --speeds slow normal fast
#   lighthouse: --speeds normal fast --sensor lighthouse
#   lh+wind   : --speeds normal --disturbance wind_const --sensor lighthouse
#   disturb   : --speeds normal --disturbance <X>
# Learned policies are reported over 3 TRAINING seeds at fixed eval seed 0.
set -o pipefail
source ~/venvs/crazy_track/bin/activate
cd /mnt/c/Users/tient/Documents/GitHub/crazy_track

A42_S0=results/2026-07-29_16-24-22-b_datt-train/datt_ppo_final.zip
A42_S1=results/2026-07-29_16-24-22_datt-train/datt_ppo_final.zip
A42_S2=results/2026-07-29_18-18-41_datt-train/datt_ppo_final.zip
V1=results/2026-07-22_18-58-56_datt-train/datt_ppo_final.zip

run_cell () {  # $1 model  $2 tag  $3... benchmark args
  local model="$1"; local tag="$2"; shift 2
  python -m crazy_track.eval.lissajous_benchmark \
    --controllers "datt_acro:$model" --tag "$tag" "$@" \
    --reason "paper-1 crossover (ADDITIVE, paper-1 results untouched): acro CTBR policy on the paper-1 benchmark cell '${tag}' - does the acrobatic controller hold up on the fig-8 benchmark it was not tuned for" \
    || { echo "FAILED $tag"; exit 1; }
}

for spec in "s0:$A42_S0" "s1:$A42_S1" "s2:$A42_S2" "v1:$V1"; do
  SEED_NAME="${spec%%:*}"; MODEL="${spec#*:}"
  if [ "$SEED_NAME" = "v1" ]; then FAM=acrov1; SFX=-s0; else FAM=acro42; SFX="-${SEED_NAME}"; fi
  echo "=== $FAM $SEED_NAME ==="
  run_cell "$MODEL" "p1x-${FAM}-nom${SFX}"     --speeds slow normal fast
  run_cell "$MODEL" "p1x-${FAM}-lh${SFX}"      --speeds normal fast --sensor lighthouse
  run_cell "$MODEL" "p1x-${FAM}-lhwind${SFX}"  --speeds normal --disturbance wind_const --sensor lighthouse
  run_cell "$MODEL" "p1x-${FAM}-wind${SFX}"    --speeds normal --disturbance wind_const
  run_cell "$MODEL" "p1x-${FAM}-gust${SFX}"    --speeds normal --disturbance wind_gust
  run_cell "$MODEL" "p1x-${FAM}-payload${SFX}" --speeds normal --disturbance payload
  run_cell "$MODEL" "p1x-${FAM}-ground${SFX}"  --speeds normal --disturbance ground
done
echo "=== crossover matrix complete ==="
