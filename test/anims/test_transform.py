import unittest
import numpy as np

from janim.anims.animation import TimeRange
from janim.anims.timeline import Timeline
from janim.anims.transform import Transform
from janim.components.points import Cmpt_Points
from janim.constants import DOWN, LEFT, RIGHT, UP
from janim.items.points import Points


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
            def build(self) -> None:
                nonlocal tsf_anim, p1, p2

                p1 = Points(UP * 2, DOWN * 2)
                p2 = Points(LEFT, RIGHT)

                self.forward(2)

                p1.points.set([UP, DOWN])

                self.play(tsf_anim := Transform(p1, p2))  # duration: 1

                p2.points.set([LEFT * 2, RIGHT * 2])

        tl = MyTimeline()
        tl._build()
        tl.init_animations()

        self.assertEqual(tsf_anim.global_range, TimeRange(2, 1))

        tsf_anim.anim_on_alpha(0)
        self.assertNparrayEqual(
            tsf_anim.aligned[(p1, p2)].union.components['points'].get(),
            [UP, DOWN]
        )

        tsf_anim.anim_on_alpha(1)
        self.assertNparrayEqual(
            tsf_anim.aligned[(p1, p2)].union.components['points'].get(),
            [LEFT, RIGHT]
        )

        tsf_anim.anim_on_alpha(0.3)
        self.assertNparrayEqual(
            tsf_anim.aligned[(p1, p2)].union.components['points'].get(),
            [UP * 0.7 + LEFT * 0.3, DOWN * 0.7 + RIGHT * 0.3]
        )




