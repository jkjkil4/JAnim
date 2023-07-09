from janim import *

class DotCloudTest(Scene):
    def construct(self) -> None:
        dots = DotCloud([
            RIGHT * i + UP * j + OUT * k
            for i in range(4)
            for j in range(4)
            for k in range(4)
        ]).set_radius(0.2).set_color([GREEN_A, BLUE_B, YELLOW_B]).to_center()
        
        self.add(dots)

class VItemTest(Scene):
    def construct(self) -> None:
        m1 = VItem()
        m1.set_points([
            UP, RIGHT, DOWN,
            DOWN, DOWN * 2, DOWN * 3,
            DOWN * 3, DOWN + LEFT * 2, LEFT + UP * 2
        ]).set_color([
            RED, GREEN, BLUE
        ])
        print(m1.get_stroke_width())

        m2 = VItem()
        m2.set_points([
            UP, RIGHT, DOWN
        ]).set_color([
            RED, GREEN, BLUE
        ]).set_stroke_width([
            0.1, 0.2
        ])

        self.add(Group(m1, m2).arrange(buff=LARGE_BUFF))

VItemTest().run()
