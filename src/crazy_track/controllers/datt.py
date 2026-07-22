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

    def reset(self, trajectory: Trajectory) -> None:
        self._traj = trajectory

    def act(self, state: np.ndarray, t: float) -> np.ndarray:
        pos, vel, quat = state[:3], state[3:6], state[6:10]
        win = self._traj.pos(t + self._t_offsets) - pos
        obs = np.concatenate([self._traj.pos(t) - pos, vel, quat, win.ravel()]).astype(np.float32)
        a, _ = self.model.predict(obs, deterministic=True)
        rpy = np.array([a[0] * RPY_MAX * 0.7, a[1] * RPY_MAX * 0.7, 0.0])
        thrust = THRUST_MIN + (np.clip(a[3], -1, 1) + 1) * 0.5 * (THRUST_MAX - THRUST_MIN)
        return np.array([rpy[0], rpy[1], rpy[2], thrust])
