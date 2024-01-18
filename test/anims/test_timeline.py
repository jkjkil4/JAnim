from __future__ import annotations

import unittest
from typing import Self

from janim.anims.timeline import Timeline
from janim.components.component import Component, CmptInfo
from janim.items.item import Item


class TimelineTest(unittest.TestCase):
    def test_store_item_data(self) -> None:
        testcase_self = self

        class MyCmpt(Component):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.value = 0

            def copy(self) -> Self:
                # copy.copy 本身就会复制 self.value
                return super().copy()

            def __eq__(self, other: MyCmpt) -> bool:
                return self.value == other.value

        class MyItem(Item):
            cmpt = CmptInfo(MyCmpt)

        class MyTimeline(Timeline):
            def build(self) -> None:
                item1 = MyItem()
                item1.cmpt.value = 114

                self.forward(2)

                item1.cmpt.value = 514

                item2 = MyItem()
                item2.cmpt.value = 1919

                self.forward(1)

                with testcase_self.assertRaises(ValueError):
                    self.forward(-1)

                item2.cmpt.value = 810

                self.forward_to(40)

                self.item1, self.item2 = item1, item2

                self.item3 = MyItem()

        tl = MyTimeline()
        tl._build()
        tl.init_animations()

        self.assertEqual(len(tl.item_stored_datas[tl.item1]), 2)
        self.assertEqual(len(tl.item_stored_datas[tl.item2]), 2)

        self.check_data_at_time: list[tuple[MyItem, float, int]] = [
            (tl.item1, 1, 114),
            (tl.item2, 1, 1919),
            (tl.item1, 2.5, 514),
            (tl.item2, 2.5, 1919),
            (tl.item1, 3.1, 514),
            (tl.item2, 3.1, 810),
        ]

        for item, t, val in self.check_data_at_time:
            self.assertEqual(
                tl.get_stored_data_at_time(item, t).components['cmpt'].value,
                val,
                msg=f'check_data_at_time {id(item):X} {t} {val}'
            )

        with self.assertRaises(ValueError):
            tl.get_stored_data_at_time(tl.item3, 1)
