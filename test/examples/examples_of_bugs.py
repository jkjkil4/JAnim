# flake8: noqa
# fmt: off
import random

from janim.imports import *


class TestSuccessionFadeOutBug(Timeline):
    def construct(self) -> None:
        circle = Circle()

        random.seed(114514)

        for i in range(10):
            self.prepare(FadeIn(circle), duration=0.32)
            self.schedule(self.current_time + 0.32, circle.hide)
            self.forward(0.5)

            self.play(
                Succession(
                    Create(circle),
                    FadeOut(circle, duration=0.9 + 0.2 * random.random())
                ),
                duration=0.9 + 0.2 * random.random()
            )
            self.forward(0.3)


class TestFloatInpreciseBug(Timeline):
    def construct(self):
        circle = Circle()

        self.schedule(0.1 + 0.2, circle.show)
        self.schedule(0.3, circle.hide)
        self.forward()


class TestIndicateSubitem(Timeline):
    def construct(self):
        text = Text('abcdefg', font_size=60)

        self.play(
            text.anim.points.shift(RIGHT * 2),
            CircleIndicate(text[0][2:5])
        )


class TestNamedGroup(Timeline):
    def construct(self) -> None:
        number_plane = NumberPlane((-2, 2), (-2, 2))
        group = NamedGroup(plane=number_plane).copy().show()
        group.points.rotate(1)

        self.forward(0.5)
        self.play(
            group['plane'].background_lines(VItem).anim.stroke.set(color=RED)
        )
        self.forward(0.5)
        self.hide_all()

        number_plane_src = NumberPlane((-2, 2), (-2, 2))

        group_src = NamedGroup(plane=number_plane_src)

        group_1 = group_src.copy()
        group_2 = group_src.copy()

        group_1.save_state('initial')
        group_2.save_state('initial')

        group_1.load_state('initial')
        group_2.load_state('initial')
        
        # should not raise Exception
        group_1['plane'].get_origin()
        group_2['plane'].get_origin()
