"""DATT-style trajectory-tracking training env on crazyflow (vectorized).

Observation (DATT, arXiv:2310.09053): position error, velocity, attitude quat,
and a feedforward window of future reference positions relative to the drone.
Action: normalized [roll, pitch, yaw, collective thrust] -> firmware attitude
interface. Training trajectories: random C^2 chained polynomials starting at
the hover point (as in DATT); evaluation on Lissajous is zero-shot.
"""

from __future__ import annotations

import numpy as np
from gymnasium import spaces
from gymnasium.vector.utils import batch_space

from crazy_track.controllers.utils import RPY_MAX, THRUST_MAX, THRUST_MIN
from crazy_track.trajectories import ChainedPolyTrajectory

START = np.array([0.0, 0.0, 1.2])
WINDOW = 10  # future reference samples
WINDOW_DT = 0.06  # s between samples (0.6 s lookahead)
OBS_DIM = 3 + 3 + 4 + 3 * WINDOW


class DATTTrackingEnv:
    """Vectorized tracking env. Wraps crazyflow Sim directly (n_worlds parallel)."""

    def __init__(self, num_envs: int = 16, freq: int = 50, episode_time: float = 6.0,
                 drone: str = "cf21B_500", dynamics: str = "first_principles",
                 seed: int = 0):
        from crazyflow import Sim
        from crazyflow.dynamics import Dynamics

        self.num_envs = num_envs
        self.freq = freq
        self.max_steps = int(episode_time * freq)
        self.sim = Sim(n_worlds=num_envs, n_drones=1, drone=drone,
                       dynamics=Dynamics(dynamics), control="attitude", freq=500, device="cpu")
        self.n_substeps = self.sim.freq // freq
        self.rng = np.random.default_rng(seed)

        self.single_observation_space = spaces.Box(-np.inf, np.inf, shape=(OBS_DIM,),
                                                   dtype=np.float32)
        self.single_action_space = spaces.Box(-1.0, 1.0, shape=(4,), dtype=np.float32)
        self.observation_space = batch_space(self.single_observation_space, num_envs)
        self.action_space = batch_space(self.single_action_space, num_envs)

        self.steps = np.zeros(num_envs, dtype=np.int64)
        # Reference bank: sampled positions at window offsets for each control step.
        self._traj = [None] * num_envs
        self._t_offsets = WINDOW_DT * np.arange(1, WINDOW + 1)

    def _sample_traj(self, i: int) -> None:
        # Randomized difficulty per trajectory: covers the full Lissajous benchmark
        # envelope (fast reaches ~3 m/s and ~9 m/s^2; policies trained only on
        # gentle refs fail on it — RMSE 0.95 m observed with vel<=1, acc<=2).
        vel_range = float(self.rng.uniform(0.5, 3.5))
        acc_range = float(self.rng.uniform(1.0, 10.0))
        self._traj[i] = ChainedPolyTrajectory.random(
            self.rng, duration=self.max_steps / self.freq + WINDOW * WINDOW_DT + 1.0,
            seg_duration=self.rng.uniform(1.0, 2.5), pos_range=1.0,
            vel_range=vel_range, acc_range=acc_range, start_pos=START,
        )

    def _set_states(self, mask: np.ndarray) -> None:
        import jax.numpy as jnp

        if not mask.any():
            return
        states = self.sim.data.states
        pos = np.array(states.pos)  # copy: np.asarray of a JAX array is read-only
        vel = np.array(states.vel)
        noise = self.rng.uniform(-0.05, 0.05, size=(int(mask.sum()), 3))
        pos[mask, 0] = START + noise
        vel[mask, 0] = 0.0
        self.sim.data = self.sim.data.replace(
            states=states.replace(pos=jnp.asarray(pos), vel=jnp.asarray(vel))
        )

    def reset(self, seed: int | None = None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.sim.reset()
        for i in range(self.num_envs):
            self._sample_traj(i)
        self.steps[:] = 0
        self._set_states(np.ones(self.num_envs, dtype=bool))
        return self._obs(), {}

    def _state_arrays(self):
        s = self.sim.data.states
        return (np.asarray(s.pos[:, 0]), np.asarray(s.vel[:, 0]), np.asarray(s.quat[:, 0]))

    def _refs(self, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Current ref pos (N,3) and window (N, WINDOW, 3)."""
        ref = np.stack([self._traj[i].pos(t[i]) for i in range(self.num_envs)])
        win = np.stack([self._traj[i].pos(t[i] + self._t_offsets) for i in range(self.num_envs)])
        return ref, win

    def _obs(self) -> np.ndarray:
        pos, vel, quat = self._state_arrays()
        t = self.steps / self.freq
        ref, win = self._refs(t)
        rel_win = (win - pos[:, None, :]).reshape(self.num_envs, -1)
        return np.concatenate([ref - pos, vel, quat, rel_win], axis=1).astype(np.float32)

    def _denorm_action(self, a: np.ndarray) -> np.ndarray:
        cmd = np.zeros((self.num_envs, 1, 4), dtype=np.float32)
        cmd[:, 0, 0:2] = np.clip(a[:, 0:2], -1, 1) * RPY_MAX * 0.7
        cmd[:, 0, 2] = 0.0  # yaw fixed
        thrust = THRUST_MIN + (np.clip(a[:, 3], -1, 1) + 1) * 0.5 * (THRUST_MAX - THRUST_MIN)
        cmd[:, 0, 3] = thrust
        return cmd

    def step(self, action: np.ndarray):
        self.sim.attitude_control(self._denorm_action(np.asarray(action)))
        self.sim.step(self.n_substeps)
        self.steps += 1

        pos, vel, quat = self._state_arrays()
        t = self.steps / self.freq
        ref, _ = self._refs(t)
        err = np.linalg.norm(ref - pos, axis=1)

        crashed = (pos[:, 2] < 0.05) | (err > 2.0)
        truncated = self.steps >= self.max_steps
        reward = np.exp(-2.0 * err) - 0.02 * np.linalg.norm(action[:, 0:2], axis=1)
        reward = np.where(crashed, -5.0, reward).astype(np.float32)

        done_mask = crashed | truncated
        info = {}
        if done_mask.any():
            info["terminal_obs"] = self._obs()  # pre-reset obs for value bootstrapping
            # per-world reset: resample trajectories, zero step counters
            import jax.numpy as jnp

            self.sim.reset(mask=jnp.asarray(done_mask))
            for i in np.flatnonzero(done_mask):
                self._sample_traj(int(i))
            self.steps[done_mask] = 0
            self._set_states(done_mask)

        return self._obs(), reward, crashed, truncated, info
