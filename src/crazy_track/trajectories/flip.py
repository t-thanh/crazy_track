from __future__ import annotations

import numpy as np

from crazy_track.trajectories.base import Trajectory


class FlipTrajectory(Trajectory):
    """Hover -> full 360-degree flip about a body axis -> hover recovery.

    Position reference stays at the hover point (the physically ideal flip
    returns there); the attitude reference sweeps 0..2*pi about `axis` over
    [t0, t0+Tf] with a smooth cosine ramp. Altitude margin matters: thrust
    averages ~zero vertical during the rotation, so the drone drops
    ~0.5*g*(Tf/2)^2-ish — hover point defaults to z=1.5 m.
    """

    def __init__(self, hover=(0.0, 0.0, 1.5), t0: float = 2.0, Tf: float = 0.5,
                 axis: int = 0, direction: int = 1, duration: float = 6.0):
        self.hover = np.asarray(hover, dtype=np.float64)
        self.t0, self.Tf = t0, Tf
        self.axis, self.direction = axis, direction  # 0 = roll, 1 = pitch
        self.duration = duration

    def pos(self, t):
        t = self._clamp(t)
        return np.broadcast_to(self.hover, t.shape + (3,)).copy()

    def vel(self, t):
        t = self._clamp(t)
        return np.zeros(t.shape + (3,))

    def acc(self, t):
        t = self._clamp(t)
        return np.zeros(t.shape + (3,))

    def att_ref_rotvec(self, t):
        t = self._clamp(t)
        u = np.clip((t - self.t0) / self.Tf, 0.0, 1.0)
        theta = self.direction * 2 * np.pi * 0.5 * (1 - np.cos(np.pi * u))  # smooth 0..2pi
        # Represent as rotvec with angle wrapped to (-pi, pi] so the error to the
        # current attitude stays continuous through the flip.
        theta_wrapped = np.mod(theta + np.pi, 2 * np.pi) - np.pi
        out = np.zeros(np.shape(theta) + (3,))
        out[..., self.axis] = theta_wrapped
        return out
