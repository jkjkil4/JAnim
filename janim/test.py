from janim import *

class Test(Scene):
    def construct(self) -> None:
        m = VItem()
        m.set_points([
            UP, RIGHT, DOWN,
            DOWN, DOWN * 2, DOWN * 3,
            DOWN * 3, DOWN + LEFT * 2, LEFT + UP * 2
        ])
        m.set_color([RED, GREEN, BLUE])

        d = DotCloud([LEFT, RIGHT, UP, DOWN]).set_radius(0.1)

        self.add(m, (d * 6).arrange(buff=LARGE_BUFF))

Test().run()
