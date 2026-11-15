import pytest

from stitch import pose_args, sensor_poses

def test_sensor_poses_turn_past_360():
    photos = [
        {"tilt": 0, "rotation": {"yaw": 350, "pitch": 0, "roll": 0}},
        {"tilt": 1, "rotation": {"yaw": 10, "pitch": 30, "roll": 4}},
    ]

    poses = sensor_poses(photos)

    assert poses[0] == pytest.approx((0, 0, 0))
    assert poses[1] == pytest.approx((20, 30, -4))

def test_pose_args_number_each_photo():
    poses = [(0, 0, 0), (20, 30, -4)]

    args = pose_args(poses)

    assert args == "--set=y0=0.0000,p0=0.0000,r0=0.0000,y1=20.0000,p1=30.0000,r1=-4.0000"
