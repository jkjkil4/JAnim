# flake8: noqa
# fmt: off
from janim.imports import *


# 在该文件中，只有以 Test_ 为前缀的 Timeline 才会被提取作为样例


class _BatchOfTests(Timeline):
    lst: list[type[Timeline]] = []
    alpha: float = 1

    def construct(self) -> None:
        tls = [cls().build().to_item().show() for cls in self.lst]
        effects = [AlphaEffect(tl).show().alpha.set(self.alpha).r for tl in tls]

        self.forward(max(tl.duration for tl in tls))


class BasicAnimationExampleWithParams(Timeline):
    def construct(self) -> None:
        circle = Circle()
        star = Star()

        self.forward()

        self.play(Create(circle, duration=0.8, rate_func=rush_from))
        self.play(
            circle.anim(rate_func=ease_out_bounce)
                .points.shift(LEFT * 3).scale(1.5)
        )
        self.play(
            circle.anim(duration=2)
                .set(color=RED, fill_alpha=0.5)
        )

        self.play(SpinInFromNothing(star, duration=0.6, rate_func=rush_from))
        self.play(
            star.anim(rate_func=ease_out_bounce)
                .points.shift(RIGHT * 3).scale(1.5)
        )
        self.play(
            star.anim(duration=2)
                .set(color=YELLOW, fill_alpha=0.5)
        )

        self.forward()


class GroupedAnimation(Timeline):
    def construct(self) -> None:
        circle = Circle()
        circle.points.to_border(UL, buff=LARGE_BUFF)

        square = Square()
        square.points.to_border(DL, buff=LARGE_BUFF)

        self.play(
            FadeIn(circle),
            FadeIn(square)
        )
        self.play(
            circle.anim
                .points.to_border(UR, buff=LARGE_BUFF),
            square.anim(at=0.2)
                .points.to_border(DR, buff=LARGE_BUFF)
        )


class ComplexGroupedAnimation(Timeline):
    def construct(self) -> None:
        circle = Circle()
        circle.points.to_border(UL, buff=LARGE_BUFF)

        square = Square()
        square.points.to_border(DL, buff=LARGE_BUFF)

        self.play(
            FadeIn(circle),
            FadeIn(square)
        )
        self.play(
            Succession(
                circle.anim(rate_func=rush_into)
                    .points.to_border(UR, buff=LARGE_BUFF),
                square.anim(rate_func=rush_from)
                    .points.to_border(DR, buff=LARGE_BUFF),
                duration=3
            ),
            AnimGroup(
                ShowCreationThenDestructionAround(circle),
                ShowCreationThenDestructionAround(square),
                at=0.5,
                duration=2
            )
        )


class PrepareAnimation(Timeline):
    def construct(self) -> None:
        txt = Text('JAnim')
        txt.points.shift(LEFT * 2)

        self.prepare(
            CircleIndicate(txt),
            at=1,
            duration=2
        )

        self.play(txt.anim.points.shift(RIGHT * 4).scale(2), duration=2)
        self.play(txt.anim.points.shift(LEFT * 4).scale(0.5), duration=2)


class CompositionControl(Timeline):
    def construct(self) -> None:
        dot = Dot(RIGHT * 2).show()
        txt = Text('just a dot').show()
        txt.points.next_to(dot, DOWN)

        star = Star(start_angle=0, outer_radius=2)
        star.points.shift(dot.points.box.center - star.points.get()[0])

        txt1 = Text('Rotating...', font_size=60, color=GREY_D, depth=1)
        txt2 = Text('Drawing a star!', font_size=60, color=GREY_D, depth=1)

        self.forward()
        self.play(
            Aligned(
                Succession(
                    Do(txt1.show),
                    Rotate(dot, TAU, about_point=ORIGIN, duration=2),
                    Do(txt1.hide),
                    Wait(0.5),
                    Do(txt2.show),
                    AnimGroup(
                        MoveAlongPath(dot, star),
                        Create(star, auto_close_path=False),
                        duration=2
                    ),
                    Do(txt2.hide)
                ),
                Follow(txt, dot, DOWN)
            )
        )
        self.forward()


