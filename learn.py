from janim.imports import *


class HelloJAnimExample(Timeline):
    def construct(self) -> None:
        group = Group(
            Circle(fill_alpha=0.5),
            Square(fill_alpha=0.5),
            Text("Text", font_size=48),
            color=BLUE,
        )
        group.points.arrange(buff=LARGE_BUFF)

        self.forward()
        self.play(
            FadeIn(group[0]), AnimGroup(FadeIn(group[1]), FadeIn(group[2]), duration=2)
        )

        self.forward()

        self.hide(group)
        self.play(
            FadeIn(group[0], duration=2),
            AnimGroup(FadeIn(group[1]), FadeIn(group[2]), at=1, duration=2),
        )
        self.forward()


#  janim run learn.py HelloJAnimExample
