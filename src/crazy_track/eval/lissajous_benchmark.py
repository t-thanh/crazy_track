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
    if name == "xadapt":
        from crazy_track.controllers.xadapt import XAdaptPIDController
        return XAdaptPIDController(control_freq=500)
    if name.startswith("datt_acro:"):
        from crazy_track.controllers.datt_acro import DATTAcroController
        return DATTAcroController(name.split(":", 1)[1], control_freq=CONTROL_FREQ)
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
    parser.add_argument("--disturbance", default="none",
                        choices=["none", "wind_const", "wind_gust", "ground", "payload"])
    parser.add_argument("--sensor", default="none", choices=["none", "lighthouse"])
    parser.add_argument("--vertical", action="store_true",
                        help="figure-8 in the x-z plane (acro benchmark)")
    args = parser.parse_args()

    from crazy_track.disturbances import SCENARIOS
    disturbance = SCENARIOS[args.disturbance]() if args.disturbance != "none" else None
    sensor = None
    if args.sensor == "lighthouse":
        from crazy_track.sensors import LighthouseSensor
        sensor = LighthouseSensor(control_freq=CONTROL_FREQ)
    traj_z = 0.08 if args.disturbance == "ground" else 1.0  # IGE needs low altitude
    if args.tag == "lissajous":
        if args.disturbance != "none":
            args.tag = f"lissajous-{args.disturbance}"
        if args.sensor != "none":
            args.tag += f"-{args.sensor}"

    log = RunLogger(
        tag=args.tag, reason=args.reason,
        config={"controllers": args.controllers, "speeds": args.speeds,
                "n_cycles": N_CYCLES, "control_freq": CONTROL_FREQ,
                "drone": "cf21B_500", "dynamics": "first_principles",
                "disturbance": args.disturbance, "sensor": args.sensor, "traj_z": traj_z},
    )
    print(f"Logging to {log.dir}")
    acro = [c.startswith("datt_acro") for c in args.controllers]
    xadapt = [c == "xadapt" for c in args.controllers]
    if (any(acro) and not all(acro)) or (any(xadapt) and not all(xadapt)):
        raise SystemExit("datt_acro (force_torque) / xadapt (rotor_vel) cannot be mixed "
                         "with attitude-mode controllers in one run — invoke separately.")
    mode = "force_torque" if any(acro) else "rotor_vel" if any(xadapt) else "attitude"
    ctrl_freq = 500 if any(xadapt) else CONTROL_FREQ  # xadapt runs at its training rate
    sim = make_sim(control=mode)

    fig, axes = plt.subplots(len(args.controllers), len(args.speeds),
                             figsize=(5 * len(args.speeds), 4.4 * len(args.controllers)),
                             squeeze=False)
    seen: dict[str, int] = {}
    for ci, cspec in enumerate(args.controllers):
        cname = cspec.split(":")[0]  # file/label-safe name (model paths follow the colon)
        seen[cname] = seen.get(cname, 0) + 1
        if seen[cname] > 1:  # avoid npz/row collisions when comparing same-type models
            cname = f"{cname}{seen[cname]}"
        for si, speed in enumerate(args.speeds):
            traj = LissajousTrajectory.from_speed(speed, n_cycles=N_CYCLES, z=traj_z,
                                                  vertical=args.vertical)
            ctrl = make_controller(cspec)
            t0 = time.time()
            data = rollout(ctrl, traj, control_freq=ctrl_freq, sim=sim,
                           disturbance=disturbance, sensor=sensor)
            wall = time.time() - t0
            metrics = tracking_metrics(data["pos"], data["ref_pos"], data["t"])
            metrics["wall_time_s"] = round(wall, 1)
            log.log_rollout(cname, speed, data, metrics)
            print(f"{cname:10s} {speed:7s} rmse_3d={metrics['rmse_3d']:.3f} m "
                  f"rmse_xy={metrics['rmse_xy']:.3f} m max={metrics['max_err']:.3f} m "
                  f"({wall:.0f}s wall)")

            # vertical fig-8s live in the x-z plane; horizontal ones in x-y
            k, axis_name = (2, "z") if args.vertical else (1, "y")
            ax = axes[ci][si]
            ax.plot(data["ref_pos"][:, 0], data["ref_pos"][:, k], "k-", lw=1, label="reference")
            ax.plot(data["pos"][:, 0], data["pos"][:, k], lw=1, label=cname)
            ax.set(title=f"{cname} | {speed} (T={LissajousTrajectory.SPEEDS[speed]}s) "
                         f"RMSE={metrics['rmse_3d']:.3f}m",
                   xlabel="x [m]", ylabel=f"{axis_name} [m]", aspect="equal")
            ax.legend(fontsize=8)
    fig.tight_layout()
    plot_name = "tracking_xz.png" if args.vertical else "tracking_xy.png"
    fig.savefig(log.dir / plot_name, dpi=150)
    print(f"Saved plot to {log.dir / plot_name}")


if __name__ == "__main__":
    main()
