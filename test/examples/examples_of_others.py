# ruff: noqa
# fmt: off
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

            lag_ratio=1,
        )
        self.forward()


class DynamicTypstExample(Timeline):
    def construct(self) -> None:
        dtyp = DynamicTypst(
            """
            #import "@preview/cetz:0.4.2"
            #import "@preview/cetz-plot:0.1.3": *

            #let width = 1
            #let ang_deg = angle * 1deg

            #cetz.canvas({
                import cetz.draw: *

                stroke((thickness: 0.7pt, join: "round", paint: white))

                let (a, b, c, d) = (
                    (0, 0),
                    (width, 0),
                    (rel: (width, 0), to: (60deg, width * 3)),
                    (60deg, width * 3),
                )

                line(a, b, c, d, a)

                let ang_eab = ang_deg
                let len_ae = width / calc.sin(60deg - ang_eab) * calc.sin(120deg)
                let e = (ang_eab, len_ae)
                let g = (a, 100%, 120deg, e)
                let f = (a, 100%, 60deg, e)

                line(a, e, f, g, a)
                line(a, f)

                for (pos, rel, lab) in (
                    (a, (-1, -1.2), $A$),
                    (b, (1, -1.5), $B$),
                    (c, (1, 1), $C$),
                    (d, (-1, 1), $D$),
                    (f, (-.5, 1.5), $F$),
                    (g, (-1, 1), $G$),
                    (e, (1, -.5), $E$),
                ) {
                    content((pos, 17%, (rel: rel)), lab)
                }
            })
            """,
            {
                'angle': 30,
            },
            post=lambda typ: typ.points.next_to(DR * 2, UL),
        ).show()

        self.play(
            # 在使用 can_keep_structure 之前请先查看文档！
            dtyp.anim_update(angle=45, can_keep_structure=True),
            duration=2,
        )

        self.play(
            dtyp.anim_update(angle=5, can_keep_structure=True),
            duration=2,
        )
