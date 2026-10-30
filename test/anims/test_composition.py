# fmt: off
import unittest

from janim.anims_core.animation import Animation
from janim.anims.composition import Aligned, AnimGroup, Succession
from janim.exception import AnimGroupError, AnimationError
from janim.timeline import Timeline
from janim.anims_core.time import TimeRange
from janim.utils.rate_functions import rush_from, rush_into, smooth


class TestComposition(unittest.TestCase):
    def test_composition(self) -> None:
        slf = self

        class MyTimeline(Timeline):
            def construct(self) -> None:
                with slf.assertRaises(AnimationError):
                    self.play(
                        Animation(at=-1)
                    )

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
                self.anim5 = AnimGroup()  # test: 空 AnimGroup
                self.anim6 = AnimGroup(  # test: 负 lag_ratio 及 offset 导致 AnimGroup 被整体后移
                    Animation(),
                    Animation(),
                    Animation(),
                    lag_ratio=-0.5,
                    offset=-0.2,
                )

                with slf.assertRaises(AnimGroupError):
                    AnimGroup(
                        AnimGroup(at=1, rate_func=smooth),
                        rate_func=smooth
                    )

                self.anim7 = AnimGroup(
                    AnimGroup(
                        Animation(rate_func=rush_into),
                        rate_func=rush_from
                    ), 
                    rate_func=smooth
                )

                self.forward(1)
                self.play(self.anim1, self.anim2, self.anim3, self.anim4, self.anim5, self.anim6)

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

        self.assertEqual(
            tl.anim5.t_range,
            TimeRange(1, 1),            
        )

        asserts(
            tl.anim6,
            TimeRange(2.4, 3.4),
            TimeRange(1.7, 2.7),
            TimeRange(1, 2),
        )

        self.assertEqual(
            tl.anim7.rate_funcs,
            [smooth],
        )

        self.assertEqual(
            tl.anim7.anims[0].rate_funcs,
            [smooth, rush_from]
        )

        self.assertEqual(
            tl.anim7.anims[0].anims[0].rate_funcs,
            [smooth, rush_from, rush_into]
        )
