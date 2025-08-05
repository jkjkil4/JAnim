.. _examples:

样例学习
==========

``examples.py`` 提供了一些样例

.. janim-example:: HelloJAnimExample
    :media: ../_static/videos/HelloJAnimExample.mp4
    :ref: :class:`~.Circle` :class:`~.Square` :class:`~.Create` :class:`~.Transform` :class:`~.Uncreate`

    from janim.imports import *

    class HelloJAnimExample(Timeline):
        def construct(self):
            # define items
            circle = Circle(color=BLUE)
            square = Square(color=GREEN, fill_alpha=0.5)

            # do animations
            self.forward()
            self.play(Create(circle))
            self.play(Transform(circle, square))
            self.play(Uncreate(square))
            self.forward()


.. janim-example:: TextExample
    :media: ../_static/videos/TextExample.mp4
    :ref: :class:`~.Text` :class:`~.Write` :class:`~.FadeIn` :class:`~.Transform`

    from janim.imports import *

    class TextExample(Timeline):
        def construct(self):
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


.. janim-example:: TypstExample
    :media: ../_static/videos/TypstExample.mp4
    :ref: :class:`~.TypstDoc` :class:`~.TypstText` :class:`~.TypstMath`

    from janim.imports import *

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
        def construct(self):
            doc = TypstDoc(typst_doc)
            typ = TypstMath('sum_(i=1)^n x_i')

            # Applying animations on text is slow
            self.play(Write(doc), duration=4)
            self.forward()
            self.play(FadeOut(doc))

            self.play(Write(typ))
            self.forward()
            self.play(FadeOut(typ))


.. janim-example:: AnimatingPiExample
    :media: ../_static/videos/AnimatingPiExample.mp4
    :ref: :meth:`~.Cmpt_Points.arrange_in_grid` :meth:`~.Cmpt_Points.apply_complex_fn` :meth:`~.Cmpt_Points.apply_point_fn`

    from janim.imports import *

    class AnimatingPiExample(Timeline):
        def construct(self):
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


.. janim-example:: NumberPlaneExample
    :media: ../_static/videos/NumberPlaneExample.mp4
    :ref: :class:`~.NumberPlane` :meth:`~.Axes.get_graph` :meth:`~.Cmpt_Points.apply_matrix`

    from janim.imports import *

    class NumberPlaneExample(Timeline):
        def construct(self):
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

.. janim-example:: UpdaterExample
    :media: ../_static/videos/UpdaterExample.mp4
    :ref: :class:`~.DataUpdater` :class:`~.ItemUpdater`

    from janim.imports import *

    class UpdaterExample(Timeline):
        def construct(self):
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


.. janim-example:: MarkedItemExample
    :media: ../_static/videos/MarkedItemExample.mp4
    :ref: :class:`~.MarkedItem` :class:`~.DataUpdater`

    from janim.imports import *

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
                    lambda data, p: data.mark.set(square.current().mark.get(0))
                ),
                DataUpdater(
                    tri2,
                    lambda data, p: data.mark.set(square.current().mark.get(1))
                ),
                DataUpdater(
                    dots,
                    lambda data, p: data.points.set(square.current().mark.get_points()),
                    skip_null_items=False
                ),
                duration=4
            )


.. janim-example:: FrameEffectExample
    :media: ../_static/videos/FrameEffectExample.mp4
    :ref: :class:`~.SimpleFrameEffect` :class:`~.Rotate` :class:`~.DataUpdater`

    from janim.imports import *

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
