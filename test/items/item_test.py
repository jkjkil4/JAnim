import unittest

import janim.utils.refresh as refresh
from janim.utils.signal import Signal
from janim.items.item import Item
from janim.components.component import Component


class ItemTest(unittest.TestCase):
    def test_broadcast_refresh(self) -> None:
        called_list = []

        class MyComp(Component):
            @Signal
            def points_changed(self):
                called_list.append(self.points_changed)
                MyComp.points_changed.emit(self)

            @points_changed.self_refresh_with_recurse(recurse_up=True)
            @refresh.register
            def bbox(self):
                called_list.append(self.bbox)

        class MyItem(Item):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                with Component.Binder():
                    self.comp = MyComp()

        m1 = MyItem().add(
            m2 := MyItem().add(
                m3 := MyItem()
            ),
            m4 := MyItem()
        )

        m: MyItem

        for m in [m1, *m1.descendants()]:
            m.comp.bbox()

        m2.comp.points_changed()

        for m in [m1, *m1.descendants()]:
            m.comp.bbox()

        m3.comp.points_changed()

        for m in [m1, *m1.descendants()]:
            m.comp.bbox()

        self.assertEqual(
            called_list,
            [
                m1.comp.bbox, m2.comp.bbox, m3.comp.bbox, m4.comp.bbox,
                m2.comp.points_changed,
                m1.comp.bbox, m2.comp.bbox,
                m3.comp.points_changed,
                m1.comp.bbox, m2.comp.bbox, m3.comp.bbox
            ]
        )


if __name__ == '__main__':
    unittest.main()