class Test_Tutorial_Animations(_BatchOfTests):
    lst = [
        BasicAnimationExampleWithParams, GroupedAnimation, ComplexGroupedAnimation, PrepareAnimation, CompositionControl,
    ]
    alpha = 0.5


class GroupExample1(Timeline):
    def construct(self) -> None:
        group = Group(
            Star(), Circle(), RegularPolygon(6),
            color=BLUE,
            fill_alpha=1
        )
        group.points.arrange(RIGHT, buff=MED_LARGE_BUFF)

        self.play(FadeIn(group))
        self.play(group(VItem).anim.fill.fade(0.7))
        self.play(Rotate(group, TAU), duration=3)
        self.play(FadeOut(group, lag_ratio=0.5))


class GroupExample2(Timeline):
    def construct(self) -> None:
        group = Group(
            Star(color=GOLD, fill_alpha=0.5),
            Circle(color=RED),
            RegularPolygon(6, color=BLUE, fill_alpha=0.5),
        )
        group.points.arrange(RIGHT, buff=MED_LARGE_BUFF)

        self.play(FadeIn(group))

        self.play(Indicate(group))
        for sub in group:
            self.play(Indicate(sub))

        self.play(group[1].anim.fill.set(alpha=0.5))

        self.play(FadeOut(group, lag_ratio=0.5))


class NestedGroupExample(Timeline):
    def construct(self) -> None:
        txt = Text('self.play(Transform(circle, square))')

        shapes = Group(
            Circle(color=BLUE),
            Arrow(color=YELLOW),
            Square(color=GREEN, fill_alpha=0.5)
        )
        shapes.points.scale(0.5).arrange(RIGHT, buff=MED_LARGE_BUFF)

        group = Group(txt, shapes)
        group.points.arrange(DOWN, aligned_edge=LEFT)

        self.play(Write(group))
        self.forward(0.5)
        self.play(
            FadeOut(txt),
            FadeOut(shapes[1:]),
            shapes[0].anim.points.scale(2).to_center()
        )
        self.play(
            Transform(shapes[0], Square(color=GREEN, fill_alpha=0.5))
        )


class Test_Tutorial_ItemGroup(_BatchOfTests):
    lst = [
        GroupExample1, GroupExample2, NestedGroupExample,
    ]
    alpha = 0.7


class BasicDataUpdater(Timeline):
    def construct(self) -> None:
        square = Square()

        self.play(
            DataUpdater(
                square,
                lambda data, p: data.points.rotate(p.alpha * PI)
            ),
            duration=3
        )


class BasicGroupUpdater(Timeline):
    def construct(self) -> None:
        squares = Square() * 2  # 与 squares = Group(Square(), Square()) 基本等价
        squares.points.arrange()

        self.play(
            GroupUpdater(
                squares,
                lambda group, p: group.points.rotate(p.alpha * PI)
            ),
            duration=3
        )


class DataUpdaterVsGroupUpdater(Timeline):
    def construct(self) -> None:
        squares1 = Square() * 2
        squares1.points.arrange()

        squares2 = squares1.copy()

        group = Group(
            Text('DataUpdater'), Text('GroupUpdater'),
            squares1, squares2
        ).show()
        group.points.arrange_in_grid(buff=LARGE_BUFF)

        self.play(
            DataUpdater(
                squares1,
                lambda data, p: data.points.rotate(p.alpha * PI),
                root_only=False
            ),
            GroupUpdater(
                squares2,
                lambda data, p: data.points.rotate(p.alpha * PI)
            ),
            duration=4
        )


class ForeverUpdater(Timeline):
    def construct(self) -> None:
        square = Square().show()

        self.forward()

        self.prepare(
            DataUpdater(
                square,
                lambda data, p: data.points.rotate(p.elapsed * 60 * DEGREES),
                duration=FOREVER
            )
        )

        self.prepare(
            DataUpdater(
                square,
                lambda data, p: data.points.set_x(2 * math.sin(p.alpha * TAU)),
                become_at_end=False
            ),
            at=2,
        )

        self.forward(5)


