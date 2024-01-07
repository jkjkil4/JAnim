import unittest

import janim.utils.refresh as refresh
from janim.utils.signal import Signal
from janim.items.item import Item
from janim.components.component import Component
from janim.components.points import Cmpt_Points


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
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                with Component.Binder():
                    self.cmpt = MyCmpt()

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

    def test_component(self) -> None:
        class MyItem(
            Item[
                Cmpt_Points,
                Cmpt_Points
            ]
        ):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                with Component.Binder():
                    self.points1 = Cmpt_Points(apply=True)
                    self.points2 = Cmpt_Points(apply=True, get=True)

                print(self.points2)
                print(self.get.all_points())

        MyItem()


if __name__ == '__main__':
    unittest.main()
