# flake8: noqa
from janim.imports import *


class AnimGroupExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Circle(fill_alpha=0.5),
            Square(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.forward()
        self.play(
            FadeIn(group[0]),
            AnimGroup(
                FadeIn(group[1]),
                FadeIn(group[2]),
                duration=2
            )
        )
        self.forward()

        self.hide(group)
        self.play(
            FadeIn(group[0], duration=2),
            AnimGroup(
                FadeIn(group[1]),
                FadeIn(group[2]),
                at=1,
                duration=2
            )
        )
        self.forward()


class SuccessionExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Circle(fill_alpha=0.5),
            Square(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.forward()
        self.play(
            Succession(
                *map(FadeIn, group)
            )
        )
        self.forward()

        self.hide(group)
        self.play(
            Succession(
                *map(FadeIn, group),
                offset=1
            )
        )
        self.forward()

        self.hide(group)
        self.play(
            Succession(
                *map(FadeIn, group),
                offset=-0.7
            )
        )
        self.forward()


class AlignedExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Circle(fill_alpha=0.5),
            Square(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.forward()
        self.play(
            Aligned(
                FadeIn(group[0], duration=2),
                FadeIn(group[1], duration=3),
                FadeIn(group[2], at=0.5, duration=0.5)
            )
        )
        self.forward()


class ShowPartialExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Line(path_arc=PI),
            Line(path_arc=PI),
            Circle(),
            Circle()
        )
        group.points.arrange(aligned_edge=DOWN)

        func1 = lambda p: (0, p.alpha)
        func2 = lambda p: (.5 - .5 * p.alpha, .5 + .5 * p.alpha)

        self.play(
            ShowPartial(group[0], func1),
            ShowPartial(group[1], func2),
            ShowPartial(group[2], func1),
            ShowPartial(group[3], func2),
            duration=3
        )


class CreateExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(),
            Square(),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.play(
            Create(group[0], auto_close_path=False),
            Create(group[1:]),
            duration=3
        )


class UncreateExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(),
            Square(),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.play(
            Uncreate(group[0], auto_close_path=False),
            Uncreate(group[1:]),
            duration=3
        )


class DestructionExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(),
            Square(),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.play(
            Destruction(group[0], auto_close_path=False),
            Destruction(group[1:]),
            duration=3
        )


class DrawBorderThenFillExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.play(
            DrawBorderThenFill(group),
            duration=3
        )
        self.forward()

        self.play(
            DrawBorderThenFill(group, stroke_radius=0.02),
            duration=3
        )
        self.forward()


class WriteExample(Timeline):
    def construct(self) -> None:
        dots = Dot(color=BLUE) * 10
        dots.points.arrange().shift(UP)

        txt = Text('Text text Text text')
        txt.points.shift(DOWN)

        self.play(
            Write(dots, duration=2),
            Write(txt, duration=2),
        )


class ShowIncreasingSubsetsExample(Timeline):
    def construct(self):
        text = Text('ShowIncreasingSubsets')
        text.points.set_width(11)
        self.forward(0.5)
        self.play(ShowIncreasingSubsets(text[0], duration=3))
        self.forward(0.5)


class ShowSubitemsOneByOneExample(Timeline):
    def construct(self):
        text = Text('ShowSubitemsOneByOne')
        text.points.set_width(11)
        self.forward(0.5)
        self.play(ShowSubitemsOneByOne(text[0], duration=3))
        self.forward(0.5)


class FadeInExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.play(
            FadeIn(group),
            duration=2
        )


class FadeOutExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.play(
            FadeOut(group),
            duration=2
        )


class GrowFromPointExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        directions=[UP,LEFT,DOWN,RIGHT]

        for direction in directions:
            self.play(
                *[
                    GrowFromPoint(item, item.points.box.center + direction * 3)
                    for item in group
                ]
            )

        self.forward()


class GrowFromCenterExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.play(*map(GrowFromCenter, group))

        self.forward()


class GrowFromEdgeExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        directions=[UP,LEFT,DOWN,RIGHT]

        for direction in directions:
            self.play(
                *[
                    GrowFromEdge(item, direction)
                    for item in group
                ]
            )

        self.forward()


class SpinInFromNothingExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.play(
            *map(SpinInFromNothing, group),
            duration=2
        )
        self.forward()


class GrowArrowExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Arrow(ORIGIN, RIGHT * 6),
            Vector(RIGHT * 6, color=YELLOW)
        )
        group.points.arrange(DOWN, buff=2)

        self.play(
            *map(GrowArrow, group),
            duration=2
        )

        self.forward()


class GrowDoubleArrowExample(Timeline):
    def construct(self) -> None:
        group = DoubleArrow(ORIGIN, RIGHT * 7) * 3
        group.points.arrange(DOWN, buff=LARGE_BUFF)

        self.play(
            GrowDoubleArrow(group[0], start_ratio=0.2),
            GrowDoubleArrow(group[1]),
            GrowDoubleArrow(group[2], start_ratio=0.8),
            duration=2
        )
        self.forward()


class FocusOnExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Dot(),
            Typst('x')
        ).show()
        group.points.scale(2).arrange(RIGHT, buff=2)

        item_or_coord = [
            *group,                             # Items: Dot and "x"
            group.points.box.right + RIGHT * 2  # Coord
        ]

        colors=[GREY, RED, BLUE]

        for obj, color in zip(item_or_coord, colors):
            self.play(FocusOn(obj, color=color))

        self.forward(0.3)


