import numpy as np
import pytest

from crazy_track.trajectories import ChainedPolyTrajectory, ZigzagTrajectory

EPS = 1e-4


@pytest.fixture
def rng():
    return np.random.default_rng(0)


class TestChainedPoly:
    def test_starts_at_rest_at_origin(self, rng):
        traj = ChainedPolyTrajectory.random(rng)
        np.testing.assert_allclose(traj.pos(0.0), np.zeros(3), atol=1e-9)
        np.testing.assert_allclose(traj.vel(0.0), np.zeros(3), atol=1e-9)
        np.testing.assert_allclose(traj.acc(0.0), np.zeros(3), atol=1e-9)

    def test_c2_continuity_at_knots(self, rng):
        traj = ChainedPolyTrajectory.random(rng, duration=10.0, seg_duration=2.0)
        for tk in traj.knot_times[1:-1]:
            for fn in (traj.pos, traj.vel, traj.acc):
                left, right = fn(tk - EPS), fn(tk + EPS)
                np.testing.assert_allclose(left, right, atol=1e-2)

    def test_derivative_consistency(self, rng):
        """vel/acc match finite differences of pos."""
        traj = ChainedPolyTrajectory.random(rng)
        t = np.linspace(0.1, traj.duration - 0.1, 50)
        num_vel = (traj.pos(t + EPS) - traj.pos(t - EPS)) / (2 * EPS)
        np.testing.assert_allclose(num_vel, traj.vel(t), atol=1e-4)
        num_acc = (traj.vel(t + EPS) - traj.vel(t - EPS)) / (2 * EPS)
        np.testing.assert_allclose(num_acc, traj.acc(t), atol=1e-4)

    def test_shapes_and_clamping(self, rng):
        traj = ChainedPolyTrajectory.random(rng)
        assert traj.pos(1.0).shape == (3,)
        assert traj.pos(np.linspace(0, 20, 7)).shape == (7, 3)
        np.testing.assert_allclose(traj.pos(traj.duration + 5.0), traj.pos(traj.duration))

    def test_ref_window(self, rng):
        traj = ChainedPolyTrajectory.random(rng)
        win = traj.ref_window(1.0, horizon=10, dt=0.02)
        assert win.shape == (10, 3)
        np.testing.assert_allclose(win[0], traj.pos(1.0))


class TestZigzag:
    def test_starts_at_origin(self, rng):
        traj = ZigzagTrajectory.random(rng)
        np.testing.assert_allclose(traj.pos(0.0), np.zeros(3), atol=1e-9)

    def test_hits_waypoints(self, rng):
        traj = ZigzagTrajectory.random(rng)
        for tk, wp in zip(traj.knot_times, traj.waypoints):
            if tk <= traj.duration:
                np.testing.assert_allclose(traj.pos(tk), wp, atol=1e-9)

    def test_position_continuous_velocity_discontinuous(self, rng):
        traj = ZigzagTrajectory.random(rng)
        interior = traj.knot_times[1:-1]
        vel_jumps = [
            np.linalg.norm(traj.vel(tk + EPS) - traj.vel(tk - EPS)) for tk in interior
        ]
        for tk in interior:
            np.testing.assert_allclose(traj.pos(tk - EPS), traj.pos(tk + EPS), atol=1e-2)
        assert max(vel_jumps) > 0.1  # infeasible by construction

    def test_shapes(self, rng):
        traj = ZigzagTrajectory.random(rng)
        assert traj.vel(1.0).shape == (3,)
        assert traj.acc(np.linspace(0, 5, 4)).shape == (4, 3)
