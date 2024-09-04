fading
======

.. autoclass:: janim.anims.fading.Fade
    :show-inheritance:

.. autoclass:: janim.anims.fading.FadeIn
    :show-inheritance:

.. janim-example:: FadeInExample
    :media: ../../_static/videos/FadeInExample.mp4

    from janim.imports import *

    class FadeInExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.fading.FadeOut
    :show-inheritance:

.. janim-example:: FadeOutExample
    :media: ../../_static/videos/FadeOutExample.mp4

    from janim.imports import *

    class FadeOutExample(Timeline):
        def construct(self):
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


.. autoclass:: janim.anims.fading.FadeInFromPoint
    :show-inheritance:

.. janim-example:: FadeInFromPointExample
    :media: ../../_static/videos/FadeInFromPointExample.mp4

    from janim.imports import *

    class FadeInFromPointExample(Timeline):
        def construct(self):
            items = Group(
                Circle(),
                Circle(fill_alpha=1),
                Text('Text', font_size=48)
            )
            items.points.scale(1.5)
            items.points.arrange(RIGHT, buff=2)

            self.forward()
            self.play(
                *[FadeInFromPoint(item, UP*3) for item in items]
            )
            self.forward()


.. autoclass:: janim.anims.fading.FadeOutToPoint
    :show-inheritance:

.. janim-example:: FadeOutToPointExample
    :media: ../../_static/videos/FadeOutToPointExample.mp4

    from janim.imports import *

    class FadeOutToPointExample(Timeline):
        def construct(self):
            items = Group(
                Circle(),
                Circle(fill_alpha=1),
                Text('Text', font_size=48)
            ).show()
            items.points.scale(1.5)
            items.points.arrange(RIGHT, buff=2)

            self.forward()
            self.play(
                *[FadeOutToPoint(item, DOWN*3) for item in items]
            )
            self.forward()
