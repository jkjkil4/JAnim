import math
import unittest

import numpy as np

from janim.constants import (DEGREES, DL, DOWN, DR, LEFT, ORIGIN, OUT, RIGHT,
                             TAU, UL, UP, UR)
from janim.exception import GetItemError, InvaildMatrixError, PointError
from janim.items.item import Item
from janim.items.points import Group, NamedGroup, Points


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
        self.assertNparrayClose(
            p.points.get(),
            [[1, 2, 3], [1.3, 1, 3]]
        )

        p.points.extend([[6, 3, 1]])
        self.assertNparrayClose(
            p.points.get(),
            [[1, 2, 3], [1.3, 1, 3], [6, 3, 1]]
        )

        p.points.reverse()
        self.assertNparrayClose(
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
        self.assertNparrayClose(
            p.points.get(),
            [[6, 3, 1], [1.3, 1, 3]]
        )

        p.points.resize(4)
        self.assertNparrayClose(
            p.points.get(),
            [[6, 3, 1], [1.3, 1, 3], [1.3, 1, 3], [1.3, 1, 3]]
        )

        p.points.clear()
        self.assertNparrayEqual(
            p.points.get(),
            []
        )

        with self.assertRaises(PointError):
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

    def test_transform(self) -> None:
        p1 = Points(UP, DOWN).add(
            Points(UP * 2, DOWN * 2)
        )
        p2 = Points(LEFT * 0.5, RIGHT * 0.5, UP * 0.5, DOWN * 0.5).add(
            p3 := Points(LEFT, RIGHT, UP, DOWN)
        )

        p2.points.surround(p1, 1, buff=0.5)

        self.assertNparrayEqual(
            p2.points.get_all(),
            [
                LEFT * 1.25, RIGHT * 1.25, UP * 1.25, DOWN * 1.25,
                LEFT * 2.5, RIGHT * 2.5, UP * 2.5, DOWN * 2.5
            ]
        )

        p2.points.surround(p1, 1, buff=0.5, stretch=True, root_only=True, item_root_only=True)

        self.assertNparrayClose(
            p2.points.get_all(),
            [
                LEFT * 0.5, RIGHT * 0.5, UP * 1.5, DOWN * 1.5,
                LEFT * 2.5, RIGHT * 2.5, UP * 2.5, DOWN * 2.5
            ]
        )

        p2.points.set_size(2, 2, 2)

        factor = 1 / 2.5

        self.assertNparrayClose(
            p2.points.get_all(),
            np.array([
                LEFT * 0.5, RIGHT * 0.5, UP * 1.5, DOWN * 1.5,
                LEFT * 2.5, RIGHT * 2.5, UP * 2.5, DOWN * 2.5
            ]) * factor
        )

        p2.points.scale((2, 1, 2))

        self.assertNparrayClose(
            p2.points.get_all(),
            np.array([
                LEFT * 0.5, RIGHT * 0.5, UP * 1.5, DOWN * 1.5,
                LEFT * 2.5, RIGHT * 2.5, UP * 2.5, DOWN * 2.5
            ]) * factor * (2, 1, 2)
        )

        p3 = Points(LEFT, RIGHT, UP, DOWN)

        p3.points.flip(axis=UR)
        self.assertNparrayClose(
            p3.points.get(),
            [DOWN, UP, RIGHT, LEFT]
        )

        p3.points.shift(UL)
        self.assertNparrayClose(
            p3.points.get(),
            [UL + DOWN, UL + UP, UL + RIGHT, UL + LEFT]
        )

        p3.points.apply_complex_fn(lambda v: complex(v.imag, v.real))
        self.assertNparrayClose(
            p3.points.get(),
            [DR + LEFT, DR + RIGHT, DR + UP, DR + DOWN]
        )

        p3.points.apply_matrix([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 2]
        ])
        self.assertNparrayClose(
            p3.points.get(),
            np.array([DR + LEFT, DR + RIGHT, DR + UP, DR + DOWN]) * 2
        )

        p3.points.apply_matrix([
            [2, 0],
            [0, 2]
        ])
        self.assertNparrayClose(
            p3.points.get(),
            np.array([DR + LEFT, DR + RIGHT, DR + UP, DR + DOWN]) * 4
        )

        with self.assertRaises(InvaildMatrixError):
            p3.points.apply_matrix([
                [1, 1, 1],
                [1, 1, 1]
            ])

        with self.assertRaises(InvaildMatrixError):
            p3.points.apply_matrix([[1]])

        with self.assertRaises(InvaildMatrixError):
            p3.points.apply_matrix([
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1]
            ])

    def test_put_start_and_end_on(self) -> None:
        p = Points(UP).do(lambda p: p.points.extend([RIGHT, DOWN]))

        self.assertNparrayEqual(p.points.get(), [UP, RIGHT, DOWN])

        p.points.put_start_and_end_on(LEFT, RIGHT)
        self.assertNparrayClose(p.points.get(), [LEFT, UP, RIGHT])

        p.points.put_start_and_end_on(DOWN * 2, UP * 2)
        self.assertNparrayClose(p.points.get(), [DOWN * 2, LEFT * 2, UP * 2])

        p.points.extend([DOWN * 2])
        with self.assertRaises(PointError):
            p.points.put_start_and_end_on(LEFT, RIGHT)

    def test_movement(self) -> None:
        p1 = Points(UP, DOWN).add(
            p2 := Points(LEFT, RIGHT),
            p3 := Points()
        )

        p1.points.shift(LEFT)

        self.assertNparrayEqual(p1.points.get(), [UL, DL])
        self.assertNparrayEqual(p2.points.get(), [LEFT * 2, ORIGIN])

        p1.points.shift(RIGHT, root_only=True)

        self.assertNparrayEqual(p1.points.get(), [UP, DOWN])
        self.assertNparrayEqual(p2.points.get(), [LEFT * 2, ORIGIN])

        p2.points.shift(RIGHT)

        self.assertNparrayEqual(p1.points.get(), [UP, DOWN])
        self.assertNparrayEqual(p2.points.get(), [LEFT, RIGHT])

        p1.points.set_x(2)

        self.assertNparrayEqual(
            p1.points.get_all(),
            [UP + RIGHT * 2, DOWN + RIGHT * 2, RIGHT, RIGHT * 3]
        )

        p1.points.set_y(-1)

        self.assertNparrayEqual(
            p1.points.get_all(),
            [RIGHT * 2, DOWN * 2 + RIGHT * 2, DOWN + RIGHT, DOWN + RIGHT * 3]
        )

        p1.points.set_z(1)

        self.assertNparrayEqual(
            p1.points.get_all(),
            [RIGHT * 2 + OUT, DOWN * 2 + RIGHT * 2 + OUT, DOWN + RIGHT + OUT, DOWN + RIGHT * 3 + OUT]
        )

        p1.points.to_center()

        self.assertNparrayEqual(
            p1.points.get_all(),
            [UP, DOWN, LEFT, RIGHT]
        )

        pp1 = Points(UP, DOWN)
        pp1.points.next_to(p1, RIGHT, buff=0.5)

        self.assertNparrayEqual(pp1.points.get(), [UP + RIGHT * 1.5, DOWN + RIGHT * 1.5])

        pp1.points.next_to(p1, DL, buff=0.5)
        self.assertNparrayEqual(
            pp1.points.get(),
            [DL * 1.5, DL * 1.5 + DOWN * 2]
        )

        pp1.points.move_to(p1)
        self.assertNparrayEqual(
            pp1.points.get(),
            [UP, DOWN]
        )


