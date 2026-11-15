import pytest

from stitch import sensor_poses

def test_sensor_poses_turn_past_360():
    photos = [
        {"tilt": 0, "rotation": {"yaw": 350, "pitch": 0, "roll": 0}},
        {"tilt": 1, "rotation": {"yaw": 10, "pitch": 30, "roll": 4}},
    ]

    poses = sensor_poses(photos)

    assert poses[0] == pytest.approx((0, 0, 0))
    assert poses[1] == pytest.approx((20, 30, -4))
