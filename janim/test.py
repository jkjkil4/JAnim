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

        d = DotCloud([RIGHT * i for i in range(12)])\
            .set_color([RED, GREEN, BLUE, YELLOW]).set_radius(0.15)
        d.to_center()

        self.add(m)
        self.add((d * 7).arrange(buff=LARGE_BUFF))

Test().run()
