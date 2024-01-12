import unittest

import janim.utils.refresh as refresh
from janim.utils.signal import Signal
from janim.items.item import Item, Group, Points
from janim.components.component import Component, CmptInfo
from janim.constants.coord import *


class ItemTest(unittest.TestCase):
    def test_broadcast_refresh(self) -> None:
        called_list = []

        class MyCmpt(Component):
            @Signal
            def points_changed(self):
                called_list.append(self.points_changed)
                MyCmpt.points_changed.emit(self)

            @points_changed.self_refresh_with_recurse(recurse_up=True)
            @refresh.register
            def bbox(self):
                called_list.append(self.bbox)

        class MyItem(Item):
            cmpt = CmptInfo(MyCmpt)

        m1 = MyItem().add(
            m2 := MyItem().add(
                m3 := MyItem()
            ),
            m4 := MyItem()
        )

        m: MyItem

        for m in [m1, *m1.descendants()]:
            m.cmpt.bbox()

        m2.cmpt.points_changed()

        for m in [m1, *m1.descendants()]:
            m.cmpt.bbox()

        m3.cmpt.points_changed()

        for m in [m1, *m1.descendants()]:
            m.cmpt.bbox()

        self.assertEqual(
            called_list,
            [
                m1.cmpt.bbox, m2.cmpt.bbox, m3.cmpt.bbox, m4.cmpt.bbox,
                m2.cmpt.points_changed,
                m1.cmpt.bbox, m2.cmpt.bbox,
                m3.cmpt.points_changed,
                m1.cmpt.bbox, m2.cmpt.bbox, m3.cmpt.bbox
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

        self.assertNparrayEqual(p1.data.get(), [UP, RIGHT])
        self.assertNparrayEqual(p1.data.get_all(), [UP, RIGHT, UL, DR])
        self.assertNparrayEqual(p2.data.get(), [UL])
        self.assertNparrayEqual(p2.data.get_all(), [UL])

        # g.data.get_all()    # Error
        # g.astype(Points).name_that_not_exists   # Error
        # self.assertNparrayEqual(g.astype(Points).data.get())  # Error

        self.assertNparrayEqual(g.astype(Points).data.get_all(), [UP, RIGHT, UL, DR, ORIGIN])
        self.assertNparrayEqual(g.astype(MyPoints).data.get_all(), [UP, RIGHT, UL, DR, ORIGIN])


if __name__ == '__main__':
    unittest.main()
