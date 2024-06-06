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
