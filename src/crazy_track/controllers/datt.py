from __future__ import annotations

import numpy as np

from crazy_track.controllers.base import Controller
from crazy_track.controllers.utils import RPY_MAX, THRUST_MAX, THRUST_MIN
from crazy_track.envs.datt_env import WINDOW, WINDOW_DT
from crazy_track.trajectories import Trajectory


class DATTPolicyController(Controller):
    """Runs a trained DATT PPO policy (obs/action conventions from datt_env)."""

    def __init__(self, model_path: str, control_freq: int = 100):
        from stable_baselines3 import PPO

        self.model = PPO.load(model_path, device="cpu")
        self._t_offsets = WINDOW_DT * np.arange(1, WINDOW + 1)
        self._traj: Trajectory | None = None
        # v3 models (43-dim obs) expect the L1 disturbance estimate appended.
        self.v3 = int(np.prod(self.model.observation_space.shape)) == 3 + 3 + 4 + 3 * WINDOW + 3
        if self.v3:
            from crazy_track.controllers.l1 import L1Estimator

            self.l1 = L1Estimator(mass=0.04338, n=1, dt=1.0 / control_freq)
        self._last_thrust = 0.04338 * 9.81

    def reset(self, trajectory: Trajectory) -> None:
        self._traj = trajectory
        if self.v3:
            self.l1.reset()
            self._last_thrust = 0.04338 * 9.81

    def act(self, state: np.ndarray, t: float) -> np.ndarray:
        pos, vel, quat = state[:3], state[3:6], state[6:10]
        win = self._traj.pos(t + self._t_offsets) - pos
        parts = [self._traj.pos(t) - pos, vel, quat, win.ravel()]
        if self.v3:
            sigma = self.l1.update(vel, quat, np.array([self._last_thrust]))
            parts.append(sigma[0])
        obs = np.concatenate(parts).astype(np.float32)
        a, _ = self.model.predict(obs, deterministic=True)
        rpy = np.array([a[0] * RPY_MAX * 0.7, a[1] * RPY_MAX * 0.7, 0.0])
        thrust = THRUST_MIN + (np.clip(a[3], -1, 1) + 1) * 0.5 * (THRUST_MAX - THRUST_MIN)
        self._last_thrust = float(thrust)
        return np.array([rpy[0], rpy[1], rpy[2], thrust])
