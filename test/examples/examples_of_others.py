# flake8: noqa
from janim.imports import *


class RectClipExample(Timeline):
    def construct(self):
        ANCHOR = LEFT * 2

        plane = NumberPlane(faded_line_ratio=1)
        dot = Dot(ANCHOR)
        txt = Text('Anchor')
        txt.points.next_to(dot, UP, buff=SMALL_BUFF)

        rect = RectClip(plane, dot, txt, anchor=ANCHOR, border=True)
        self.show(plane, dot, txt, rect)

        self.forward()
        self.play(
            rect.anim.points.scale([0.3, 0.5, 1]),
            rect.anim.points.shift(LEFT * 2),
            rect.anim.points.shift(UR),

            rect.anim.transform.set(scale=1.5, rotate=20 * DEGREES),
            Wait(0.5),
            rect.anim.transform.set(scale=1, rotate=0),

            rect.anim.set_center_on().color.set(RED),

            rect.anim.transform.set(scale=1.5, rotate=20 * DEGREES),
            Wait(0.5),
            rect.anim.transform.set(scale=1, rotate=0),
            lag_ratio=1
        )
        self.forward()
