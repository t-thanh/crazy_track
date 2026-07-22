from __future__ import annotations

import numpy as np

from crazy_track.controllers.base import Controller
from crazy_track.controllers.utils import acc2attitude
from crazy_track.trajectories import Trajectory


class ADRCController(Controller):
    """Active Disturbance Rejection Control (translational, reduced-order ESO).

    Since velocity is measured, a 2nd-order ESO per axis estimates the total
    disturbance acceleration sigma (unmodeled drag, attitude-loop lag, wind):

        v_hat' = u + sigma_hat + l1 (v - v_hat)     l1 = 2*w_obs
        sigma_hat' =            l2 (v - v_hat)      l2 = w_obs^2

    where u is the commanded acceleration. Control law cancels sigma:
        a_cmd = ref_acc + kp*e + kd*edot - sigma_hat

    sigma_hat is saturated: an unsaturated estimate feeds back its own
    actuation lag during aggressive transients and destabilizes the loop
    (observed with a full-order position ESO at w_obs=25 — RMSE > 5 m).
    """

    def __init__(self, kp: float = 16.0, kd: float = 8.0, omega_obs: float = 10.0,
                 sigma_max: float = 3.0, control_freq: int = 100):
        self.kp, self.kd = kp, kd
        self.l1, self.l2 = 2 * omega_obs, omega_obs**2
        self.sigma_max = sigma_max
        self.dt = 1.0 / control_freq
        self._traj: Trajectory | None = None
        self._v_hat = np.zeros(3)
        self._sigma = np.zeros(3)
        self._u_prev = np.zeros(3)

    def reset(self, trajectory: Trajectory) -> None:
        self._traj = trajectory
        self._v_hat = np.zeros(3)
        self._sigma = np.zeros(3)
        self._u_prev = np.zeros(3)

    def act(self, state: np.ndarray, t: float) -> np.ndarray:
        pos, vel, quat = state[:3], state[3:6], state[6:10]

        e_v = vel - self._v_hat
        self._v_hat += self.dt * (self._u_prev + self._sigma + self.l1 * e_v)
        self._sigma = np.clip(self._sigma + self.dt * self.l2 * e_v,
                              -self.sigma_max, self.sigma_max)

        a_cmd = (
            self._traj.acc(t)
            + self.kp * (self._traj.pos(t) - pos)
            + self.kd * (self._traj.vel(t) - vel)
            - self._sigma
        )
        self._u_prev = a_cmd
        return acc2attitude(a_cmd, quat)