class IndicateExample(Timeline):
    def construct(self) -> None:
        formula = Typst('f(x)')
        dot = Dot()

        group = Group(formula, dot).show()
        group.points.scale(3).arrange(DOWN, buff=3)

        for mob in [formula[2], dot]:
            self.play(Indicate(mob))

        self.forward(0.3)


class CircleIndicateExample(Timeline):
    def construct(self):
        group = Group(
            Dot(),
            Typst('x')
        ).show()
        group.points.scale(2).arrange(RIGHT, buff=2)

        self.forward(0.2)

        for obj in group:
            self.play(CircleIndicate(obj))

        self.forward(0.2)

        for obj in group:
            self.play(CircleIndicate(obj, scale=1.5))


class ShowCreationThenDestructionExample(Timeline):
    def construct(self):
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.scale(1.5).arrange(RIGHT, buff=2)

        self.play(
            *[
                ShowCreationThenDestruction(item, auto_close_path=True)
                for item in group
            ],
            duration=2
        )
        self.forward()


class ShowCreationThenFadeOutExample(Timeline):
    def construct(self):
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        )
        group.points.scale(1.5).arrange(RIGHT, buff=2)

        self.play(
            *map(ShowCreationThenFadeOut, group)
        )
        self.forward()


class ShowPassingFlashAroundExample(Timeline):
    def construct(self):
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        ).show()
        group.points.scale(1.5).arrange(RIGHT, buff=2)

        self.play(
            *map(ShowPassingFlashAround, group)
        )
        self.forward()


class ShowCreationThenDestructionAroundExample(Timeline):
    def construct(self):
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        ).show()
        group.points.scale(1.5).arrange(RIGHT, buff=2)

        self.play(
            *map(ShowCreationThenDestructionAround, group)
        )
        self.forward()


class ShowCreationThenFadeAroundExample(Timeline):
    def construct(self):
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        ).show()
        group.points.scale(1.5).arrange(RIGHT, buff=2)

        self.play(
            *map(ShowCreationThenFadeAround, group)
        )
        self.forward()


class FlashExample(Timeline):
    def construct(self):
        group = Group(
            Dot(),
            Typst('x')
        ).show()
        group.points.scale(2).arrange(RIGHT, buff=2)

        item_or_coord = [
            *group,                             # Items: Dot and "x"
            group.points.box.right + RIGHT * 2  # Coord
        ]

        colors = [GREY, RED, BLUE]

        self.forward(0.3)

        for obj, color in zip(item_or_coord, colors):
            self.play(Flash(obj, color=color, flash_radius=0.5))

        self.forward(0.3)


