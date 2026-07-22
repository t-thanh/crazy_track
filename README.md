# crazy_track

Replicating the **DATT** (Deep Adaptive Trajectory Tracking) benchmark — Figure 5 of
[Huang et al., 2023 (arXiv:2311.13081)](https://arxiv.org/pdf/2311.13081) — on the
[crazyflow](https://github.com/utiasDSL/crazyflow) Crazyflie simulator.

## Goal

Reproduce the Figure 5 benchmarking scenario: tracking error of a learned policy
vs. classical baselines on two families of reference trajectories:

1. **Smooth trajectories** — randomized chained polynomials (dynamically feasible).
2. **Infeasible trajectories** — random zigzags (piecewise-linear position with
   velocity discontinuities).

Compared controllers (as in the paper):

| Controller | Status |
|---|---|
| DATT (PPO policy + L1 adaptation + feedforward ref encoding) | planned |
| Nonlinear MPC | planned |
| L1-MPC (MPC + L1 adaptive compensation) | planned |
| PID / geometric baseline | planned |

## Why crazyflow (not CrazySim)

- Pip-installable, CPU-friendly JAX + MuJoCo sim of the Crazyflie 2.x — no
  CUDA, Gazebo, or ROS 2 required (this machine has no NVIDIA GPU).
- Batched/vectorized rollouts make PPO training feasible on CPU.
- Same simulator family used by
  [lsy_drone_racing](https://github.com/learnsyslab/lsy_drone_racing), which we
  use as a structural reference alongside
  [learning-to-fly](https://github.com/arplaboratory/learning-to-fly) and the
  original [DATT code](https://github.com/KevinHuang8/DATT).

## Setup (WSL2 Ubuntu recommended on Windows)

crazyflow officially targets Linux. On Windows, use WSL2:

```powershell
# In an elevated PowerShell (one-time):
wsl --install -d Ubuntu-24.04
```

If the repo lives on the Windows drive (`/mnt/c/...`), enable permission
metadata once inside Ubuntu (editable pip installs fail without it), then
restart the distro:

```bash
sudo tee -a /etc/wsl.conf >/dev/null <<'EOF'

[automount]
options = "metadata"
EOF
# then from Windows: wsl --terminate Ubuntu-24.04
```

Then inside Ubuntu:

```bash
./scripts/setup_env.sh              # venv at ~/venvs/crazy_track, installs crazyflow + this package
source ~/venvs/crazy_track/bin/activate
python -m pytest tests/             # sanity check
```

The trajectory-generation and analysis code is pure numpy and also runs on
native Windows; only the simulator (JAX/MuJoCo) prefers Linux.

## Repository layout

```
src/crazy_track/
  trajectories/    # DATT-style reference generators (chained poly, zigzag)
  envs/            # crazyflow gymnasium wrapper for trajectory tracking
  controllers/     # PID, MPC, L1, DATT policy (common interface)
  training/        # PPO training entrypoint
  eval/            # Figure-5 benchmark runner + plots
configs/           # experiment configs
scripts/           # environment setup, run helpers
tests/             # unit tests (pure-numpy parts)
```

## Roadmap

- [x] Repo scaffold, trajectory generators (smooth + zigzag)
- [ ] crazyflow tracking env (obs = state + windowed future ref, act = CTBR)
- [ ] PID baseline closed-loop in sim
- [ ] PPO training of DATT policy (feedforward ref encoding)
- [ ] L1 adaptation module
- [ ] MPC / L1-MPC baselines
- [ ] Figure 5 replication: tracking-error statistics + box plots
