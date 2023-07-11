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
        m1 = Group()
        for i in range(-65, -30, 5):
            vect = RIGHT * np.cos(i * DEGREES) + UP * np.sin(i * DEGREES)

            item = VItem()
            item.set_points([
                DOWN * 2, DOWN * 1, ORIGIN,
                ORIGIN, vect, vect * 2
            ]).set_stroke_width(0.2)

            m1.add(item)

        self.add(m1.arrange())

VItemTest().run()
