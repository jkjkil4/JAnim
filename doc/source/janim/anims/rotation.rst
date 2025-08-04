.. _janim_anims_rotation:

rotation
========

.. important::

    如果你想要实现旋转效果，请不要尝试直接使用 ``self.play(item.anim.points.rotate(...))``，
    因为这只是在当前和结果之间进行 :class:`~.MethodTransform` ，并无旋转效果

    实现旋转效果请使用下方给出的 :class:`~.Rotate` 和 :class:`~.Rotating`

.. autoclass:: janim.anims.rotation.Rotate
    :show-inheritance:

.. janim-example:: RotateExample
    :media: ../../_static/videos/RotateExample.mp4

    from janim.imports import *

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

.. autoclass:: janim.anims.rotation.Rotating
    :show-inheritance:

.. janim-example:: RotatingExample
    :media: ../../_static/videos/RotatingExample.mp4

    from janim.imports import *

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

