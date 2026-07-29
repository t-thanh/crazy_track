#!/bin/bash
# acro4.2 chained train -> flip_eval -> suite pipeline. Usage: acro42_pipeline.sh <seed> [<seed> ...]
# Run from Windows: wsl -d Ubuntu-24.04 -- bash -c "tr -d '\r' < /mnt/c/.../scripts/acro42_pipeline.sh | bash -s -- 0 2"
set -o pipefail
source ~/venvs/crazy_track/bin/activate
cd /mnt/c/Users/tient/Documents/GitHub/crazy_track

for SEED in "$@"; do
  echo "=== acro4.2 seed $SEED: training 8M ==="
  LOGFILE="/tmp/acro42_s${SEED}_train.log"
  python -m crazy_track.training.ppo_train --timesteps 8000000 --acro4 --seed "$SEED" \
    --reason "acro4.2 s${SEED}: acro4.1 recipe + rate-feedforward aux reward (+0.5*exp(-|w_cmd-w_ref|/5) in rotation window, commanded-rate trapezoid match) targeting flip DISCOVERY (acro4.1 s1 total refusal)" \
    2>&1 | tee "$LOGFILE" || { echo "TRAIN FAILED seed $SEED"; exit 1; }
  RUN=$(grep -m1 "^Logging to " "$LOGFILE" | awk '{print $3}')
  MODEL="$RUN/datt_ppo_final.zip"
  [ -f "$MODEL" ] || { echo "MODEL MISSING seed $SEED: $MODEL"; exit 1; }
  echo "=== acro4.2 seed $SEED: flip eval ($MODEL) ==="
  python -m crazy_track.eval.flip_eval --model "$MODEL" --ballistic \
    --reason "acro4.2 s${SEED} flip eval: 4 ballistic flip variants, success gate >=3/4 complete at dev<0.75/rec<0.15" \
    || { echo "FLIP EVAL FAILED seed $SEED"; exit 1; }
  echo "=== acro4.2 seed $SEED: suite h ==="
  python -m crazy_track.eval.lissajous_benchmark --controllers "datt_acro:$MODEL" \
    --speeds fast acro --tag "acro42-suite-h-s${SEED}" \
    --reason "acro4.2 s${SEED} horizontal suite: check rate-feedforward aux reward did not dent tracking (target near flip-free v1)" \
    || { echo "SUITE H FAILED seed $SEED"; exit 1; }
  echo "=== acro4.2 seed $SEED: suite v ==="
  python -m crazy_track.eval.lissajous_benchmark --controllers "datt_acro:$MODEL" \
    --speeds normal fast acro --vertical --tag "acro42-suite-v-s${SEED}" \
    --reason "acro4.2 s${SEED} vertical suite: check rate-feedforward aux reward did not dent tracking (target near flip-free v1)" \
    || { echo "SUITE V FAILED seed $SEED"; exit 1; }
  echo "=== acro4.2 seed $SEED: DONE ==="
done
echo "=== acro4.2 pipeline complete for seeds: $* ==="
