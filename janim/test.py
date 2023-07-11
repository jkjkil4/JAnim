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
        m1.set_points_as_corners([ORIGIN, DOWN])
        m1.add_points_as_corners([DR, RIGHT])

        self.add(m1)

VItemTest().run()