class ApplyWaveExample(Timeline):
    def construct(self):
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        ).show()
        group.points.scale(1.5).arrange(RIGHT, buff=2)

        self.play(*map(ApplyWave, group))
        self.forward()


class WiggleOutThenInExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Square(fill_alpha=0.5),
            Circle(fill_alpha=0.5),
            Text('Text', font_size=48),
            color=BLUE
        ).show()
        group.points.scale(1.5).arrange(RIGHT, buff=2)

        self.play(*map(WiggleOutThenIn, group))
        self.forward()


class HomotopyExample(Timeline):
    def construct(self):
        def homotopy_func(x, y, z, t):
            return [x * t, y * t, z]

        square = Square()
        self.play(Homotopy(square, homotopy_func))
        self.forward(0.3)


class ComplexHomotopyExample(Timeline):
    def construct(self):
        def complex_func(z: complex, t: float) -> complex:
            return interpolate(z, z**3, t)

        group = Group(
            Text('Text'),
            Square(side_length=1),
        )
        group.points.arrange(RIGHT, buff=2)

        self.play(
            *[ComplexHomotopy(
                item,
                complex_func
            ) for item in group]
        )
        self.forward(0.3)


class MoveAlongPathExample(Timeline):
    def construct(self) -> None:
        line = Line(ORIGIN, RIGHT * Config.get.frame_width, buff=1)
        dot1 = Dot(color=YELLOW)

        curve = ParametricCurve(
            lambda t: [math.cos(t) * t * 0.2, math.sin(t) * t * 0.2, 0],
            (0, 10, 0.1)
        )
        dot2 = Dot(color=YELLOW)

        group = Group(line, curve).show()
        group.points.arrange(DOWN)

        self.play(
            MoveAlongPath(dot1, line),
            MoveAlongPath(dot2, curve),
            duration=2
        )
        self.forward(0.3)


class RotateExample(Timeline):
    def construct(self):
        square = Square(side_length=4).show()

        self.play(
            Rotate(
                square,
                PI / 4,
                duration=2
            )
        )
        self.forward(0.3)
        self.play(
            Rotate(
                square,
                PI,
                axis=RIGHT,
                duration=2,
            )
        )
        self.forward(0.3)


class RotatingExample(Timeline):
    def construct(self):
        square = Square(side_length=4).show()

        self.play(
            Rotating(
                square,
                PI / 4,
                duration=2
            )
        )
        self.forward(0.3)
        self.play(
            Rotating(
                square,
                PI,
                axis=RIGHT,
                duration=2,
            )
        )
        self.forward(0.3)


class TransformExample(Timeline):
    def construct(self):
        A = Text('Text-A', font_size=72)
        B = Text('Text-B', font_size=72)
        C = Text('C-Text', font_size=72)

        A.show()
        self.forward()
        self.play(Transform(A, B))
        self.forward()
        self.play(Transform(B, C))
        self.forward()


class TransformInSegmentsExample(Timeline):
    def construct(self):
        typ1 = Typst('sin x + cos x')
        typ2 = Typst('cos y + sin y')
        Group(typ1, typ2).points.scale(3)

        self.show(typ1)
        self.forward(0.5)
        self.play(TransformInSegments(typ1, [[0,3,4], [5,8,9]],
                                      typ2, ...,
                                      lag_ratio=0.5))
        self.forward(0.5)


class MethodTransformExample(Timeline):
    def construct(self):
        A = Text("Text-A")
        A.points.to_border(LEFT)

        A.show()
        self.forward()
        self.play(
            A.anim.points.scale(3).shift(RIGHT * 7 + UP * 2)
        )
        self.play(
            A.anim.color.set(BLUE)
        )
        self.forward()


class FadeTransformExample(Timeline):
    def construct(self) -> None:
        rect = Rect(6, 2, color=BLUE, fill_alpha=1).show()
        txt = Text('Rectangle')
        txt.points.scale(3)

        self.forward(0.5)
        self.play(FadeTransform(rect, txt))
        self.forward(0.5)
