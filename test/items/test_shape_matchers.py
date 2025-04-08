
import unittest

import numpy as np

from janim.constants import DL, UR
from janim.items.geometry.arc import Circle
from janim.items.shape_matchers import SurroundingRect
from janim.utils.data import Margins


class ShapeMatcherTest(unittest.TestCase):
    def assertNparrayEqual(self, np1, np2):
        self.assertListEqual(np.array(np1).tolist(), np.array(np2).tolist())

    def assertNparrayClose(self, np1, np2):
        np1 = np.array(np1)
        np2 = np.array(np2)
        self.assertListEqual(np.isclose(np1, np2).tolist(), np.full(np1.shape, True).tolist())

    def test_surrect(self):
        circle = Circle(radius=1)
        rect1 = SurroundingRect(circle, buff=1)
        rect2 = SurroundingRect(circle, buff=Margins(1, 2, 3, 4))

        self.assertNparrayClose(rect1.points.box.data[[0, 2]], [DL * 2, UR * 2])
        self.assertNparrayClose(rect2.points.box.data[[0, 2]], [[-2, -5, 0], [4, 3, 0]])
