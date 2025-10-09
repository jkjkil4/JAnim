creation
========

.. autoclass:: janim.anims.creation.ShowPartial
    :show-inheritance:

.. janim-example:: ShowPartialExample
    :media: _static/videos/ShowPartialExample.mp4

    from janim.imports import *

    class ShowPartialExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.creation.Create
    :show-inheritance:

.. janim-example:: CreateExample
    :media: _static/videos/CreateExample.mp4

    from janim.imports import *

    class CreateExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.creation.Uncreate
    :show-inheritance:

.. janim-example:: UncreateExample
    :media: _static/videos/UncreateExample.mp4

    from janim.imports import *

    class UncreateExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.creation.Destruction
    :show-inheritance:

.. janim-example:: DestructionExample
    :media: _static/videos/DestructionExample.mp4

    class DestructionExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.creation.DrawBorderThenFill
    :show-inheritance:

.. janim-example:: DrawBorderThenFillExample
    :media: _static/videos/DrawBorderThenFillExample.mp4

    from janim.imports import *

    class DrawBorderThenFillExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.creation.Write
    :show-inheritance:

.. janim-example:: WriteExample
    :media: _static/videos/WriteExample.mp4

    from janim.imports import *

    class WriteExample(Timeline):
        def construct(self):
            dots = Dot(color=BLUE) * 10
            dots.points.arrange().shift(UP)

            txt = Text('Text text Text text')
            txt.points.shift(DOWN)

            self.play(
                Write(dots, duration=2),
                Write(txt, duration=2),
            )

.. autoclass:: janim.anims.creation.ShowIncreasingSubsets
    :show-inheritance:

.. janim-example:: ShowIncreasingSubsetsExample
    :media: _static/videos/ShowIncreasingSubsetsExample.mp4

    from janim.imports import *

    class ShowIncreasingSubsetsExample(Timeline):
        def construct(self):
            text = Text('ShowIncreasingSubsets')
            text.points.set_width(11)
            self.forward(0.5)
            self.play(ShowIncreasingSubsets(text[0], duration=3))
            self.forward(0.5)

.. autoclass:: janim.anims.creation.ShowSubitemsOneByOne
    :show-inheritance:

.. janim-example:: ShowSubitemsOneByOneExample
    :media: _static/videos/ShowSubitemsOneByOneExample.mp4

    from janim.imports import *

    class ShowSubitemsOneByOneExample(Timeline):
        def construct(self):
            text = Text('ShowSubitemsOneByOne')
            text.points.set_width(11)
            self.forward(0.5)
            self.play(ShowSubitemsOneByOne(text[0], duration=3))
            self.forward(0.5)