class SimplestStepUpdater(Timeline):
    def construct(self) -> None:
        NumberPlane(faded_line_ratio=1).show()

        circle = Circle(0.5, color=YELLOW, fill_alpha=0.6).show()

        self.forward()
        self.play(
            StepUpdater(
                circle,
                lambda data, p: data.points.shift(RIGHT / 50)
            ),
            duration=2
        )
        self.forward()


class DynamicNumber(Timeline):
    def construct(self) -> None:
        tr = ValueTracker(0)
        txt = Text('0.00', font_size=40).show()

        self.forward()
        self.play(
            Succession(
                tr.anim.set_value(4),
                tr.anim.set_value(2.5),
                tr.anim.set_value(10)
            ),
            ItemUpdater(
                txt,
                lambda p: Text(f'{tr.current().get_value():.2f}', font_size=40),
                duration=3
            )
        )
        self.forward()


class Test_Tutorial_Updaters(_BatchOfTests):
    lst = [
        BasicDataUpdater,
        BasicGroupUpdater,
        DataUpdaterVsGroupUpdater,
        ForeverUpdater,
        SimplestStepUpdater,
        DynamicNumber,
    ]
    alpha = 0.5


class DoDetectChange(Timeline):
    def construct(self) -> None:
        circle = Circle().show()

        self.play(
            Wait(),
            # 在没有 detect_changes，无法侦测到 circle 变为了红色，所以不会在画面上体现
            Do(lambda: circle.set(color=RED), detect_changes=False),
            Wait(),
            Do(lambda: circle.set(color=BLUE)),
            Wait(),
            lag_ratio=1,
        )


class _BPMExample(Timeline):
    def construct(self) -> None:
        SQUARE_COUNT = 3
        LOOP_COUNT = 5

        # Place the three squares on the right
        squares = Square() * SQUARE_COUNT
        squares.show()
        squares.points.arrange(DOWN).to_border(RIGHT)

        # Blink once per "second"
        for i in range(LOOP_COUNT):
            for square in squares:
                self.forward()
                square.set(fill_alpha=int(i % 2 == 0))
        self.forward()


class BPMExample(Timeline):
    def construct(self) -> None:
        # This is only for showing the source code in the top-left corner; it can be ignored
        src1 = SourceDisplayer(_BPMExample).show()
        src2 = SourceDisplayer(BPMExample).show()
        src2.points.next_to(src1, DOWN, aligned_edge=LEFT)

        # BPM setting
        BPM = 180
        BPS = BPM / 60

        # Play _BPMExample at BPS speed so it matches the BPM
        tl = _BPMExample().build().to_playback_control_item().show()
        tl.start(speed=BPS)
        self.forward(tl.duration / BPS)


class TestPixelText(Timeline):
    def construct(self) -> None:
        txt1 = Text('Lorem ipsum').show().points.shift(UP * 2).r

        txt2 = Text('Lorem ipsum', render='pixel').show().points.shift(DOWN * 2).r

        self.play(
            txt1.anim.points.scale(2),
            txt2.anim.points.scale(2),
        )
        self.play(
            FadeIn(txt1),
            FadeIn(txt2),
        )
        self.play(
            txt1.anim.set(color=RED),
            txt2.anim.set(color=RED),
        )

        self.play(
            self.camera.anim.points.set(orientation=quat(0.42, -0.09, -0.18, 0.89))
        )


class TestVItemRendering(Timeline):
    def construct(self) -> None:
        # VItemPlaneRenderer
        vitem1 = Ellipse()

        # VItemCurveRenderer
        vitem2 = Ellipse().apply_depth_test()

        # ArrowRenderer
        vitem3 = Arrow(LEFT * 2, RIGHT * 2, path_arc=30 * DEGREES)
        vitem4 = Arrow(LEFT * 2, RIGHT * 2, path_arc=30 * DEGREES, alpha=0.5)

        group = Group(vitem1, vitem2, vitem3, vitem4).show()
        group.points.arrange(DOWN)

        self.forward(0.5)
        self.play(
            self.camera.anim.points.set(orientation=quat(0.44, 0.09, 0.17, 0.87))
        )
        self.forward(0.5)


