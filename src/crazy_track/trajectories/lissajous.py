from __future__ import annotations

import numpy as np

from crazy_track.trajectories.base import Trajectory


class LissajousTrajectory(Trajectory):
    """Figure-eight Lissajous from 'Learning to Fly in Seconds' (arXiv:2311.13081, Fig. 5).

    p(t) = [A*cos(2*pi*t/T), B*sin(4*pi*t/T), z] with A=1, B=0.5 as in the paper.
    Cycle times benchmarked: slow T=15s, normal T=5.5s, fast T=3.5s (up to 3 m/s, 0.9g).
    """

    SPEEDS = {"slow": 15.0, "normal": 5.5, "fast": 3.5}

    def __init__(self, T: float = 5.5, A: float = 1.0, B: float = 0.5, z: float = 1.0,
                 n_cycles: int = 2):
        self.T, self.A, self.B, self.z = T, A, B, z
        self.duration = n_cycles * T

    @classmethod
    def from_speed(cls, speed: str, **kwargs) -> "LissajousTrajectory":
        return cls(T=cls.SPEEDS[speed], **kwargs)

    def _angles(self, t):
        t = self._clamp(t)
        w = 2 * np.pi / self.T
        return t, w

    def pos(self, t):
        t, w = self._angles(t)
        return np.stack(
            [self.A * np.cos(w * t), self.B * np.sin(2 * w * t), np.full_like(t, self.z)], axis=-1
        )

    def vel(self, t):
        t, w = self._angles(t)
        return np.stack(
            [-self.A * w * np.sin(w * t), 2 * w * self.B * np.cos(2 * w * t), np.zeros_like(t)],
            axis=-1,
        )

    def acc(self, t):
        t, w = self._angles(t)
        return np.stack(
            [-self.A * w**2 * np.cos(w * t), -4 * w**2 * self.B * np.sin(2 * w * t),
             np.zeros_like(t)],
            axis=-1,
        )
