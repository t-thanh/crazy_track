"""Flip-maneuver evaluation: rotation completeness, position deviation, recovery.

Usage: python -m crazy_track.eval.flip_eval --model <path> --reason "..."
"""

from __future__ import annotations

import argparse

import numpy as np
from scipy.spatial.transform import Rotation as R

from crazy_track.controllers.datt_acro import DATTAcroController
from crazy_track.envs.rollout import make_sim, rollout
from crazy_track.eval.runlog import RunLogger
from crazy_track.trajectories import FlipTrajectory

HOVER = np.array([0.0, 0.0, 1.5])


def flip_metrics(data: dict, traj: FlipTrajectory) -> dict:
    quat, pos, t = data["quat"], data["pos"], data["t"]
    # Total rotation about the flip axis: sum of per-step relative rotations.
    rots = R.from_quat(quat)
    rel = (rots[:-1].inv() * rots[1:]).as_rotvec()
    total_rot = float(np.sum(rel[:, traj.axis]))
    dev = np.linalg.norm(pos - HOVER, axis=1)
    after = t >= traj.t0 + traj.Tf + 1.5  # settled 1.5 s after the flip ends
    return {
        "total_rotation_deg": round(np.degrees(total_rot), 1),
        "rotation_complete": bool(abs(abs(total_rot) - 2 * np.pi) < np.radians(45)),
        "max_pos_dev": round(float(dev.max()), 3),
        "min_z": round(float(pos[:, 2].min()), 3),
        "recovery_err": round(float(dev[after].mean()) if after.any() else np.nan, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()

    log = RunLogger(tag="flip-eval", reason=args.reason,
                    config={"model": args.model, "hover_z": 1.5})
    print(f"Logging to {log.dir}")
    sim = make_sim(control="force_torque")
    for axis, name in ((0, "roll"), (1, "pitch")):
        for direction in (1, -1):
            traj = FlipTrajectory(hover=HOVER, t0=2.0, Tf=0.5, axis=axis,
                                  direction=direction, duration=6.0)
            ctrl = DATTAcroController(args.model, control_freq=100)
            data = rollout(ctrl, traj, control_freq=100, sim=sim)
            m = flip_metrics(data, traj)
            log.log_rollout("datt_acro2", f"{name}{'+' if direction > 0 else '-'}", data, m)
            print(f"flip {name}{'+' if direction > 0 else '-'}: {m}")


if __name__ == "__main__":
    main()
