import unittest

from janim.utils.space_ops import (angle_axis_from_quaternion,
                                   quaternion_from_angle_axis, rotate_vector,
                                   rotation_matrix,
                                   rotation_matrix_from_quaternion)


class TestQuaternionOperations(unittest.TestCase):
    def test_quaternion_from_angle_axis(self):
        angle = 1.0
        axis = [1.0, 0.0, 0.0]
        q = quaternion_from_angle_axis(angle, axis)
        self.assertAlmostEqual(q[0], 0.479425538604203, places=6)
        self.assertAlmostEqual(q[1], 0.0, places=6)
        self.assertAlmostEqual(q[2], 0.0, places=6)
        self.assertAlmostEqual(q[3], 0.8775825618903728, places=6)

    def test_angle_axis_from_quaternion(self):
        q = [0.5403023058681398, 0.8414709848078965, 0.0, 0.0]
        angle, axis = angle_axis_from_quaternion(q)
        self.assertAlmostEqual(angle, 3.141592653589793, places=6)
        self.assertAlmostEqual(axis[0], 0.5403023058681398, places=6)
        self.assertAlmostEqual(axis[1], 0.8414709848078965, places=6)
        self.assertAlmostEqual(axis[2], 0.0, places=6)

    def test_rotate_vector(self):
        v = [1.0, 2.0, 3.0]
        rotated_v = rotate_vector(v, 2, [1, 3, 0])
        self.assertAlmostEqual(rotated_v[0], 3.16306179, places=6)
        self.assertAlmostEqual(rotated_v[1], 1.2789794, places=6)
        self.assertAlmostEqual(rotated_v[2], -1.5359856, places=6)

    def test_rotation_matrix_from_quaternion(self):
        q = [0.5403023058681398, 0.8414709848078965, 0.0, 0.0]
        R = rotation_matrix_from_quaternion(q)
        expected_R = [
            [-0.41614684, 0.90929743,  0.        ],
            [ 0.90929743, 0.41614684,  0.        ],
            [ 0.        , 0.        , -1.        ],
        ]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(R[i][j], expected_R[i][j], places=6)

    def test_rotation_matrix(self):
        angle = 1.0
        axis = [1.0, 0.0, 0.0]
        R = rotation_matrix(angle, axis)
        expected_R = [
            [1.0, 0.0, 0.0],
            [0.0, 0.5403023058681398, -0.8414709848078965],
            [0.0, 0.8414709848078965, 0.5403023058681398]
        ]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(R[i][j], expected_R[i][j], places=6)


if __name__ == '__main__':
    unittest.main()
