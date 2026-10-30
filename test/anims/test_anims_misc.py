import unittest

from janim.anims.fading import FadeIn
from janim.anims.indication import ApplyWave, Indicate, WiggleOutThenIn
from janim.anims.movement import MoveAlongPath
from janim.exception import JAnimException
from janim.items.geometry.line import Line
from janim.items.group import Group
from janim.items.item import Item
from janim.timeline import Timeline


class TestAnimsMisc(unittest.TestCase):
    def test_anims_misc(self) -> None:
        slf = self

        class MyTimeline(Timeline):
            def construct(self) -> None:
                with slf.assertRaises(JAnimException):
                    FadeIn(Item(), Item())  # type: ignore

                self.play(
                    FadeIn(Item(), skip_null_items=False),
                    MoveAlongPath(Item(), Line(), skip_null_items=False),
                    Indicate(Group(Item(), Item()), root_only=False, skip_null_items=False),
                    ApplyWave(Item(), skip_null_items=False),
                    WiggleOutThenIn(Item(), skip_null_items=False),
                )

        MyTimeline().build(quiet=True)
