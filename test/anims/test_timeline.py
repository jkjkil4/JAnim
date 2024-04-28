from __future__ import annotations

import inspect
import unittest
from typing import Self

from janim.anims.timeline import Timeline
from janim.components.component import CmptInfo, Component
from janim.constants import LEFT, RIGHT
from janim.exception import (NotAnimationError, RecordFailedError,
                             RecordNotFoundError, TimelineLookupError)
from janim.items.item import Item
from janim.items.points import Points


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

            def not_changed(self, other: MyCmpt) -> bool:
                return self.value == other.value

            def become(self, other): ...

        class MyItem(Item):
            cmpt = CmptInfo(MyCmpt)

        class MyTimeline(Timeline):
            def construct(self) -> None:
                item1 = MyItem()
                self.track(item1)
                item1.cmpt.value = 114

                self.forward(2)

                item1.cmpt.value = 514

                item2 = MyItem()
                self.track(item2)
                item2.cmpt.value = 1919

                self.forward(1)

                with testcase_self.assertRaises(ValueError):
                    self.forward(-1)

                item2.cmpt.value = 810

                self.forward_to(40)

                self.item1, self.item2 = item1, item2

                self.item3 = MyItem()

        tl = MyTimeline()
        tl.build(quiet=True)

        self.assertEqual(len(tl.items_history[tl.item1].history.lst), 2)
        self.assertEqual(len(tl.items_history[tl.item2].history.lst), 2)

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
                item.current(as_time=t).cmpt.value,
                val,
                msg=f'check_data_at_time {id(item):X} {t} {val}'
            )

        with self.assertRaises(RecordNotFoundError):
            tl.items_history[tl.item3].history.get(1)

    def test_fmt_time(self) -> None:
        self.assertEqual(  '     21s      ', Timeline.fmt_time(21))
        self.assertEqual(  '     59s      ', Timeline.fmt_time(59))
        self.assertEqual(  '  1m  0s      ', Timeline.fmt_time(60))
        self.assertEqual(  ' 31m 31s 237ms', Timeline.fmt_time(31 * 60 + 31.23666))
        self.assertEqual(  ' 37m  2s 234ms', Timeline.fmt_time(37 * 60 + 2.23444))
        self.assertEqual('3h 37m  2s 234ms', Timeline.fmt_time(3 * 60 * 60 + 37 * 60 + 2.23444))

    def test_blank_timeline(self) -> None:
        class MyTimeline(Timeline):
            def construct(self) -> None:
                pass

        anim = MyTimeline().build(quiet=True)

        self.assertGreater(anim.global_range.duration, 0)

    def test_exceptions(test) -> None:
        test.assertIs(Timeline.get_context(raise_exc=False), None)

        with test.assertRaises(TimelineLookupError):
            Timeline.get_context()

        class MyTimeline(Timeline):
            def construct(self) -> None:
                p = Points(LEFT, RIGHT)

                test.assertEqual(self.get_lineno_at_time(0), -1)

                with test.assertRaises(NotAnimationError):
                    self.prepare(p.points.shift(LEFT))

                self.prepare(p.anim.points.shift(LEFT))
                self.forward(0.5)
                lineno1 = inspect.currentframe().f_lineno - 1

                self.forward(0.2)
                lineno2 = inspect.currentframe().f_lineno - 1

                test.assertEqual(self.get_lineno_at_time(0.4), lineno1)
                test.assertEqual(self.get_lineno_at_time(0.6), lineno2)

                with test.assertRaises(RecordFailedError):
                    self.play(p.anim.points.shift(RIGHT))

                with test.assertRaises(RecordFailedError):
                    p.points.shift(RIGHT * 2)
                    self.forward()

        MyTimeline().build(quiet=True)