class Indication(Timeline):
    def construct(self) -> None:
        x = TypstMath('x y z w').show()
        x.points.shift(UL * 2)
        self.play(
            CircleIndicate(x),
            CircleIndicate(x, scale=2, circle_kwargs={'stroke_color': RED, 'alpha': 0.6})
        )
        x.hide()

        items1 = Star(color=GOLD, fill_alpha=0.75) * 3
        items1.points.arrange_by_offset(RIGHT * 2).shift(UP * 2)

        items2 = items1.copy().fix_in_frame()
        items2.points.shift(DOWN * 4)

        anims = [FocusOn, CircleIndicate, ShowPassingFlashAround]

        self.play(Write(items1), Write(items2), duration=0.5)
        self.camera.save_state()
        self.camera.points.set(orientation=quat(0.43, -0.1, -0.21, 0.87))
        self.play(
            *[
                AnimGroup(anim(item1), anim(item2))
                for item1, item2, anim in zip(items1, items2, anims)
            ]
        )

        self.hide(items1, items2)
        self.camera.load_state()

        item = Star()
        item.points.shift(DL)
        item.add(Star())
        item.set(fill_alpha=0.5)

        items1 = item * 2
        items1.points.arrange_by_offset(RIGHT * 4).shift(UP * 2)

        items2 = items1.copy()
        items2.points.shift(DOWN * 4)

        self.play(Write(items1), Write(items2), duration=0.5)
        self.play(
            ApplyWave(items1[0]), WiggleOutThenIn(items1[1]),
            ApplyWave(items2[0], root_only=True), WiggleOutThenIn(items2[1], root_only=True),
        )


class Creation(Timeline):
    def construct(self) -> None:
        squares = Square() * 9
        squares.points.arrange_in_grid()

        self.play(
            Create(squares, lag_ratio=0.5),
            duration=1.5
        )
        self.play(
            ShowPassingFlash(squares, time_width=0.5, lag_ratio=0.5),
            duration=1.5
        )
    
        squares.set(fill_alpha=0.5)
        self.camera.points.scale(0.5)
        self.play(
            Write(squares, stroke_radius=0.1),
            duration=1.5
        )
        self.play(
            Write(squares, stroke_radius=0.1, scale_with_camera=True),
            duration=1.5
        )


class Test_Misc1(_BatchOfTests):
    lst = [
        DoDetectChange,
        BPMExample,
        TestPixelText,
        TestVItemRendering,
        Indication,
        Creation,
    ]
    alpha = 0.6


class MotionBlurBasic(Timeline):
    CONFIG = Config(fps=30, motion_blur_samples=16, motion_blur_shutter=8 / 30)

    def construct(self) -> None:
        blurred = Square(0.8, fill_color=BLUE, fill_alpha=1, stroke_alpha=0)
        blurred.apply_motion_blur().show()
        blurred.points.shift(LEFT * 2 + UP * 1.2)

        sharp = Square(0.8, fill_color=RED, fill_alpha=1, stroke_alpha=0).show()
        sharp.points.shift(LEFT * 2 - UP * 1.2)

        Text('set_motion_blur()', font_size=26, color=BLUE).points.move_to([0, 2.6, 0]).r.show()
        Text('default: no blur', font_size=26, color=RED).points.move_to([0, -2.6, 0]).r.show()

        self.play(
            blurred.anim(rate_func=linear).points.shift(RIGHT * 4),
            sharp.anim(rate_func=linear).points.shift(RIGHT * 4),
            duration=1.6,
        )


