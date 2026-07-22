#!/usr/bin/env bash
# One-time environment setup inside WSL2 Ubuntu (24.04 recommended).
# Usage: ./scripts/setup_env.sh
#
# The venv lives in the WSL filesystem (~/venvs/crazy_track), not on /mnt/c —
# Windows-mounted paths are slow and need the "metadata" automount option
# (see README) for editable installs to work at all.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-$HOME/venvs/crazy_track}"

PYTHON=${PYTHON:-python3}
ver=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
case "$ver" in
  3.11|3.12|3.13) ;;
  *) echo "Need Python >= 3.11 (found $ver). On Ubuntu: sudo apt install python3.12-venv"; exit 1 ;;
esac

if [ ! -d "$VENV" ]; then
  $PYTHON -m venv "$VENV"
fi
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -e "$REPO[sim,train,dev]"

echo
echo "Done. Activate with:  source $VENV/bin/activate"
echo "Sanity check:         python -m pytest tests/"
echo "Preview trajectories: python -m crazy_track.eval.benchmark --preview"
