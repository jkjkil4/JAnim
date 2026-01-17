import unittest

import janim.utils.refresh as refresh
from janim.components.component import CmptInfo, Component
from janim.constants.coord import *
from janim.items.item import Item
from janim.items.points import Group, Points
from janim.utils.signal import Signal


class ItemTest(unittest.TestCase):
    def test_broadcast_refresh(self) -> None:
        called_list = []

        class MyCmpt(Component, impl=True):
            @Signal
            def points_changed(self):
                called_list.append(self.points_changed)
                MyCmpt.points_changed.emit(self)

            @points_changed.self_refresh_with_recurse(recurse_up=True)
            @refresh.register
            def bbox(self):
                called_list.append(self.bbox)

            @points_changed.self_refresh_with_recurse(recurse_down=True)
            @refresh.register
            def fn_down(self):
                called_list.append(self.fn_down)

        class MyItem(Item):
            cmpt = CmptInfo(MyCmpt)

        m1 = MyItem().add(
            m2 := MyItem().add(
                m3 := MyItem()
            ),
            m4 := MyItem()
        )

        m: MyItem

        self.assertEqual(m1._children[0], m1[0])
        self.assertEqual(m1._children[1], m1[1])
        self.assertListEqual(m1[:1]._children, [m2])

        for m in [m1, *m1.descendants()]:
            m.cmpt.bbox()
            m.cmpt.fn_down()

        m2.cmpt.points_changed()

        for m in [m1, *m1.descendants()]:
            m.cmpt.bbox()
            m.cmpt.fn_down()

        m3.cmpt.points_changed()

        for m in [m1, *m1.descendants()]:
            m.cmpt.bbox()
            m.cmpt.fn_down()

        self.assertEqual(
            called_list,
            [
                m1.cmpt.bbox, m1.cmpt.fn_down,
                m2.cmpt.bbox, m2.cmpt.fn_down,
                m3.cmpt.bbox, m3.cmpt.fn_down,
                m4.cmpt.bbox, m4.cmpt.fn_down,

                m2.cmpt.points_changed,

                m1.cmpt.bbox,
                m2.cmpt.bbox, m2.cmpt.fn_down,
                              m3.cmpt.fn_down,

                m3.cmpt.points_changed,

                m1.cmpt.bbox,
                m2.cmpt.bbox,
                m3.cmpt.bbox, m3.cmpt.fn_down
            ]
        )


class PointsTest(unittest.TestCase):
    def assertNparrayEqual(self, d1, d2) -> None:
        self.assertEqual(np.array(d1).tolist(), np.array(d2).tolist())

    def test_get_all(self) -> None:
        class MyPoints(Points): ...

        g = Group(
            p1 := MyPoints(UP, RIGHT).add(
                p2 := Points(UL),
                p3 := Points(DR)
            ),
            p4 := Points(ORIGIN)
        )

        self.assertNparrayEqual(p1.points.get(), [UP, RIGHT])
        self.assertNparrayEqual(p1.points.get_all(), [UP, RIGHT, UL, DR])
        self.assertNparrayEqual(p2.points.get(), [UL])
        self.assertNparrayEqual(p2.points.get_all(), [UL])

        self.assertNparrayEqual(g.astype(Points).points.get_all(), [UP, RIGHT, UL, DR, ORIGIN])
        self.assertNparrayEqual(g.astype(MyPoints).points.get_all(), [UP, RIGHT, UL, DR, ORIGIN])

        p1.points.extend([LEFT])
        self.assertNparrayEqual(g.astype(Points).points.get_all(), [UP, RIGHT, LEFT, UL, DR, ORIGIN])