class MotionBlurShutterDemo(Timeline):
    CONFIG = Config(fps=30, motion_blur_samples=16)

    class _Lane(Timeline):
        def __init__(self, y: float = 0.0, color: JAnimColor = WHITE):
            super().__init__()
            self.y = y
            self.color = color

        def construct(self) -> None:
            square = Square(0.75, fill_color=self.color, fill_alpha=1, stroke_alpha=0)
            square.apply_motion_blur().show()
            square.points.shift(LEFT * 2.4 + UP * self.y)
            self.play(
                square.anim(rate_func=linear).points.shift(RIGHT * 4),
                duration=1.4,
            )

    def construct(self) -> None:
        for i, (shutter, color) in enumerate(zip([0, 3 / 30, 6 / 30], [GREY, BLUE, PURPLE])):
            y = 2.2 - i * 2.2
            Text(f'shutter = {shutter:g}s', font_size=26, color=color).points.move_to(
                [-4.2, y, 0]
            ).r.show()
            with Config(motion_blur_shutter=shutter):
                self._Lane(y, color).build(quiet=True).to_item(keep_last_frame=True).show()

        self.forward(1.4)


class MotionBlurCoexistDemo(Timeline):
    CONFIG = Config(fps=30, motion_blur_samples=16, motion_blur_shutter=9 / 30)

    def construct(self) -> None:
        translucent = Circle(0.5, fill_color=TEAL, fill_alpha=0.5, stroke_alpha=0)
        translucent.apply_motion_blur().show()
        translucent.points.shift(LEFT * 2.4 + UP * 1.7)

        effected = Square(0.9, fill_color=RED, fill_alpha=0.9, stroke_alpha=0)
        effected.apply_motion_blur().show()
        effected.points.shift(LEFT * 2.4)

        frozen = Square(0.9, fill_color=GREY_D, fill_alpha=0.95, stroke_alpha=0).show()
        frozen.points.shift(LEFT * 2.4 - UP * 1.7)

        SimpleFrameEffect(
            effected,
            shader='f_color = frame_texture(v_texcoord); f_color.rgb *= vec3(0.55, 1.0, 0.85);',
        ).show()

        labels = ['translucent + blur', 'FrameEffect + blur', 'not enabled (frozen)']
        for text, y in zip(labels, [1.7, 0, -1.7]):
            Text(text, font_size=24, color=GREY).points.move_to([4.2, y, 0]).r.show()

        self.play(
            translucent.anim(rate_func=linear).points.shift(RIGHT * 4.8),
            effected.anim(rate_func=linear).points.shift(RIGHT * 4.8),
            frozen.anim(rate_func=linear).points.shift(RIGHT * 4.8),
            duration=1.6,
        )


class MotionBlurDiagram(Timeline):
    def construct(self) -> None:
        gap = 2.4  # 相邻两帧在示意图上的间距，代表 1 / fps
        shutter = 3
        samples = 8

        axis = Line([-6.4, 0, 0], [6.4, 0, 0], color=GREY)
        window = Rect(gap * shutter, 1.9, fill_color=BLUE, fill_alpha=0.18, stroke_alpha=1, color=BLUE_C)
        centers = Group(
            *[
                Line([x, -1.1, 0], [x, 1.1, 0], color=GREY)
                for x in (-4.8, -2.4, 0.0, 2.4, 4.8)
            ]
        )
        samples_group = Group(
            *[
                Circle(0.06, fill_alpha=1, stroke_alpha=0, color=YELLOW)
                .points.move_to([(i + 0.5 - samples / 2) * gap * shutter / samples, 0, 0])
                .r
                for i in range(samples)
            ]
        )
        labels = Group(
            Text('frame time t', font_size=22, color=GREY).points.move_to([0, 1.75, 0]).r,
            Text('1 / fps', font_size=22, color=GREY).points.move_to([3.6, 1.75, 0]).r,
            Text(
                'shutter interval = motion_blur_shutter / fps', font_size=22, color=BLUE
            ).points.move_to([0, -1.75, 0]).r,
            Text('motion_blur_samples samples per frame', font_size=22, color=YELLOW)
            .points.move_to([0, -2.45, 0])
            .r,
            Text('(only items with set_motion_blur() are sampled)', font_size=20, color=GREY)
            .points.move_to([0, -3.05, 0])
            .r,
        )

        Group(axis, window, centers, samples_group, labels).show()
        self.forward(1)


class Test_MotionBlur(_BatchOfTests):
    lst = [
        MotionBlurBasic,
        MotionBlurShutterDemo,
        MotionBlurCoexistDemo,
        MotionBlurDiagram,
    ]
    alpha = 1
