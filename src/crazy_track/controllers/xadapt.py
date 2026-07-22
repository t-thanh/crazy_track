"""xadapt_ctrl (muellerlab) as the low-level layer under our PID position loop.

'A Learning-based Quadcopter Controller with Extreme Adaptation' (Zhang et al.,
T-RO 2025). AdapLowLevelControl consumes [omega, proper_acc_z, cmd_bodyrates,
cmd_mass_norm_thrust] + 100-step history, outputs motor speeds (rad/s,
normalized by max). We convert to RPM for crazyflow's rotor_vel mode.

Stack: PID position (this file) -> attitude P -> CTBR -> xadapt -> motors.
Run rollouts at 500 Hz (their training timescale; history stats matter).
Requires: onnxruntime + the cloned repo (XADAPT_PATH, default ~/xadapt_ctrl).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

from crazy_track.controllers.base import Controller
from crazy_track.controllers.utils import GRAVITY, MASS, RPY_MAX, acc2attitude
from crazy_track.trajectories import Trajectory

RAD_S_TO_RPM = 60.0 / (2 * np.pi)
# cf21B: vmotor2rpm ~ [2938, 6001] (affine in V); ~4V full battery -> ~27k RPM
MAX_MOTOR_RAD_S = 2800.0


class _QuadState:
    __slots__ = ("att", "omega", "proper_acc", "cmd_collective_thrust", "cmd_bodyrates")


class XAdaptPIDController(Controller):
    def __init__(self, kp: float = 16.0, kd: float = 8.0, ki: float = 4.0,
                 kp_att: float = 8.0, control_freq: int = 500, motor_order=(0, 1, 2, 3)):
        self.ki, self.int_max = ki, 1.0
        self._int_err = np.zeros(3)
        path = os.environ.get("XADAPT_PATH", str(Path.home() / "xadapt_ctrl"))
        if path not in sys.path:
            sys.path.insert(0, path)
        from xadapt_controller.controller import AdapLowLevelControl

        self.ll = AdapLowLevelControl()
        self.ll.set_max_motor_spd(MAX_MOTOR_RAD_S)
        self.kp, self.kd, self.kp_att = kp, kd, kp_att
        self.dt = 1.0 / control_freq
        self.motor_order = list(motor_order)  # crazyflow motor index for each xadapt output
        self._traj: Trajectory | None = None
        self._prev_vel = np.zeros(3)

    def reset(self, trajectory: Trajectory) -> None:
        from xadapt_controller.controller import AdapLowLevelControl

        self._traj = trajectory
        self._prev_vel = np.zeros(3)
        self._int_err = np.zeros(3)
        self.ll = AdapLowLevelControl()  # fresh history buffers per episode
        self.ll.set_max_motor_spd(MAX_MOTOR_RAD_S)

    def act(self, state: np.ndarray, t: float) -> np.ndarray:
        pos, vel, quat, omega = state[:3], state[3:6], state[6:10], state[10:13]
        # Outer PID -> desired acceleration -> thrust magnitude + attitude
        err = self._traj.pos(t) - pos
        self._int_err = np.clip(self._int_err + err * self.dt, -self.int_max, self.int_max)
        a_cmd = (self._traj.acc(t) + self.kp * err + self.ki * self._int_err
                 + self.kd * (self._traj.vel(t) - vel))
        rpyt = acc2attitude(a_cmd, quat)
        # Attitude P loop (body frame) -> commanded body rates
        rot = R.from_quat(quat)
        rot_des = R.from_euler("xyz", [rpyt[0], rpyt[1], rpyt[2]])
        e_rotvec = (rot.inv() * rot_des).as_rotvec()
        cmd_rates = np.clip(self.kp_att * e_rotvec, -10.0, 10.0)

        # Proper acceleration (specific force) along body z, measured
        acc = (vel - self._prev_vel) / self.dt
        self._prev_vel = vel.copy()
        proper = rot.inv().apply(acc + np.array([0.0, 0.0, GRAVITY]))

        s = _QuadState()
        s.att = quat
        s.omega = omega.astype(np.float32)
        s.proper_acc = proper.astype(np.float32)
        s.cmd_bodyrates = cmd_rates.astype(np.float32)
        s.cmd_collective_thrust = np.float32(rpyt[3] / MASS)  # mass-normalized

        spd = self.ll.run(s)  # rad/s in xadapt motor order
        rpm = np.clip(spd * RAD_S_TO_RPM, 0.0, MAX_MOTOR_RAD_S * RAD_S_TO_RPM)
        return rpm[self.motor_order].astype(np.float32)
