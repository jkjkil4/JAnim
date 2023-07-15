from janim import *

class DotCloudTest(Scene):
    def construct(self) -> None:
        dots = DotCloud([
            RIGHT * i + UP * j + OUT * k
            for i in range(4)
            for j in range(4)
            for k in range(4)
        ]).set_radius(0.2).set_points_color([GREEN_A, BLUE_B, YELLOW_B]).to_center()
        
        self.add(dots)

class VItemTest(Scene):
    def construct(self) -> None:
        m1 = VItem()
        m1.set_points_as_corners([
            ORIGIN, RIGHT, RIGHT + UR * 3, RIGHT + UP * 3, RIGHT + UP * 2, RIGHT * 0.5 + UR, LEFT + UP * 2,
            LEFT, DOWN, DOWN * 2, DR, DOWN * 0.4
        ]).set_fill(BLUE, 0.5).set_points_color(BLUE)
        m1.close_path().make_approximately_smooth()

        m2 = VItem()
        m2.set_points_as_corners([LEFT, DOWN, RIGHT, UP]).close_path().make_approximately_smooth().reverse_points()
        m2.rotate(30 * DEGREES).scale(0.5).shift(UL * 0.3 + UP * 0.3)
        m1.append_points(m2.get_points())

        m1.to_center()

        # print(m1.get_points(), *m1.get_subpaths(), sep='\n')
        self.add(m1)

class GeometryTest(Scene):
    def construct(self) -> None:
        self.add(RoundedRectangle())

GeometryTest().run()
