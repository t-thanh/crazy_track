#!/usr/bin/env python
"""Per-control-step compute cost for each stack in the pool.

Times controller.act() alone -- no simulator, no logging -- so the number is
the control law's cost rather than a harness episode time. Run on an idle
machine; report the median.

    python scripts/bench_control_step.py [--n 200]
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from crazy_track.eval.lissajous_benchmark import make_controller
from crazy_track.trajectories import LissajousTrajectory

POOL = [
    ("PID + feedforward", "pid"),
    ("ADRC", "adrc"),
    ("MPPI + L1", "mppi_l1"),
    ("Offset-free MPC", "mpc_offsetfree"),
    ("ADRC + xadapt", "xadapt_adrc"),
    ("DATT-Asym", "datt:results/2026-07-22_17-32-52_datt-train/datt_ppo_final.zip"),
    ("Plain MPC", "mpc"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="timed act() calls per stack")
    args = ap.parse_args()

    traj = LissajousTrajectory(cycle_time=5.5, n_cycles=2, z=1.0)
    # a plausible mid-flight state: on the reference, moving along it
    state = np.concatenate([traj.pos(1.0), traj.vel(1.0),
                            np.array([0.0, 0.0, 0.0, 1.0]), np.zeros(3)])

    print(f"{'controller':>18s}  {'median':>9s}  {'p90':>9s}   (per act() call)")
    print("-" * 58)
    for label, spec in POOL:
        ctrl = make_controller(spec)
        ctrl.reset(traj)
        for i in range(10):                       # warm up JIT / solver caches
            ctrl.act(state, 1.0 + 0.01 * i)
        dt = []
        for i in range(args.n):
            t = 1.0 + 0.01 * i
            t0 = time.perf_counter()
            ctrl.act(state, t)
            dt.append(time.perf_counter() - t0)
        d = np.asarray(dt) * 1e3                  # ms
        print(f"{label:>18s}  {np.median(d):7.3f} ms  {np.percentile(d, 90):7.3f} ms")
    print("\nControl period is 10 ms at 100 Hz (2 ms for the 500 Hz inner loop).")


if __name__ == "__main__":
    main()
