"""PPO training for the DATT-style tracking policy.

Run (WSL venv):
    python -m crazy_track.training.ppo_train --timesteps 2000000 --reason "..."
"""

from __future__ import annotations

import argparse

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv

from crazy_track.envs.datt_env import DATTTrackingEnv
from crazy_track.eval.runlog import RunLogger


class SB3Adapter(VecEnv):
    """Adapt DATTTrackingEnv (gymnasium-vector-style) to the SB3 VecEnv API."""

    def __init__(self, env: DATTTrackingEnv):
        self.env = env
        super().__init__(env.num_envs, env.single_observation_space, env.single_action_space)
        self._actions = None

    def reset(self):
        obs, _ = self.env.reset()
        return obs

    def step_async(self, actions):
        self._actions = actions

    def step_wait(self):
        obs, reward, term, trunc, info = self.env.step(self._actions)
        done = term | trunc
        infos = [{} for _ in range(self.num_envs)]
        if done.any():
            terminal_obs = info["terminal_obs"]
            for i in np.flatnonzero(done):
                infos[i]["terminal_observation"] = terminal_obs[i]
                infos[i]["TimeLimit.truncated"] = bool(trunc[i] and not term[i])
        return obs, reward, done, infos

    def close(self):
        pass

    def get_attr(self, attr_name, indices=None):
        return [getattr(self.env, attr_name)] * self.num_envs

    def set_attr(self, attr_name, value, indices=None):
        setattr(self.env, attr_name, value)

    def env_method(self, method_name, *args, indices=None, **kwargs):
        return [getattr(self.env, method_name)(*args, **kwargs)] * self.num_envs

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=2_000_000)
    parser.add_argument("--n-envs", type=int, default=16)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--noisy-sensor", action="store_true",
                        help="v4: train on Lighthouse-noisy observations")
    args = parser.parse_args()

    log = RunLogger(tag="datt-train", reason=args.reason, config=vars(args))
    print(f"Logging to {log.dir}", flush=True)

    env = SB3Adapter(DATTTrackingEnv(num_envs=args.n_envs, seed=args.seed,
                                     noisy_sensor=args.noisy_sensor))
    model = PPO(
        "MlpPolicy", env, verbose=1, seed=args.seed,
        n_steps=256, batch_size=1024, learning_rate=3e-4, gamma=0.98,
        policy_kwargs=dict(net_arch=[64, 64]),
        tensorboard_log=str(log.dir / "tb"),
    )
    model.learn(total_timesteps=args.timesteps, progress_bar=False)
    model.save(log.dir / "datt_ppo_final")
    print(f"Saved model to {log.dir / 'datt_ppo_final.zip'}", flush=True)


if __name__ == "__main__":
    main()
