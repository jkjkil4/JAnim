# flake8: noqa
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
