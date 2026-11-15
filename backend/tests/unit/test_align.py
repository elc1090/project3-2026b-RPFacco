import math

import numpy as np
import pytest

from align import angles, camera_rays, rotation

def test_angles_undo_rotation():
    yaw, pitch, roll = 30, -20, 5

    matrix = rotation(yaw, pitch, roll)

    assert angles(matrix) == pytest.approx((yaw, pitch, roll))

def test_camera_rays_point_from_the_photo():
    images = [{"w": 100, "h": 100, "hfov": 90}]
    centre, right_edge, top_edge = (50, 50), (100, 50), (50, 0)
    xs = np.array([centre[0], right_edge[0], top_edge[0]], dtype=float)
    ys = np.array([centre[1], right_edge[1], top_edge[1]], dtype=float)

    rays = camera_rays(images, np.array([0, 0, 0]), xs, ys)

    half = math.sqrt(0.5)
    assert rays[0] == pytest.approx([0, 0, 1])
    assert rays[1] == pytest.approx([half, 0, half])
    assert rays[2] == pytest.approx([0, half, half])
