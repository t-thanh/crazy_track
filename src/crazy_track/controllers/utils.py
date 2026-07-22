"""Shared math for position-level controllers: desired acceleration -> attitude command."""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation as R

GRAVITY = 9.81
# cf21B_500 physical limits (drones/params.toml): 4 motors x [thrust_min, thrust_max]
THRUST_MIN = 4 * 0.02136263065537499
THRUST_MAX = 4 * 0.2
MASS = 0.04338
RPY_MAX = 1.0  # rad, safety clip for commanded roll/pitch


def acc2attitude(a_des: np.ndarray, quat_xyzw: np.ndarray, mass: float = MASS,
                 yaw_des: float = 0.0) -> np.ndarray:
    """Convert desired CoM acceleration to [roll, pitch, yaw, thrust_N] (Mellinger-style).

    thrust = f_des . z_body (current attitude); desired attitude aligns body-z
    with f_des at the desired yaw.
    """
    f_des = mass * (a_des + np.array([0.0, 0.0, GRAVITY]))
    z_body = R.from_quat(quat_xyzw).as_matrix()[:, 2]
    thrust = float(np.clip(np.dot(f_des, z_body), THRUST_MIN, THRUST_MAX))

    z_des = f_des / max(np.linalg.norm(f_des), 1e-6)
    x_c = np.array([np.cos(yaw_des), np.sin(yaw_des), 0.0])
    y_des = np.cross(z_des, x_c)
    y_des /= max(np.linalg.norm(y_des), 1e-6)
    x_des = np.cross(y_des, z_des)
    rpy = R.from_matrix(np.stack([x_des, y_des, z_des], axis=-1)).as_euler("xyz")
    rpy[:2] = np.clip(rpy[:2], -RPY_MAX, RPY_MAX)
    return np.array([rpy[0], rpy[1], rpy[2], thrust])
