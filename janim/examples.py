# flake8: noqa
from janim.imports import *


class SimpleCurveExample(Timeline):
    def construct(self) -> None:
        item1 = VItem(
            LEFT * 2, DR, UR * 3 + UP, RIGHT * 4, DR * 2, DOWN * 2, LEFT * 2,
            LEFT * 2,   # 与上一个点重复，表示开始新路径（以 DL * 3 开始）
            DL * 3, DL * 4, DOWN * 3, DL * 2, DL * 3,
        )
        item1.fill.set(alpha=0.5)
        item1.radius.set(0.02)
        item1.show()

        self.forward(0.5)
        self.play(
            item1.anim()
            .do(lambda m: m.color.set(BLUE)),
        )
        self.play(
            item1.anim()
            .do(lambda m: m.points.rotate(-90 * DEGREES)),
        )
        self.forward(0.5)
        self.play(
            self.camera.anim()
            .do(lambda c: c.points.move_to(item1.points.get_start()).scale(0.2)),
            duration=2
        )
        self.forward(0.5)
        self.play(
            self.camera.anim()
            .do(lambda c: c.points.to_center().scale(5)),
            duration=2
        )
        self.forward(1)

        item2 = VItem(LEFT, UP, RIGHT, DOWN, LEFT)
        item2.color.set(BLUE)
        item2.fill.set(alpha=0.2)

        self.play(
            Transform(item1, item2),
            duration=2
        )
        self.forward(1)
