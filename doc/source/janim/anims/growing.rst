growing
=======

.. autoclass:: janim.anims.growing.GrowFromPoint
    :show-inheritance:

.. janim-example:: GrowFromPointExample
    :media: ../../_static/videos/GrowFromPointExample.mp4

    from janim.imports import *

    class GrowFromPointExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.growing.GrowFromCenter
    :show-inheritance:

.. janim-example:: GrowFromCenterExample
    :media: ../../_static/videos/GrowFromCenterExample.mp4

    from janim.imports import *

    class GrowFromCenterExample(Timeline):
        def construct(self):
            group = Group(
                Square(fill_alpha=0.5),
                Circle(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            )
            group.points.arrange(buff=LARGE_BUFF)

            self.play(*map(GrowFromCenter, group))

            self.forward()

.. autoclass:: janim.anims.growing.GrowFromEdge
    :show-inheritance:

.. janim-example:: GrowFromEdgeExample
    :media: ../../_static/videos/GrowFromEdgeExample.mp4

    from janim.imports import *

    class GrowFromEdgeExample(Timeline):
    def construct(self):
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

.. autoclass:: janim.anims.growing.SpinInFromNothing
    :show-inheritance:

.. janim-example:: SpinInFromNothingExample
    :media: ../../_static/videos/SpinInFromNothingExample.mp4

    from janim.imports import *

    class SpinInFromNothingExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.growing.GrowArrowByBoundFunc
    :show-inheritance:

.. autoclass:: janim.anims.growing.GrowArrow
    :show-inheritance:

.. janim-example:: GrowArrowExample
    :media: ../../_static/videos/GrowArrowExample.mp4

    from janim.imports import *

    class GrowArrowExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.growing.GrowDoubleArrow
    :show-inheritance:

.. janim-example:: GrowDoubleArrowExample
    :media: ../../_static/videos/GrowDoubleArrowExample.mp4

    from janim.imports import *

    class GrowDoubleArrowExample(Timeline):
        def construct(self):
            group = DoubleArrow(ORIGIN, RIGHT * 7) * 3
            group.points.arrange(DOWN, buff=LARGE_BUFF)

            self.play(
                GrowDoubleArrow(group[0], start_ratio=0.2),
                GrowDoubleArrow(group[1]),
                GrowDoubleArrow(group[2], start_ratio=0.8),
                duration=2
            )
            self.forward()
