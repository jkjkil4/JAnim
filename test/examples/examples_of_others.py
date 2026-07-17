# ruff: noqa
# fmt: off
from janim.imports import *


# beginmark UpdatingPhysicalBlock
class PhysicalBlock(Square):
    physic = CustomData()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.physic.set({
            'speed': ORIGIN,    # 默认静止
            'accel': ORIGIN,    # 并且没有加速度
        })

    def do_physic(self, dt: float) -> Self:
        # 根据 `speed` 与 `accel` 更新物件位置
        value = self.physic.get()

        avg_speed = value['speed'] + 0.5 * value['accel'] * dt
        shift = avg_speed * dt

        self.physic.update({ 'speed': value['speed'] + value['accel'] * dt })
        self.points.shift(shift)

        return self

    def do_physic_updater(self):
        # 将 `do_physic` 包装为 Updater
        return StepUpdater(self, lambda data, p: data.do_physic(p.dt))


class UpdatingPhysicalBlock(Timeline):
    def construct(self):
        block = PhysicalBlock()
        block.points.to_border(DL)

        # 实时显示物块的运动向量
        def vectors_updater(p):
            cur = block.current()
            pos = cur.points.box.center
            value = cur.physic.get()

            vec_speed = Vector(value['speed'] * 0.5, color=BLUE)
            vec_speed.points.shift(pos)
            vec_accel = Vector(value['accel'] * 0.5, color=RED)
            vec_accel.points.shift(pos)

            return Group(vec_speed, vec_accel)

        self.prepare(ItemUpdater(None, vectors_updater, duration=FOREVER))

        # 物块运动以及参数变更
        self.play(block.do_physic_updater())
        block.physic.set({ 'speed': np.array([4, 6, 0]), 'accel': DOWN * 4 })
        self.play(block.do_physic_updater(), duration=2)
        block.physic.update({ 'accel': LEFT * 6 })
        self.play(block.do_physic_updater(), duration=2)
# endmark UpdatingPhysicalBlock


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


class ReadVFRVideoExample(Timeline):
    def construct(self) -> None:
        video = Video('assets/VFR-fps2-fps5.mp4').show().start(speed=2)
        video.points.scale(0.8)
        self.forward(video.info.duration / 2)