class NamedGroupTest(unittest.TestCase):
    def test_named_group(self) -> None:
        group = NamedGroup(
            a=NamedGroup(
                b=Item(),
                c=Item()
            ),
            d=Item()
        )
        self.assertIs(group['a'], group[0])
        self.assertIs(group['a']['b'], group[0][0])
        self.assertIs(group['a']['c'], group[0][1])
        self.assertIs(group['d'], group[1])

        group2 = group.copy()
        self.assertIs(group2['a'], group2[0])
        self.assertIs(group2['a']['b'], group2[0][0])
        self.assertIs(group2['a']['c'], group2[0][1])
        self.assertIs(group2['d'], group2[1])

        # group2: [a, d]

        group2.add(e=Item())
        self.assertIs(group2['e'], group2[-1])

        group2.add(f=Item(), prepend=True)
        self.assertIs(group2['f'], group2[0])

        # group2: [f a d e]

        group2.insert(1, g=Item())
        self.assertIs(group2['g'], group2[1])

        # group2: [f g a d e]

        self.assertIs(group2['g'], group2[1])
        self.assertIs(group2['e'], group2[4])
        group2.remove(group2['f'])
        self.assertIs(group2['g'], group2[0])
        self.assertIs(group2['a'], group2[1])
        self.assertIs(group2['d'], group2[2])
        self.assertIs(group2['e'], group2[3])

        # group2: [g a d e]

        prev_mapping = group2.resolve()
        group2.shuffle()
        curr_mapping = group2.resolve()
        self.assertEqual(prev_mapping, curr_mapping)

        group2.remove('a')
        with self.assertRaises(GetItemError):
            group2['a']
