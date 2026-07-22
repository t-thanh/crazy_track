"""Figure-5 Lissajous benchmark runner (arXiv:2311.13081, Table III style).

Usage (inside the WSL venv):
    python -m crazy_track.eval.lissajous_benchmark --controllers pid --reason "why this run"
"""

from __future__ import annotations

import argparse
import time

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from crazy_track.envs.rollout import make_sim, rollout
from crazy_track.eval.runlog import RunLogger, tracking_metrics
from crazy_track.trajectories import LissajousTrajectory

N_CYCLES = 2
CONTROL_FREQ = 100


def make_controller(name: str):
    if name == "pid":
        from crazy_track.controllers.pid import PIDController
        return PIDController(control_freq=CONTROL_FREQ)
    if name == "adrc":
        from crazy_track.controllers.adrc import ADRCController
        return ADRCController(control_freq=CONTROL_FREQ)
    if name == "mppi_l1":
        from crazy_track.controllers.mppi_l1 import MPPIL1Controller
        return MPPIL1Controller(control_freq=CONTROL_FREQ)
    if name == "mpc":
        from crazy_track.controllers.mpc import MPCController
        return MPCController(control_freq=CONTROL_FREQ)
    if name.startswith("datt:"):
        from crazy_track.controllers.datt import DATTPolicyController
        return DATTPolicyController(name.split(":", 1)[1], control_freq=CONTROL_FREQ)
    raise ValueError(f"Unknown controller: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controllers", nargs="+", default=["pid"])
    parser.add_argument("--speeds", nargs="+", default=["slow", "normal", "fast"])
    parser.add_argument("--reason", required=True, help="why this run is being made (logged)")
    parser.add_argument("--tag", default="lissajous")
    args = parser.parse_args()

    log = RunLogger(
        tag=args.tag, reason=args.reason,
        config={"controllers": args.controllers, "speeds": args.speeds,
                "n_cycles": N_CYCLES, "control_freq": CONTROL_FREQ,
                "drone": "cf21B_500", "dynamics": "first_principles"},
    )
    print(f"Logging to {log.dir}")
    sim = make_sim()

    fig, axes = plt.subplots(len(args.controllers), len(args.speeds),
                             figsize=(5 * len(args.speeds), 4.4 * len(args.controllers)),
                             squeeze=False)
    for ci, cname in enumerate(args.controllers):
        for si, speed in enumerate(args.speeds):
            traj = LissajousTrajectory.from_speed(speed, n_cycles=N_CYCLES)
            ctrl = make_controller(cname)
            t0 = time.time()
            data = rollout(ctrl, traj, control_freq=CONTROL_FREQ, sim=sim)
            wall = time.time() - t0
            metrics = tracking_metrics(data["pos"], data["ref_pos"], data["t"])
            metrics["wall_time_s"] = round(wall, 1)
            log.log_rollout(cname, speed, data, metrics)
            print(f"{cname:10s} {speed:7s} rmse_3d={metrics['rmse_3d']:.3f} m "
                  f"rmse_xy={metrics['rmse_xy']:.3f} m max={metrics['max_err']:.3f} m "
                  f"({wall:.0f}s wall)")

            ax = axes[ci][si]
            ax.plot(data["ref_pos"][:, 0], data["ref_pos"][:, 1], "k-", lw=1, label="reference")
            ax.plot(data["pos"][:, 0], data["pos"][:, 1], lw=1, label=cname)
            ax.set(title=f"{cname} | {speed} (T={LissajousTrajectory.SPEEDS[speed]}s) "
                         f"RMSE={metrics['rmse_3d']:.3f}m",
                   xlabel="x [m]", ylabel="y [m]", aspect="equal")
            ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(log.dir / "tracking_xy.png", dpi=150)
    print(f"Saved plot to {log.dir / 'tracking_xy.png'}")


if __name__ == "__main__":
    main()
