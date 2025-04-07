import unittest

from janim.anims.animation import Animation, TimeRange
from janim.anims.composition import Succession, Aligned, AnimGroup
from janim.anims.timeline import Timeline


class TestComposition(unittest.TestCase):
    def test_succession(self) -> None:
        class MyTimeline(Timeline):
            def construct(self) -> None:
                self.anim1 = Succession(
                    Animation(),
                    Animation(duration=2),
                    Animation()
                )
                self.anim2 = Succession(
                    Animation(),
                    Animation(duration=2),
                    Animation(),
                    duration=8
                )
                self.anim3 = Succession(
                    Animation(),
                    Animation(duration=2),
                    Animation(),
                    offset=0.5
                )
                self.anim4 = Aligned(
                    Animation(),
                    Animation(duration=2),
                    Animation(at=0.5, duration=0.5)
                )
                self.forward(1)
                self.play(self.anim1, self.anim2, self.anim3, self.anim4)

        tl = MyTimeline()
        tl.build(quiet=True)

        def asserts(group: AnimGroup, *ranges: TimeRange) -> None:
            for i, (anim, range) in enumerate(zip(group.anims, ranges, strict=True)):
                self.assertEqual(anim.t_range, range, f'group[{i}]')

        asserts(
            tl.anim1,
            TimeRange(1, 2),
            TimeRange(2, 4),
            TimeRange(4, 5)
        )

        asserts(
            tl.anim2,
            TimeRange(1, 3),
            TimeRange(3, 7),
            TimeRange(7, 9)
        )

        asserts(
            tl.anim3,
            TimeRange(1, 2),
            TimeRange(2.5, 4.5),
            TimeRange(5, 6)
        )

        asserts(
            tl.anim4,
            TimeRange(1, 3),
            TimeRange(1, 3),
            TimeRange(1, 3)
        )
