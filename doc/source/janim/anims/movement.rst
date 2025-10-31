movement
========

.. autoclass:: janim.anims.movement.Homotopy
    :show-inheritance:

.. janim-example:: HomotopyExample
    :media: _static/videos/HomotopyExample.mp4

    from janim.imports import *

    class HomotopyExample(Timeline):
        def construct(self):
            def homotopy_func(x, y, z, t):
                return [x * t, y * t, z]

            square = Square()
            self.play(Homotopy(square, homotopy_func))
            self.forward(0.3)

.. autoclass:: janim.anims.movement.ComplexHomotopy
    :show-inheritance:

.. janim-example:: ComplexHomotopyExample
    :media: _static/videos/ComplexHomotopyExample.mp4

    from janim.imports import *

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

.. autoclass:: janim.anims.movement.MoveAlongPath
    :show-inheritance:

.. janim-example:: MoveAlongPathExample
    :media: _static/videos/MoveAlongPathExample.mp4

    from janim.imports import *

    class MoveAlongPathExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.movement.Follow
    :show-inheritance:

.. janim-example:: FollowExample
    :media: _static/videos/FollowExample.mp4

    from janim.imports import *

    class FollowExample(Timeline):
        def construct(self):
            dot = Dot(RIGHT * 2).show()
            txt = Text('dot').show()
            txt.points.next_to(dot, DOWN)

            self.forward()
            self.play(
                Succession(
                    Rotate(dot, PI * 3 / 2, about_point=ORIGIN),
                    dot.anim.points.shift(UP * 4),
                    duration=3
                ),
                Follow(txt, dot, DOWN, duration=3),
            )
            self.forward()
