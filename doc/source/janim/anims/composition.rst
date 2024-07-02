composition
===========

.. note::

    为了更好地了解这些动画组合的效果，你可以复制到你的文件中运行，这样你就可以在界面上看到子动画对应的区段

.. autoclass:: janim.anims.composition.AnimGroup
    :show-inheritance:

.. warning::

    视频示例的代码在下方，不是上方的时间示例

.. janim-example:: AnimGroupExample
    :media: ../../_static/videos/AnimGroupExample.mp4

    from janim.imports import *

    class AnimGroupExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.composition.Succession
    :show-inheritance:

.. warning::

    视频示例的代码在下方，不是上方的时间示例

.. janim-example:: SuccessionExample
    :media: ../../_static/videos/SuccessionExample.mp4

    from janim.imports import *

    class SuccessionExample(Timeline):
        def construct(self):
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

.. autoclass:: janim.anims.composition.Aligned
    :show-inheritance:

.. warning::

    视频示例的代码在下方，不是上方的时间示例

.. janim-example:: AlignedExample
    :media: ../../_static/videos/AlignedExample.mp4

    from janim.imports import *

    class AlignedExample(Timeline):
        def construct(self):
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
