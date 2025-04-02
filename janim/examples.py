# flake8: noqa
from janim.imports import *


class HelloJAnimExample(Timeline):
    def construct(self) -> None:
        # define items
        circle = Circle(color=BLUE)
        square = Square(color=GREEN, fill_alpha=0.5)

        # do animations
        self.forward()
        self.play(Create(circle))
        self.play(Transform(circle, square))
        self.play(Uncreate(square))
        self.forward()


class SimpleCurveExample(Timeline):
    def construct(self) -> None:
        item1 = VItem(
            LEFT * 2, DR, UR * 3 + UP, RIGHT * 4, DR * 2, DOWN * 2, LEFT * 2,
            NAN_POINT,
            DL * 3, DL * 2, DOWN * 3, DL * 4, DL * 3,
        )
        item1.fill.set(alpha=0.5)
        item1.show()

        self.forward(0.5)
        self.play(item1.anim.color.set(BLUE))
        self.play(Rotate(item1, -90 * DEGREES))
        self.forward(0.5)

        item2 = VItem(LEFT, UP, RIGHT, DOWN, LEFT)
        item2.color.set(BLUE)
        item2.fill.set(alpha=0.2)

        state = self.camera.copy()
        self.play(self.camera.anim.points.scale(0.5))
        self.play(self.camera.anim.become(state))

        self.play(
            Transform(item1, item2),
            duration=2
        )
        self.forward(1)


class TextExample(Timeline):
    def construct(self) -> None:
        txt = Text('Here is a text', font_size=64)
        desc = Group(
            Text('You can also apply <c BLUE>styles</c> to the text.', format=Text.Format.RichText),
            Text('You can also apply <c GREEN><fs 1.4>styles</fs></c> to the text.', format=Text.Format.RichText),
        )
        group = Group(txt, desc)
        group.points.arrange(DOWN, buff=MED_LARGE_BUFF)

        self.forward()
        self.play(Write(txt))
        self.play(FadeIn(desc[0], UP))
        self.play(Transform(desc[0], desc[1]))
        self.forward()


typst_doc = '''
JAnim provides #text(green)[`TypstDoc`] class to insert typst document.

Math expressions are also available.

$ A = pi r^2 $
$ "area" = pi dot "radius"^2 $
$ cal(A) :=
    { x in RR | x "is natural" } $
#let x = 5
$ #x < 17 $

The difference between #text(green)[`TypstDoc`] and #text(green)[`TypstMath`]:
- #text(green)[`TypstDoc`] automatically align to the top of view,
  so you can see the document from the start.
- The content of #text(green)[`TypstMath`] is wrapped by math environment
  and move to the center by default.
'''


class TypstExample(Timeline):
    def construct(self) -> None:
        doc = TypstDoc(typst_doc)
        typ = TypstMath('sum_(i=1)^n x_i')

        # Applying animations on text is slow
        self.play(Write(doc), duration=4)
        self.forward()
        self.play(FadeOut(doc))

        self.play(Write(typ))
        self.forward()
        self.play(FadeOut(typ))


class AnimatingPiExample(Timeline):
    def construct(self) -> None:
        grid = TypstMath('pi') * 100
        grid.points.scale(2).arrange_in_grid(10, 10, buff=0.2)
        grid.show()

        self.play(grid.anim.points.shift(LEFT))
        self.play(grid(VItem).anim.color.set(YELLOW))
        self.forward()
        self.play(grid(VItem).anim.color.set(BLUE))
        self.forward()
        self.play(grid.anim.points.to_center().set_height(TAU - MED_SMALL_BUFF))
        self.forward()

        self.play(grid.anim.points.apply_complex_fn(np.exp), duration=5)
        self.forward()

        self.play(
            grid.anim.points.apply_point_fn(
                lambda p: [
                    p[0] + 0.5 * math.sin(p[1]),
                    p[1] + 0.5 * math.sin(p[0]),
                    p[2]
                ]
            ),
            duration=5
        )
        self.forward()


