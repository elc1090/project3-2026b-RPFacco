import pytest

from align import angles, rotation

def test_angles_undo_rotation():
    yaw, pitch, roll = 30, -20, 5

    matrix = rotation(yaw, pitch, roll)

    assert angles(matrix) == pytest.approx((yaw, pitch, roll))
