from __future__ import annotations

import numpy as np

from crazy_track.controllers.base import Controller
from crazy_track.controllers.mppi_l1 import _load_so_rpy_params
from crazy_track.controllers.utils import THRUST_MAX, THRUST_MIN
from crazy_track.trajectories import Trajectory


class MPCController(Controller):
    """Nonlinear receding-horizon MPC on crazyflow's identified so_rpy model.

    Follows lsy_drone_racing's attitude-MPC approach: the identified 2nd-order
    RPY model (Euler-angle state, [rpy, thrust] input) as prediction model,
    multiple-shooting transcription, ipopt with warm starting. crazyflow ships
    the same model as CasADi symbolics; we rebuild the Euler form here directly
    from its parameters.
    """

    def __init__(self, horizon: int = 20, dt_plan: float = 0.04, control_freq: int = 100):
        import casadi as cs

        self.H, self.dtp = horizon, dt_plan
        p = _load_so_rpy_params()
        self.hover = float((p["mass"] * 9.81 - p["acc_coef"]) / p["cmd_f_coef"])

        # so_rpy Euler dynamics: x = [pos(3), rpy(3), vel(3), drpy(3)], u = [rpy_cmd(3), f]
        x, u = cs.MX.sym("x", 12), cs.MX.sym("u", 4)
        rpy, vel, drpy = x[3:6], x[6:9], x[9:12]
        cr, sr = cs.cos(rpy[0]), cs.sin(rpy[0])
        cp, sp = cs.cos(rpy[1]), cs.sin(rpy[1])
        cy, sy = cs.cos(rpy[2]), cs.sin(rpy[2])
        z_axis = cs.vertcat(cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp)
        thrust = p["acc_coef"] + p["cmd_f_coef"] * u[3]
        acc = thrust * z_axis / p["mass"] + cs.DM(p["gravity_vec"])
        ddrpy = (cs.DM(p["rpy_coef"]) * rpy + cs.DM(p["rpy_rates_coef"]) * drpy
                 + cs.DM(p["cmd_rpy_coef"]) * u[0:3])
        xdot = cs.vertcat(vel, drpy, acc, ddrpy)
        f = cs.Function("f", [x, u], [x + self.dtp * (xdot + 0)])  # Euler; dt small vs dynamics

        # Multiple shooting NLP
        opti = cs.Opti()
        X = opti.variable(12, self.H + 1)
        U = opti.variable(4, self.H)
        X0 = opti.parameter(12)
        REF = opti.parameter(3, self.H)
        REFV = opti.parameter(3, self.H)
        cost = 0
        opti.subject_to(X[:, 0] == X0)
        for k in range(self.H):
            opti.subject_to(X[:, k + 1] == f(X[:, k], U[:, k]))
            cost += cs.sumsqr(X[0:3, k + 1] - REF[:, k])
            cost += 0.05 * cs.sumsqr(X[6:9, k + 1] - REFV[:, k])
            cost += 0.02 * cs.sumsqr(U[0:2, k]) + 0.02 * cs.sumsqr(U[3, k] - self.hover)
            if k > 0:
                cost += 0.1 * cs.sumsqr(U[:, k] - U[:, k - 1])
        opti.subject_to(opti.bounded(-1.0, U[0, :], 1.0))
        opti.subject_to(opti.bounded(-1.0, U[1, :], 1.0))
        opti.subject_to(opti.bounded(-0.3, U[2, :], 0.3))
        opti.subject_to(opti.bounded(THRUST_MIN, U[3, :], THRUST_MAX))
        opti.minimize(cost)
        opti.solver("ipopt", {"print_time": False, "ipopt.print_level": 0,
                              "ipopt.max_iter": 60, "ipopt.tol": 1e-4,
                              "ipopt.warm_start_init_point": "yes"})
        self.opti, self.X, self.U, self.X0, self.REF, self.REFV = opti, X, U, X0, REF, REFV
        self._prev = None
        self._traj: Trajectory | None = None

    def reset(self, trajectory: Trajectory) -> None:
        self._traj = trajectory
        self._prev = None

    def act(self, state: np.ndarray, t: float) -> np.ndarray:
        from scipy.spatial.transform import Rotation as R

        pos, vel, quat, omega = state[:3], state[3:6], state[6:10], state[10:13]
        rpy = R.from_quat(quat).as_euler("xyz")
        cr, sr = np.cos(rpy[0]), np.sin(rpy[0])
        cp, tp = np.cos(rpy[1]), np.tan(rpy[1])
        E_inv = np.array([[1, sr * tp, cr * tp], [0, cr, -sr], [0, sr / cp, cr / cp]])
        x0 = np.concatenate([pos, rpy, vel, E_inv @ omega])

        times = t + self.dtp * np.arange(1, self.H + 1)
        self.opti.set_value(self.X0, x0)
        self.opti.set_value(self.REF, self._traj.pos(times).T)
        self.opti.set_value(self.REFV, self._traj.vel(times).T)
        if self._prev is not None:
            Xp, Up = self._prev
            self.opti.set_initial(self.X, Xp)
            self.opti.set_initial(self.U, Up)
        try:
            sol = self.opti.solve()
            Xs, Us = sol.value(self.X), sol.value(self.U)
        except RuntimeError:  # ipopt failed: fall back to last iterate
            Xs = self.opti.debug.value(self.X)
            Us = self.opti.debug.value(self.U)
        # warm start next solve with shifted solution
        Xp = np.hstack([Xs[:, 1:], Xs[:, -1:]])
        Up = np.hstack([Us[:, 1:], Us[:, -1:]])
        self._prev = (Xp, Up)
        u0 = Us[:, 0]
        return np.array([u0[0], u0[1], u0[2], np.clip(u0[3], THRUST_MIN, THRUST_MAX)])
