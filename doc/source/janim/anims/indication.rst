indication
==========

.. autoclass:: janim.anims.indication.FocusOn
    :show-inheritance:

.. janim-example:: FocusOnExample
    :media: ../../_static/videos/FocusOnExample.mp4

    from janim.imports import *

    class FocusOnExample(Timeline):
        def construct(self):
            group = Group(
                Dot(),
                Typst('x')
            ).show()
            group.points.scale(2).arrange(RIGHT, buff=2)

            item_or_coord = [
                *group,                             # Items: Dot and "x"
                group.points.box.right + RIGHT * 2  # Coord
            ]

            colors=[GREY, RED, BLUE]

            for obj, color in zip(item_or_coord, colors):
                self.play(FocusOn(obj, color=color))

            self.forward(0.3)

.. autoclass:: janim.anims.indication.Indicate
    :show-inheritance:

.. janim-example:: IndicateExample
    :media: ../../_static/videos/IndicateExample.mp4

    from janim.imports import *

    class IndicateExample(Timeline):
        def construct(self):
            formula = Typst('f(x)')
            dot = Dot()

            group = Group(formula, dot).show()
            group.points.scale(3).arrange(DOWN, buff=3)

            for mob in [formula[2], dot]:
                self.play(Indicate(mob))

            self.forward(0.3)

.. autoclass:: janim.anims.indication.CircleIndicate
    :show-inheritance:

.. janim-example:: CircleIndicateExample
    :media: ../../_static/videos/CircleIndicateExample.mp4

    from janim.imports import *

    class CircleIndicateExample(Timeline):
        def construct(self):
            group = Group(
                Dot(),
                Typst('x')
            ).show()
            group.points.scale(2).arrange(RIGHT, buff=2)

            self.forward(0.2)

            for obj in group:
                self.play(CircleIndicate(obj))

            self.forward(0.2)

            for obj in group:
                self.play(CircleIndicate(obj, scale=1.5))

.. autoclass:: janim.anims.indication.ShowPassingFlash
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: janim.anims.indication.ShowCreationThenDestruction
    :show-inheritance:

.. janim-example:: ShowCreationThenDestructionExample
    :media: ../../_static/videos/ShowCreationThenDestructionExample.mp4

    from janim.imports import *

    class ShowCreationThenDestructionExample(Timeline):
        def construct(self):
            group = Group(
                Square(fill_alpha=0.5),
                Circle(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            )
            group.points.scale(1.5).arrange(RIGHT, buff=2)

            self.play(
                *[
                    ShowCreationThenDestruction(item, auto_close_path=True)
                    for item in group
                ],
                duration=2
            )
            self.forward()

.. autoclass:: janim.anims.indication.ShowCreationThenFadeOut
    :show-inheritance:

.. janim-example:: ShowCreationThenFadeOutExample
    :media: ../../_static/videos/ShowCreationThenFadeOutExample.mp4

    from janim.imports import *

    class ShowCreationThenFadeOutExample(Timeline):
        def construct(self):
            group = Group(
                Square(fill_alpha=0.5),
                Circle(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            )
            group.points.scale(1.5).arrange(RIGHT, buff=2)

            self.play(
                *map(ShowCreationThenFadeOut, group)
            )
            self.forward()

.. autoclass:: janim.anims.indication.AnimationOnSurroundingRect
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: janim.anims.indication.ShowPassingFlashAround
    :show-inheritance:

.. janim-example:: ShowPassingFlashAroundExample
    :media: ../../_static/videos/ShowPassingFlashAroundExample.mp4

    from janim.imports import *

    class ShowPassingFlashAroundExample(Timeline):
        def construct(self):
            group = Group(
                Square(fill_alpha=0.5),
                Circle(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            ).show()
            group.points.scale(1.5).arrange(RIGHT, buff=2)

            self.play(
                *map(ShowPassingFlashAround, group)
            )
            self.forward()

.. autoclass:: janim.anims.indication.ShowCreationThenDestructionAround
    :show-inheritance:

.. janim-example:: ShowCreationThenDestructionAroundExample
    :media: ../../_static/videos/ShowCreationThenDestructionAroundExample.mp4

    from janim.imports import *

    class ShowCreationThenDestructionAroundExample(Timeline):
        def construct(self):
            group = Group(
                Square(fill_alpha=0.5),
                Circle(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            ).show()
            group.points.scale(1.5).arrange(RIGHT, buff=2)

            self.play(
                *map(ShowCreationThenDestructionAround, group)
            )
            self.forward()

.. autoclass:: janim.anims.indication.ShowCreationThenFadeAround
    :show-inheritance:

.. janim-example:: ShowCreationThenFadeAroundExample
    :media: ../../_static/videos/ShowCreationThenFadeAroundExample.mp4

    from janim.imports import *

    class ShowCreationThenFadeAroundExample(Timeline):
        def construct(self):
            group = Group(
                Square(fill_alpha=0.5),
                Circle(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            ).show()
            group.points.scale(1.5).arrange(RIGHT, buff=2)

            self.play(
                *map(ShowCreationThenFadeAround, group)
            )
            self.forward()

.. autoclass:: janim.anims.indication.Flash
    :show-inheritance:

.. janim-example:: FlashExample
    :media: ../../_static/videos/FlashExample.mp4

    from janim.imports import *

    class FlashExample(Timeline):
        def construct(self):
            group = Group(
                Dot(),
                Typst('x')
            ).show()
            group.points.scale(2).arrange(RIGHT, buff=2)

            item_or_coord = [
                *group,                             # Items: Dot and "x"
                group.points.box.right + RIGHT * 2  # Coord
            ]

            colors = [GREY, RED, BLUE]

            self.forward(0.3)

            for obj, color in zip(item_or_coord, colors):
                self.play(Flash(obj, color=color, flash_radius=0.5))

            self.forward(0.3)

.. autoclass:: janim.anims.indication.ApplyWave
    :show-inheritance:

.. janim-example:: ApplyWaveExample
    :media: ../../_static/videos/ApplyWaveExample.mp4

    from janim.imports import *

    class ApplyWaveExample(Timeline):
        def construct(self):
            group = Group(
                Square(fill_alpha=0.5),
                Circle(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            ).show()
            group.points.scale(1.5).arrange(RIGHT, buff=2)

            self.play(*map(ApplyWave, group))
            self.forward()

.. autoclass:: janim.anims.indication.WiggleOutThenIn
    :show-inheritance:

.. janim-example:: WiggleOutThenInExample
    :media: ../../_static/videos/WiggleOutThenInExample.mp4

    from janim.imports import *

    class WiggleOutThenInExample(Timeline):
        def construct(self) -> None:
            group = Group(
                Square(fill_alpha=0.5),
                Circle(fill_alpha=0.5),
                Text('Text', font_size=48),
                color=BLUE
            ).show()
            group.points.scale(1.5).arrange(RIGHT, buff=2)

            self.play(*map(WiggleOutThenIn, group))
            self.forward()

.. # TODO: FlashyFadeIn
