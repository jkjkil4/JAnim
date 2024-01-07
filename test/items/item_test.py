import unittest

import janim.utils.refresh as refresh
from janim.utils.signal import Signal
from janim.items.item import Item, Group
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

    def test_component_apply(self) -> None:
        called_list = []

        class MyCmpt(Component):
            @Component.for_many
            def inc_value(self, *, _as: Item = None):
                if _as is None:
                    _as = self.bind.item

                called_list.append((self, _as))

        class MyItem[GT, AT](Item[MyCmpt | GT, MyCmpt | AT]):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                with Component.Binder():
                    self.c1 = MyCmpt(apply=True, get=True)
                    self.c2 = MyCmpt(apply=True)

        g = Group(
            m1 := MyItem().add(
                m2 := MyItem()
            )
        )

        m1.c1.inc_value()
        m2.c1.inc_value()

        m2.apply.inc_value()

        g.apply.inc_value()

        self.assertEqual(
            called_list,
            [
                (m1.c1, m1),
                (m2.c1, m2),

                (m2.c1, m2),
                (m2.c2, m2),

                (m1.c1, g),
                (m1.c2, g)
            ]
        )


if __name__ == '__main__':
    unittest.main()
