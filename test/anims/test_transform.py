import unittest

import numpy as np

from janim.anims.animation import Animation, TimeRange
from janim.anims.timeline import Timeline
from janim.anims.transform import Transform
from janim.constants import DOWN, LEFT, RIGHT, UP
from janim.items.points import Points
from janim.utils.data import ContextSetter
from janim.utils.rate_functions import linear


class TransformTest(unittest.TestCase):
    def assertNparrayEqual(self, np1, np2):
        self.assertListEqual(np.array(np1).tolist(), np.array(np2).tolist())

    def assertNparrayClose(self, np1, np2):
        np1 = np.array(np1)
        np2 = np.array(np2)
        self.assertListEqual(np.isclose(np1, np2).tolist(), np.full(np1.shape, True).tolist())

    def test_transform(self) -> None:
        tsf_anim: Transform = None
        p1: Points = None
        p2: Points = None

        class MyTimeline(Timeline):
            def construct(self) -> None:
                nonlocal tsf_anim, p1, p2

                p1 = Points(UP * 2, DOWN * 2)
                p2 = Points(LEFT, RIGHT)

                self.show(p1)

                self.forward(2)

                p1.points.set([UP, DOWN])

                self.play(tsf_anim := Transform(p1, p2, rate_func=linear))  # duration: 1

                p2.points.set([LEFT * 2, RIGHT * 2])

                self.forward(1)

        tl = MyTimeline()
        built = tl.build(quiet=True)

        self.assertEqual(tsf_anim.t_range, TimeRange(2, 3))

        def tsf_anim_at(global_t: float):
            with ContextSetter(Animation.global_t_ctx, global_t):
                for data, render in tsf_anim.additional_calls:
                    render(data)

        tsf_anim_at(2)
        self.assertNparrayEqual(
            tsf_anim.aligned[(p1, p2)].union.points.get(),
            [UP, DOWN]
        )

        tsf_anim_at(3)
        self.assertNparrayClose(
            tsf_anim.aligned[(p1, p2)].union.points.get(),
            [LEFT, RIGHT]
        )

        tsf_anim_at(2.3)
        self.assertNparrayClose(
            tsf_anim.aligned[(p1, p2)].union.points.get(),
            [UP * 0.7 + LEFT * 0.3, DOWN * 0.7 + RIGHT * 0.3]
        )

        self.assertEqual(tsf_anim.t_range.at, 2)
        self.assertEqual(tsf_anim.t_range.end, 3)
