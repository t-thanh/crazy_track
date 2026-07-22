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
OBS_DIM = 3 + 3 + 4 + 3 * WINDOW  # v2 (no L1)
OBS_DIM_V3 = OBS_DIM + 3  # v3 appends the L1 disturbance estimate
PRIV_DIM = 3 + 3 + 4 + 3  # v5 privileged critic block: true err/vel/quat + perturb acc
OBS_DIM_V5 = OBS_DIM_V3 + PRIV_DIM
STACK = 4  # v6a: actor frames stacked so sensor-noise level becomes observable
OBS_DIM_V6 = OBS_DIM_V3 * STACK + PRIV_DIM
OBS_DIM_ACRO2 = OBS_DIM_V3 + 3  # + attitude-error rotvec (flip maneuvers)
MASS = 0.04338
PERTURB_ACC_MAX = 3.5  # m/s^2 per axis, as in DATT (arXiv:2310.09053)


class DATTTrackingEnv:
    """Vectorized tracking env. Wraps crazyflow Sim directly (n_worlds parallel)."""

    def __init__(self, num_envs: int = 16, freq: int = 50, episode_time: float = 6.0,
                 drone: str = "cf21B_500", dynamics: str = "first_principles",
                 seed: int = 0, v3: bool = True, noisy_sensor: bool = False,
                 v5: bool = False, v6: bool = False, ctbr: bool = False,
                 acro2: bool = False):
        from crazyflow import Sim
        from crazyflow.dynamics import Dynamics

        self.num_envs = num_envs
        self.freq = freq
        self.acro2 = acro2  # flip primitives: attitude-ref obs + reward, mixed episodes
        self.ctbr = ctbr or acro2  # action = [thrust, body rates], rate loop -> torques
        self.v3 = v3
        self.v6 = v6  # frame-stacked actor obs (implies v5)
        self.v5 = v5 or v6  # privileged critic obs + noise-level domain randomization
        self.noisy_sensor = noisy_sensor or self.v5  # v4/v5/v6: policy sees noisy obs
        if self.noisy_sensor:
            from crazy_track.sensors import LighthouseSensorBatch

            self.sensor = LighthouseSensorBatch(num_envs, control_freq=freq,
                                                seed=seed + 1, noise_dr=self.v5)
        if v6:
            self._stack = np.zeros((num_envs, STACK, OBS_DIM_V3), dtype=np.float32)
        self.max_steps = int(episode_time * freq)
        self.sim = Sim(n_worlds=num_envs, n_drones=1, drone=drone,
                       dynamics=Dynamics(dynamics),
                       control="force_torque" if self.ctbr else "attitude",
                       freq=500, device="cpu")
        self.n_substeps = self.sim.freq // freq
        self.rng = np.random.default_rng(seed)
        if v3:
            from crazy_track.controllers.l1 import L1Estimator

            self.l1 = L1Estimator(MASS, n=num_envs, dt=1.0 / freq)
            self.perturb_force = np.zeros((num_envs, 3))
        obs_dim = (OBS_DIM_ACRO2 if acro2 else OBS_DIM_V6 if v6 else
                   OBS_DIM_V5 if self.v5 else (OBS_DIM_V3 if v3 else OBS_DIM))

        self.single_observation_space = spaces.Box(-np.inf, np.inf, shape=(obs_dim,),
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
        # CTBR/acro mode extends to the platform limit (TWR 1.88 -> ~15 m/s^2 lateral).
        # acro2 mixes in flip episodes (50%): hover -> 360-deg roll/pitch -> recover.
        if self.acro2 and self.rng.random() < 0.5:
            from crazy_track.trajectories import FlipTrajectory

            self._traj[i] = FlipTrajectory(
                hover=(0.0, 0.0, 1.5),
                t0=float(self.rng.uniform(1.5, 3.0)),
                Tf=float(self.rng.uniform(0.4, 0.7)),
                axis=int(self.rng.integers(0, 2)),
                direction=int(self.rng.choice([-1, 1])),
                duration=self.max_steps / self.freq + WINDOW * WINDOW_DT + 1.0,
            )
            return
        if self.ctbr:
            vel_range = float(self.rng.uniform(1.0, 5.0))
            acc_range = float(self.rng.uniform(3.0, 15.0))
        else:
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
        starts = np.stack([self._traj[i].pos(0.0) for i in np.flatnonzero(mask)])
        pos[mask, 0] = starts + noise
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
        all_mask = np.ones(self.num_envs, dtype=bool)
        self._set_states(all_mask)
        if self.v3:
            self.l1.reset()
            self._sample_perturb(all_mask)
        if self.noisy_sensor:
            self.sensor.reset()
        self._meas = self._measured_arrays()
        if self.v6:  # fill every stack slot with the initial frame
            base = self._base_obs()
            self._stack[:] = base[:, None, :]
        return self._obs(), {}

    def _state_arrays(self):
        s = self.sim.data.states
        return (np.asarray(s.pos[:, 0]), np.asarray(s.vel[:, 0]), np.asarray(s.quat[:, 0]))

    def _measured_arrays(self):
        """What the policy/L1 see: noisy+delayed under v4, true state otherwise."""
        pos, vel, quat = self._state_arrays()
        if not self.noisy_sensor:
            return pos, vel, quat
        omega = np.asarray(self.sim.data.states.ang_vel[:, 0])
        t = self.steps / self.freq
        pos_m, vel_m, quat_m, _ = self.sensor.measure(t, pos, vel, quat, omega)
        return pos_m, vel_m, quat_m

    def _refs(self, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Current ref pos (N,3) and window (N, WINDOW, 3)."""
        ref = np.stack([self._traj[i].pos(t[i]) for i in range(self.num_envs)])
        win = np.stack([self._traj[i].pos(t[i] + self._t_offsets) for i in range(self.num_envs)])
        return ref, win

    def _base_obs(self) -> np.ndarray:
        """The deployable (noisy-view) observation frame, (N, OBS_DIM_V3|OBS_DIM)."""
        pos, vel, quat = self._meas  # measured (v4+: noisy/delayed) state
        t = self.steps / self.freq
        ref, win = self._refs(t)
        rel_win = (win - pos[:, None, :]).reshape(self.num_envs, -1)
        parts = [ref - pos, vel, quat, rel_win]
        if self.v3:
            parts.append(self.l1.sigma_f.astype(np.float32))
        if self.acro2:
            parts.append(self._att_err(quat, t).astype(np.float32))
        return np.concatenate(parts, axis=1).astype(np.float32)

    def _att_err(self, quat: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Rotation-vector error between reference attitude and current, (N, 3)."""
        from scipy.spatial.transform import Rotation as R

        ref_rv = np.stack([self._traj[i].att_ref_rotvec(t[i]) for i in range(self.num_envs)])
        return (R.from_rotvec(ref_rv).inv() * R.from_quat(quat)).as_rotvec()

    def _push_stack(self, base: np.ndarray, refill_mask: np.ndarray | None = None) -> None:
        self._stack = np.roll(self._stack, -1, axis=1)
        self._stack[:, -1] = base
        if refill_mask is not None and refill_mask.any():
            self._stack[refill_mask] = base[refill_mask][:, None, :]

    def _obs(self) -> np.ndarray:
        base = self._base_obs()
        actor = self._stack.reshape(self.num_envs, -1) if self.v6 else base
        if not self.v5:
            return actor
        # privileged tail, visible only to the critic
        t = self.steps / self.freq
        ref = np.stack([self._traj[i].pos(t[i]) for i in range(self.num_envs)])
        pos_t, vel_t, quat_t = self._state_arrays()
        priv = np.concatenate(
            [ref - pos_t, vel_t, quat_t, self.perturb_force / MASS], axis=1
        )
        return np.concatenate([actor, priv], axis=1).astype(np.float32)

    def _sample_perturb(self, mask: np.ndarray) -> None:
        """Per-episode random constant force perturbation (DATT recipe)."""
        n = int(mask.sum())
        acc = self.rng.uniform(-PERTURB_ACC_MAX, PERTURB_ACC_MAX, size=(n, 3))
        acc[:, 2] *= 0.5  # limit vertical component (TWR is only 1.88)
        self.perturb_force[mask] = MASS * acc

    def _denorm_action(self, a: np.ndarray) -> np.ndarray:
        if self.ctbr:
            from crazy_track.controllers.utils import RATE_MAX, ctbr_to_force_torque

            thrust = THRUST_MIN + (np.clip(a[:, 0], -1, 1) + 1) * 0.5 * (THRUST_MAX - THRUST_MIN)
            w_des = np.clip(a[:, 1:4], -1, 1) * RATE_MAX
            omega = np.asarray(self.sim.data.states.ang_vel[:, 0])
            return ctbr_to_force_torque(thrust, w_des, omega)[:, None, :].astype(np.float32)
        cmd = np.zeros((self.num_envs, 1, 4), dtype=np.float32)
        cmd[:, 0, 0:2] = np.clip(a[:, 0:2], -1, 1) * RPY_MAX * 0.7
        cmd[:, 0, 2] = 0.0  # yaw fixed
        thrust = THRUST_MIN + (np.clip(a[:, 3], -1, 1) + 1) * 0.5 * (THRUST_MAX - THRUST_MIN)
        cmd[:, 0, 3] = thrust
        return cmd

    def _apply_cmd(self, cmd: np.ndarray) -> None:
        if self.ctbr:
            self.sim.force_torque_control(cmd)
        else:
            self.sim.attitude_control(cmd)

    def step(self, action: np.ndarray):
        cmd = self._denorm_action(np.asarray(action))
        if self.v3:
            import jax.numpy as jnp

            force = jnp.asarray(self.perturb_force[:, None, :], dtype=jnp.float32)
            self.sim.data = self.sim.data.replace(
                states=self.sim.data.states.replace(force=force)
            )
        self._apply_cmd(cmd)
        self.sim.step(self.n_substeps)
        self.steps += 1
        self._meas = self._measured_arrays()
        if self.v3:
            _, vel_m, quat_m = self._meas  # L1 runs on measured state, as onboard
            thrust_cmd = cmd[:, 0, 0] if self.ctbr else cmd[:, 0, 3]
            self.l1.update(vel_m, quat_m, thrust_cmd)

        pos, vel, quat = self._state_arrays()
        t = self.steps / self.freq
        ref, _ = self._refs(t)
        err = np.linalg.norm(ref - pos, axis=1)

        crashed = (pos[:, 2] < 0.05) | (err > 2.0)
        truncated = self.steps >= self.max_steps
        reward = np.exp(-2.0 * err) - 0.02 * np.linalg.norm(action[:, 0:2], axis=1)
        if self.acro2:  # attitude tracking matters as much as position for maneuvers
            att_angle = np.linalg.norm(self._att_err(quat, t), axis=1)
            reward = reward + 0.6 * np.exp(-3.0 * att_angle)
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
            if self.v3:
                self._sample_perturb(done_mask)
                self.l1.v_hat[done_mask] = 0.0
                self.l1.sigma_hat[done_mask] = 0.0
                self.l1.sigma_f[done_mask] = 0.0
            if self.noisy_sensor:
                self.sensor.reset_rows(done_mask)
            self._meas = self._measured_arrays()

        if self.v6:
            self._push_stack(self._base_obs(),
                             refill_mask=done_mask if done_mask.any() else None)
        return self._obs(), reward, crashed, truncated, info