class NumberPlaneExample(Timeline):
    def construct(self) -> None:
        plane = NumberPlane(faded_line_ratio=1)

        sin_graph = plane.get_graph(lambda x: math.sin(x))

        self.forward(0.2)
        self.play(Write(plane, lag_ratio=0.05))
        self.play(Write(sin_graph))
        self.forward()

        self.play(
            plane.anim.points.apply_matrix([
                [3, -1],
                [1, 2]
            ]),
            sin_graph.anim(),
            duration=2
        )
        self.forward()



class UpdaterExample(Timeline):
    def construct(self) -> None:
        square = Square(fill_color=BLUE_E, fill_alpha=1).show()
        brace = Brace(square, UP).show()

        def text_updater(p: UpdaterParams):
            cmpt = brace.current().points
            return cmpt.create_text(f'Width = {cmpt.brace_length:.2f}')

        self.prepare(
            DataUpdater(
                brace,
                lambda data, p: data.points.match(square.current())
            ),
            ItemUpdater(None, text_updater),
            duration=10
        )
        self.forward()
        self.play(square.anim.points.scale(2))
        self.play(square.anim.points.scale(0.5))
        self.play(square.anim.points.set_width(5, stretch=True))

        w0 = square.points.box.width

        self.play(
            DataUpdater(
                square,
                lambda data, p: data.points.set_width(
                    w0 + 0.5 * w0 * math.sin(p.alpha * p.range.duration)
                )
            ),
            duration=5
        )
        self.forward()


class MarkedSquare(MarkedItem, Square):
    def __init__(self, side_length: float = 2.0, **kwargs):
        super().__init__(side_length, **kwargs)
        self.mark.set_points([RIGHT * side_length / 4, DOWN * side_length / 4])


class MarkedItemExample(Timeline):
    def construct(self):
        square = MarkedSquare()

        tri1 = Triangle(radius=0.2, color=GREEN)
        tri2 = Triangle(radius=0.2, color=BLUE)
        dots = DotCloud(color=RED)

        self.play(
            square.update.points.rotate(TAU),
            DataUpdater(
                square,
                lambda data, p: data.points.shift(RIGHT * math.sin(4 * math.pi * p.alpha))
            ),

            DataUpdater(
                tri1,
                lambda data, p: data.mark.set(square.current().mark.get())
            ),
            DataUpdater(
                tri2,
                lambda data, p: data.mark.set(square.current().mark.get(index=1))
            ),
            DataUpdater(
                dots,
                lambda data, p: data.points.set(square.current().mark.get_points()),
                skip_null_items=False
            ),
            duration=4
        )


class FrameEffectExample(Timeline):
    def construct(self):
        squares = Square(0.5, color=BLUE, fill_alpha=0.3) * 49
        squares.points.arrange_in_grid()

        effect1 = SimpleFrameEffect(    # (2~8s) [::2] 的方块产生渐变色
            squares[::2],
            shader='''
            f_color = texture(fbo, v_texcoord);
            f_color.gb *= v_texcoord;
            '''
        )

        effect2 = SimpleFrameEffect(    # (4~8s) [1::2] 的方块产生故障效果
            squares[1::2],
            shader='''
            vec2 uv = v_texcoord;

            float glitchStrength = sin(time) * 0.02;
            vec2 offset = vec2(glitchStrength, 0.0);

            float r = texture(fbo, uv + offset).r;
            float g = texture(fbo, uv).g;
            float b = texture(fbo, uv - offset).b;
            float a = max(texture(fbo, uv + offset).a, max(texture(fbo, uv).a, texture(fbo, uv - offset).a));

            float lineNoise = step(0.5, fract(uv.y * 10.0 + time));
            r *= lineNoise;
            b *= lineNoise;

            f_color = vec4(r, g, b, a);
            ''',
            uniforms=['float time']
        )


        self.schedule(2, effect1.show)

        self.play(
            Rotate(squares, TAU, duration=8),
            DataUpdater(
                effect2,
                lambda data, p: data.apply_uniforms(time=p.global_t - p.range.at),
                at=4,
                duration=4
            )
        )
