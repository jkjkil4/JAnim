import unittest

from janim.utils.space_ops import (angle_axis_from_quaternion,
                                   quaternion_from_angle_axis, rotate_vector,
                                   rotation_matrix,
                                   rotation_matrix_from_quaternion)


class TestQuaternionOperations(unittest.TestCase):
    def test_quaternion_from_angle_axis(self):
        angle = 1.0
        axis = [1.0, 0.5, 0.0]
        q = quaternion_from_angle_axis(angle, axis)
        self.assertAlmostEqual(q[0], 0.428811237787379, places=6)
        self.assertAlmostEqual(q[1], 0.2144056188936895, places=6)
        self.assertAlmostEqual(q[2], 0.0, places=6)
        self.assertAlmostEqual(q[3], 0.8775825618903728, places=6)

    def test_angle_axis_from_quaternion(self):
        q = [0.5403023058681398, 0.8414709848078965, 0.5, 0.0]
        angle, axis = angle_axis_from_quaternion(q)
        self.assertAlmostEqual(angle, 3.141592653589793, places=6)
        self.assertAlmostEqual(axis[0], 0.54030231, places=6)
        self.assertAlmostEqual(axis[1], 0.84147098, places=6)
        self.assertAlmostEqual(axis[2], 0.5, places=6)

    def test_rotate_vector(self):
        v = [1.0, 2.0, 3.0]
        rotated_v = rotate_vector(v, 2, [1, 3, 0])
        self.assertAlmostEqual(rotated_v[0], 3.16306179, places=6)
        self.assertAlmostEqual(rotated_v[1], 1.2789794, places=6)
        self.assertAlmostEqual(rotated_v[2], -1.5359856, places=6)

    def test_rotation_matrix_from_quaternion(self):
        q = [0.5403023058681398, 0.8414709848078965, 0.5, 0.0]
        R = rotation_matrix_from_quaternion(q)
        expected_R = [
            [-0.53291747,  0.72743794,  0.43224184],
            [ 0.72743794,  0.13291747,  0.67317679],
            [ 0.43224184,  0.67317679, -0.6       ],
        ]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(R[i][j], expected_R[i][j], places=6)

    def test_rotation_matrix(self):
        angle = 1.0
        axis = [1.0, 0.5, 0.0]
        R = rotation_matrix(angle, axis)
        expected_R = [
            [ 0.90806046, 0.18387908,  0.37631726],
            [ 0.18387908, 0.63224184, -0.75263453],
            [-0.37631726, 0.75263453,  0.54030231],
        ]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(R[i][j], expected_R[i][j], places=6)


if __name__ == '__main__':
    unittest.main()
