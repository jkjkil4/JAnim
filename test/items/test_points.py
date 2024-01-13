import math
import unittest

import numpy as np

from janim.constants import DL, DOWN, DR, LEFT, ORIGIN, RIGHT, UL, UP, UR, OUT, TAU, DEGREES
from janim.items.item import Group, Item
from janim.items.points import Points


class PointsTest(unittest.TestCase):
    def assertNparrayEqual(self, np1, np2):
        self.assertListEqual(np.array(np1).tolist(), np.array(np2).tolist())

    def assertNparrayClose(self, np1, np2):
        np1 = np.array(np1)
        np2 = np.array(np2)
        self.assertListEqual(np.isclose(np1, np2).tolist(), np.full(np1.shape, True).tolist())

    def test_points(self) -> None:
        p = Points()

        p.points.set([[1, 2, 3], [1.3, 1, 3]])
        self.assertNparrayEqual(
            p.points.get(),
            [[1, 2, 3], [1.3, 1, 3]]
        )

        p.points.append([[6, 3, 1]])
        self.assertNparrayEqual(
            p.points.get(),
            [[1, 2, 3], [1.3, 1, 3], [6, 3, 1]]
        )

        p.points.reverse()
        self.assertNparrayEqual(
            p.points.get(),
            [[6, 3, 1], [1.3, 1, 3], [1, 2, 3]]
        )

        self.assertEqual(p.points.count(), 3)
        self.assertTrue(p.points.has())
        self.assertNparrayEqual(
            p.points.get_start(),
            [6, 3, 1]
        )
        self.assertNparrayEqual(
            p.points.get_end(),
            [1, 2, 3]
        )

        p.points.resize(2)
        self.assertNparrayEqual(
            p.points.get(),
            [[6, 3, 1], [1.3, 1, 3]]
        )

        p.points.resize(4)
        self.assertNparrayEqual(
            p.points.get(),
            [[6, 3, 1], [1.3, 1, 3], [1.3, 1, 3], [1.3, 1, 3]]
        )

        p.points.clear()
        self.assertNparrayEqual(
            p.points.get(),
            []
        )

        with self.assertRaises(ValueError):
            p.points.get_start()

        p.points.resize(3)
        self.assertNparrayEqual(
            p.points.get(),
            [ORIGIN] * 3
        )

    def test_get_all_points(self) -> None:
        root = Points(UP, RIGHT).add(
            g := Group(
                Points(DOWN, UL),
                Item(),
                Points(RIGHT, DR, DL)
            )
        )
        self.assertNparrayEqual(
            root.points.get_all(),
            [UP, RIGHT, DOWN, UL, RIGHT, DR, DL]
        )
        self.assertNparrayEqual(
            g.astype(Points).points.get_all(),
            [DOWN, UL, RIGHT, DR, DL]
        )

    def test_bounding_box(self) -> None:
        p = Points(UL, RIGHT, UR + UP, OUT * 2)
        box = p.points.box.data

        self.assertNparrayEqual(
            box[[0, 2]],
            [LEFT, UR + UP + OUT * 2]
        )
        self.assertNparrayEqual(
            p.points.box.get(UP),
            UP * 2 + OUT
        )

        box = p.points.box

        self.assertNparrayEqual(
            [
                box.top,
                box.bottom,
                box.left,
                box.right,

                box.zenith,
                box.nadir,

                box.center
            ],
            [
                UP * 2 + OUT,
                ORIGIN + OUT,
                UL + OUT,
                UR + OUT,

                UP + OUT * 2,
                UP,

                UP + OUT
            ]
        )
        self.assertListEqual(
            [
                box.width,
                box.height,
                box.depth,

                box.x,
                box.y,
                box.z
            ],
            [
                2,
                2,
                2,

                0,
                1,
                1
            ]
        )

    def test_bounding_box_with_rel(self) -> None:
        g = Group(
            p1 := Points(UL, RIGHT),
            p2 := Points(UR + UP),
            p3 := Points()
        )

        box = g.astype(Points).points.box.data
        self.assertNparrayEqual(
            box[[0, 2]],
            [LEFT, UR + UP]
        )

        g.add(Points(DOWN))
        box = g.astype(Points).points.box.data
        self.assertNparrayEqual(
            box[[0, 2]],
            [DL, UR + UP]
        )

        self.assertNparrayEqual(
            g.astype(Points).points.box.get(UR),
            UR + UP
        )

        self.assertNparrayEqual(p1.points.self_box.left, LEFT + UP * 0.5)
        self.assertNparrayEqual(p3.points.box.data, [ORIGIN, ORIGIN, ORIGIN])

    def test_bounding_box_get_continuous(self) -> None:
        def test(center: np.ndarray, width: int, height: int):
            half_width = width / 2
            half_height = height / 2

            vect = half_width * RIGHT + half_height * DOWN
            p = Points(center + vect, center - vect)

            for radian in np.arange(0, TAU, DEGREES * 8.1):
                x = math.cos(radian)
                y = math.sin(radian)
                factor = min(
                    math.inf if x == 0 else half_width / abs(x),
                    math.inf if y == 0 else half_height / abs(y)
                )

                point = center + [x * factor, y * factor, 0]

                self.assertNparrayClose(
                    p.points.box.get_continuous([x, y, 0]),
                    point
                )

        test(LEFT, 2, 4)
        test(ORIGIN, 1, 0.2)
        test(RIGHT * UP * 10, 3, 2)

