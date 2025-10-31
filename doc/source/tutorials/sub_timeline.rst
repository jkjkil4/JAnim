子时间轴机制
==============================

JAnim 引入了子时间轴机制，使得在主时间轴中可以嵌套子时间轴，从而实现复杂逻辑的分离，以及更好的可复用性。

.. janim-example:: SubTimeline1
    :media: _static/tutorial/SubTimeline1.mp4
    :hide_name:
    :ref: :meth:`~.BuiltTimeline.to_item`

    from janim.imports import *

    class DrawingStarInNumberPlane(Timeline):
        def construct(self):
            plane = NumberPlane(faded_line_ratio=1)
            star = Star(outer_radius=2)
            dot = Dot(star.points.get_start(), color=YELLOW)

            state = self.camera.copy()

            self.play(Create(plane, lag_ratio=0.05))
            self.play(
                self.camera.anim.points.move_to(dot).scale(0.3),
                FadeIn(dot, scale=0.8),
                lag_ratio=0.3
            )
            self.play(
                MoveAlongPath(dot, star),
                Create(star, auto_close_path=False),
                Follow(self.camera, dot, ORIGIN),
                duration=3
            )
            self.play(
                self.camera.anim.become(state),
                star.anim.set(color=YELLOW, fill_alpha=0.5),
                duration=2
            )


    class Texts(Timeline):
        def construct(self):
            txt = Text(
                'I just wrote some text for demonstration.\n'
                'It has no real meaning—it\'s only meant to show that \n'
                'this text is completely decoupled from another Timeline.',
                stroke_color=BLACK,
                stroke_alpha=1,
                stroke_background=True
            )
            txt.points.to_border(UL)

            self.forward()
            self.play(Write(txt, duration=3))


    class MainTimeline(Timeline):
        def construct(self):
            tl1 = DrawingStarInNumberPlane().build().to_item().show()
            tl2 = Texts().build().to_item(keep_last_frame=True).show()

            self.forward(tl1.duration)

在上面这个例子中，我们向主时间轴 ``MainTimeline`` 中插入了两个子时间轴 ``DrawingStarInNumberPlane`` 和 ``Texts`` 。

子时间轴的引入使得每个子时间轴都可以独立地控制自己的动画，我们可以在主时间轴中更灵活地组织和管理动画逻辑。

.. hint::

    上面这个例子中，文字不随另一个时间轴的动画而移动，这个效果也可以使用 :meth:`~.Item.fix_in_frame` 方法来实现，你可以另行参阅。

并且子时间轴在主时间轴中作为一个整体物件，可以更加方便地传入 :class:`~.FrameEffect` 及其派生类应用复杂的视觉效果：

.. janim-example:: SubTimeline2
    :media: _static/tutorial/SubTimeline2.mp4
    :hide_name:
    :ref: :class:`~.SimpleFrameEffect` :class:`~.TransformableFrameClip`

    class MainTimeline(Timeline):
        def construct(self):
            tl1 = DrawingStarInNumberPlane().build().to_item(keep_last_frame=True).show()

            effect = SimpleFrameEffect(
                tl1,
                shader='''
                f_color = texture(fbo, v_texcoord);

                vec3 col = 0.5 + 0.5 * cos(time * 1.5 + v_texcoord.xyx + vec3(0,2,4));
                f_color.rgb *= col;
                ''',
                uniforms=['float time']
            )
            frameclip = TransformableFrameClip(effect)

            tl2 = Texts().build().to_item(keep_last_frame=True).show()

            self.play(
                DataUpdater(
                    effect,
                    lambda data, p: data.apply_uniforms(time=p.elapsed)
                ),
                duration=tl1.duration
            )
            self.forward()
            self.play(
                frameclip.anim.clip.set(scale=0.5, x_offset=-0.2, y_offset=-0.1)
            )
            self.play(
                Write(frameclip.create_border_rect())
            )

并且，子 Timeline 机制让 Timeline 有了极高的可复用性：

.. janim-example:: SubTimeline3
    :media: _static/tutorial/SubTimeline3.mp4
    :hide_name:

    from janim.imports import *

    class GraphDemonstration(Timeline):
        def __init__(self, f, x_range, typ_code):
            super().__init__()
            self.f = f
            self.x_range = x_range
            self.typ_code = typ_code

        def construct(self):
            axes = Axes(axis_config=dict(include_numbers=True))
            graph = axes.get_graph(self.f, self.x_range, color=RED, stroke_radius=0.05)

            typ = TypstMath(
                self.typ_code,
                stroke_color=BLACK,
                stroke_alpha=1,
                stroke_background=True
            ).show()
            typ.points.scale(1.6).to_border(UP)

            def dots_updater(p):
                points = graph.current().points
                return Group(
                    Dot(points.get_start()),
                    Dot(points.get_end()),
                    fill_color=BLACK,
                    stroke_alpha=1,
                )

            self.forward()
            self.play(
                Create(axes, lag_ratio=0.05)
            )
            self.play(
                Create(graph),
                ItemUpdater(None, dots_updater)
            )


    class MainTimeline(Timeline):
        def construct(self):
            params_list = [
                (lambda x: x**2, (-1, 1.5), 'f(x) = x^2'),
                (lambda x: x**3, (-1.5, 1.5), 'f(x) = x^3'),
                (lambda x: math.atan(x), (-2, 2), 'f(x) = tan^(-1) x')
            ]

            width = 1 / len(params_list)
            clip = 0.5 - width / 2

            for i, params in enumerate(params_list):
                offset = (-clip + i * width, 0)
                tl = GraphDemonstration(*params).build().to_item(keep_last_frame=True).show()
                frameclip = TransformableFrameClip(tl, clip=(clip, 0, clip, 0), offset=offset).show()

            self.forward(4)

.. note::

    有待完善关于 :meth:`~.BuiltTimeline.to_playback_control_item` 的说明
